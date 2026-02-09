"""Tests for BYOK cryptographic service (AES-256-GCM)."""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from app.config import Environment, Settings
from services.byok_crypto import (
    BYOKCryptoError,
    _derive_encryption_key,
    decrypt_api_key,
    encrypt_api_key,
    generate_session_key_params,
)


@pytest.fixture
def test_settings():
    """Settings with known encryption key for deterministic tests."""
    return Settings(
        environment=Environment.TESTING,
        session_secret_key=SecretStr("test-secret-key-minimum-32-chars!!"),
        byok_encryption_key=SecretStr("test-byok-encryption-key-32bytes!"),
    )


@pytest.fixture(autouse=True)
def _patch_settings(test_settings):
    """Patch settings globally for all tests in this module."""
    with patch("services.byok_crypto.get_settings", return_value=test_settings):
        yield


class TestKeyDerivation:
    def test_derives_32_byte_key(self):
        key = _derive_encryption_key("session-123")
        assert len(key) == 32

    def test_different_sessions_produce_different_keys(self):
        key1 = _derive_encryption_key("session-aaa")
        key2 = _derive_encryption_key("session-bbb")
        assert key1 != key2

    def test_same_session_produces_same_key(self):
        key1 = _derive_encryption_key("session-xyz")
        key2 = _derive_encryption_key("session-xyz")
        assert key1 == key2

    def test_uses_byok_encryption_key_when_set(self):
        """Verify the BYOK encryption key is preferred over session secret."""
        key_with_byok = _derive_encryption_key("session-1")

        settings_no_byok = Settings(
            environment=Environment.TESTING,
            session_secret_key=SecretStr("different-session-key-for-test!!"),
            byok_encryption_key=SecretStr("test-byok-encryption-key-32bytes!"),
        )
        with patch(
            "services.byok_crypto.get_settings",
            return_value=settings_no_byok,
        ):
            key_same_byok = _derive_encryption_key("session-1")

        # Same BYOK key → same derived key
        assert key_with_byok == key_same_byok


class TestEncryptDecryptRoundtrip:
    def test_roundtrip_simple_key(self):
        session_id = "sess-roundtrip-1"
        original = "sk-test-api-key-12345"
        encrypted = encrypt_api_key(original, session_id)
        decrypted = decrypt_api_key(encrypted, session_id)
        assert decrypted == original

    def test_roundtrip_long_key(self):
        session_id = "sess-long"
        original = "a" * 256
        encrypted = encrypt_api_key(original, session_id)
        decrypted = decrypt_api_key(encrypted, session_id)
        assert decrypted == original

    def test_roundtrip_special_characters(self):
        session_id = "sess-special"
        original = "key/with+special=chars&more!@#$%"
        encrypted = encrypt_api_key(original, session_id)
        decrypted = decrypt_api_key(encrypted, session_id)
        assert decrypted == original

    def test_roundtrip_unicode_key(self):
        session_id = "sess-unicode"
        original = "key-with-émojis-🔑"
        encrypted = encrypt_api_key(original, session_id)
        decrypted = decrypt_api_key(encrypted, session_id)
        assert decrypted == original

    def test_encrypted_data_starts_with_12_byte_nonce(self):
        encrypted = encrypt_api_key("test-key", "session-1")
        # nonce(12) + ciphertext+tag (at least 16 bytes for GCM tag + payload)
        assert len(encrypted) > 12 + 16

    def test_different_encryptions_produce_different_ciphertext(self):
        """Each encryption should use a random nonce → different output."""
        ct1 = encrypt_api_key("same-key", "same-session")
        ct2 = encrypt_api_key("same-key", "same-session")
        assert ct1 != ct2  # Random nonce makes ciphertext unique


class TestDecryptionFailures:
    def test_wrong_session_raises(self):
        encrypted = encrypt_api_key("my-key", "session-A")
        with pytest.raises(BYOKCryptoError):
            decrypt_api_key(encrypted, "session-B")

    def test_tampered_ciphertext_raises(self):
        encrypted = encrypt_api_key("my-key", "session-1")
        # Flip a bit in the ciphertext (after the nonce)
        tampered = bytearray(encrypted)
        tampered[15] ^= 0xFF
        with pytest.raises(BYOKCryptoError):
            decrypt_api_key(bytes(tampered), "session-1")

    def test_truncated_data_raises(self):
        with pytest.raises(BYOKCryptoError):
            decrypt_api_key(b"short", "session-1")

    def test_empty_data_raises(self):
        with pytest.raises(BYOKCryptoError):
            decrypt_api_key(b"", "session-1")

    def test_nonce_only_raises(self):
        """12 bytes of nonce but no ciphertext."""
        with pytest.raises(BYOKCryptoError):
            decrypt_api_key(os.urandom(12), "session-1")

    def test_random_data_raises(self):
        """Completely random data should fail GCM auth."""
        with pytest.raises(BYOKCryptoError):
            decrypt_api_key(os.urandom(64), "session-1")


class TestBYOKCryptoError:
    def test_error_code(self):
        error = BYOKCryptoError()
        assert error.code == "BYOK_CRYPTO_ERROR"

    def test_error_status_code(self):
        error = BYOKCryptoError()
        assert error.status_code == 401

    def test_error_message_is_generic(self):
        """Error message must NOT reveal any crypto internals."""
        error = BYOKCryptoError()
        assert "decrypt" in error.message.lower() or "re-encrypt" in error.message.lower()
        # Must NOT contain: key, nonce, AES, GCM, etc.
        assert "aes" not in error.message.lower()
        assert "gcm" not in error.message.lower()


class TestSessionKeyParams:
    def test_params_contain_required_fields(self):
        params = generate_session_key_params("session-test")
        assert params["algorithm"] == "AES-GCM"
        assert params["key_size"] == 256
        assert params["nonce_size"] == 12
        assert "salt" in params
        assert params["session_id"] == "session-test"
        assert params["kdf"] == "SHA-256"

    def test_salt_is_random_each_call(self):
        p1 = generate_session_key_params("session-1")
        p2 = generate_session_key_params("session-1")
        assert p1["salt"] != p2["salt"]
