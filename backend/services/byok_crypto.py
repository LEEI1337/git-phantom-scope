"""BYOK Cryptographic Service — AES-256-GCM key handling.

Provides server-side decryption for BYOK (Bring Your Own Key) API keys.
Frontend encrypts the user's API key with AES-256-GCM using a session-derived
key, sends the ciphertext in `X-Encrypted-Key` header. Backend decrypts
in-memory only for the duration of the request.

SECURITY:
- Decrypted keys exist in memory ONLY during the API call
- Keys are NEVER logged, stored, or persisted anywhere
- Keys are NEVER included in error messages or stack traces
- Uses AES-256-GCM authenticated encryption (AEAD)
- Nonce (IV) is prepended to the ciphertext
"""

import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings
from app.exceptions import GPSBaseError
from app.logging_config import get_logger

logger = get_logger(__name__)

# Nonce size for AES-GCM (96 bits = 12 bytes, NIST recommended)
_NONCE_SIZE = 12

# AES key size (256 bits = 32 bytes)
_KEY_SIZE = 32


class BYOKCryptoError(GPSBaseError):
    """BYOK encryption/decryption error — generic, no details exposed."""

    def __init__(self) -> None:
        super().__init__(
            code="BYOK_CRYPTO_ERROR",
            message="Key decryption failed. Please re-encrypt and try again.",
            status_code=401,
        )


def _derive_encryption_key(session_id: str) -> bytes:
    """Derive a 256-bit AES key from the server secret + session ID.

    Uses HKDF-like derivation via SHA-256(secret || session_id).
    The session_id acts as a salt, binding the key to the session.

    Args:
        session_id: Current user session identifier.

    Returns:
        32-byte AES key.
    """
    settings = get_settings()
    secret = settings.byok_encryption_key or settings.session_secret_key
    secret_bytes = secret.get_secret_value().encode("utf-8")
    session_bytes = session_id.encode("utf-8")

    # SHA-256 produces exactly 32 bytes = 256 bits
    return hashlib.sha256(secret_bytes + session_bytes).digest()


def encrypt_api_key(plaintext_key: str, session_id: str) -> bytes:
    """Encrypt an API key with AES-256-GCM for transit/storage.

    Format: nonce (12 bytes) || ciphertext+tag

    This is primarily used for testing and the server-side key exchange
    flow. In production, the frontend performs encryption via WebCrypto.

    Args:
        plaintext_key: The raw API key to encrypt.
        session_id: Session ID to derive the encryption key.

    Returns:
        bytes: nonce || ciphertext (including GCM auth tag).
    """
    aes_key = _derive_encryption_key(session_id)
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(aes_key)
    ciphertext = aesgcm.encrypt(nonce, plaintext_key.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_api_key(encrypted_data: bytes, session_id: str) -> str:
    """Decrypt an API key from AES-256-GCM ciphertext.

    Expected format: nonce (12 bytes) || ciphertext+tag

    SECURITY: The returned plaintext MUST NOT be logged or persisted.
    Caller is responsible for using it only for the API call duration.

    Args:
        encrypted_data: nonce + ciphertext bytes (from X-Encrypted-Key header).
        session_id: Session ID to derive the decryption key.

    Returns:
        Decrypted API key as string.

    Raises:
        BYOKCryptoError: If decryption fails (wrong key, tampered data, etc.)
    """
    if len(encrypted_data) < _NONCE_SIZE + 1:
        raise BYOKCryptoError()

    nonce = encrypted_data[:_NONCE_SIZE]
    ciphertext = encrypted_data[_NONCE_SIZE:]

    aes_key = _derive_encryption_key(session_id)
    aesgcm = AESGCM(aes_key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        # NEVER expose the reason for failure
        raise BYOKCryptoError()


def generate_session_key_params(session_id: str) -> dict[str, str]:
    """Generate parameters for the frontend to derive the same AES key.

    The frontend uses WebCrypto API to derive the AES key from these
    parameters and encrypt the user's API key before sending it.

    Args:
        session_id: Current session ID.

    Returns:
        Dict with key derivation parameters for the frontend.
    """
    # Generate a random salt for this key exchange
    salt = secrets.token_hex(16)

    return {
        "algorithm": "AES-GCM",
        "key_size": 256,
        "nonce_size": _NONCE_SIZE,
        "salt": salt,
        "session_id": session_id,
        "kdf": "SHA-256",
    }
