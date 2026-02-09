---
name: "byok-security"
description: "Implement and audit the BYOK (Bring Your Own Key) security protocol ensuring client-side encryption, in-memory-only decryption, and zero persistence."
mode: "agent"
---

# BYOK Security

## Context
The BYOK system allows users to bring their own API keys for AI models. This is the most security-critical component of Git Phantom Scope.

## Security Protocol (MANDATORY)

### Client-Side (Frontend)
```typescript
// 1. User enters API key in browser
// 2. Generate random AES-256 key per session
// 3. Encrypt the API key with WebCrypto API
// 4. Send encrypted key in X-Encrypted-Key header
// 5. Send AES key in X-Session-Key header (over HTTPS only)

async function encryptApiKey(apiKey: string, sessionKey: CryptoKey): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(apiKey);
  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    sessionKey,
    encoded
  );
  return btoa(String.fromCharCode(...new Uint8Array([...iv, ...new Uint8Array(encrypted)])));
}
```

### Server-Side (Backend)
```python
# 1. Receive encrypted key from header
# 2. Decrypt in-memory using session key
# 3. Use decrypted key for API call
# 4. Immediately discard from memory after use
# 5. NEVER log, store, or include in error messages

async def decrypt_byok_key(encrypted_key: str, session_key: str) -> str:
    """Decrypt BYOK key in-memory. Key is discarded after function returns."""
    try:
        decrypted = aes_decrypt(encrypted_key, session_key)
        return decrypted
    except Exception:
        raise GPSBaseError(
            code="BYOK_DECRYPTION_FAILED",
            message="Failed to decrypt API key",  # NO key content in error
            status_code=400
        )
    # decrypted variable goes out of scope here - garbage collected
```

## Security Checklist
- [ ] API key never appears in any log output
- [ ] API key never appears in error messages or stack traces
- [ ] API key never written to disk (including temp files)
- [ ] API key never stored in Redis or PostgreSQL
- [ ] API key encrypted with AES-256-GCM
- [ ] Session key transmitted only over HTTPS
- [ ] Key validation happens in-memory only
- [ ] Memory is properly cleared after use (Python gc)
- [ ] Rate limiting on key validation endpoint
- [ ] Failed validation attempts are logged (without key content)

## Audit Requirements
When reviewing BYOK code, check:
1. `grep -r "api_key" --include="*.py"` - Ensure no logging of keys
2. `grep -r "byok" --include="*.py"` - Review all BYOK handling
3. `grep -r "X-Encrypted-Key"` - Verify header handling
4. No `print()`, `logger.debug()`, or `logger.info()` with key content

## Implementation Files
- `frontend/lib/crypto.ts` - Client-side encryption
- `backend/services/byok_manager.py` - Server-side key handling
- `backend/api/deps.py` - BYOK dependency injection
- `backend/services/model_connector.py` - Key usage in API calls
