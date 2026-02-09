---
name: "privacy-check"
description: "Audit codebase for privacy compliance: verify zero PII storage, BYOK key handling, Redis TTL enforcement, and GDPR-by-design principles."
mode: "agent"
---

# Privacy Check

## Context
Audit the Git Phantom Scope codebase for privacy compliance. This is a critical skill that must be run before every release.

## Audit Checklist

### 1. PII Storage Audit
Scan all database models and migrations for PII fields:
```bash
# Check PostgreSQL models for forbidden fields
grep -rn "username\|email\|github_id\|ip_address\|user_agent" backend/db/
grep -rn "CharField\|StringField\|VARCHAR" backend/db/models.py
```

**Forbidden fields in PostgreSQL:**
- username, user_name, github_username
- email, email_address
- github_id, user_id (as PII reference)
- ip_address, client_ip
- session_id (linked to user)
- Any field that could identify a specific person

### 2. Redis TTL Audit
Verify all Redis keys have TTL:
```python
# CORRECT: TTL set on every write
await redis.setex(f"session:{session_id}", 1800, data)  # 30 min TTL

# WRONG: No TTL - data persists forever
await redis.set(f"session:{session_id}", data)  # FORBIDDEN
```

Check for TTL enforcement:
```bash
grep -rn "redis.set\b" backend/  # Should return 0 results (use setex instead)
grep -rn "\.setex\|\.expire" backend/  # Should match all Redis writes
```

### 3. BYOK Key Audit
Verify keys never appear in logs or storage:
```bash
# Check for key logging
grep -rn "api_key\|byok_key\|secret_key" backend/ --include="*.py" | grep -i "log\|print\|debug"

# Check for key storage
grep -rn "api_key\|byok_key" backend/db/  # Should return 0 results
```

### 4. Error Message Audit
Verify no PII leaks in error messages:
```bash
# Check error messages for variable interpolation of user data
grep -rn "f\".*username\|f\".*email\|f\".*api_key" backend/ --include="*.py"
```

### 5. Log Audit
Verify logging does not capture PII:
```bash
# Check all logger calls for PII
grep -rn "logger\.\(info\|debug\|warning\|error\)" backend/ --include="*.py"
# Manually review each for PII inclusion
```

### 6. Asset Cleanup Audit
Verify generated files have auto-deletion:
```python
# CORRECT: Schedule cleanup
await schedule_cleanup(file_path, ttl_hours=4)

# WRONG: No cleanup scheduled
save_file(file_path)  # File persists forever
```

## Automated Privacy Report
```json
{
  "audit_date": "2025-08-17T12:00:00Z",
  "status": "PASS|FAIL",
  "checks": {
    "pii_in_database": {"status": "PASS", "findings": 0},
    "redis_ttl_missing": {"status": "PASS", "findings": 0},
    "byok_key_exposure": {"status": "PASS", "findings": 0},
    "pii_in_errors": {"status": "PASS", "findings": 0},
    "pii_in_logs": {"status": "PASS", "findings": 0},
    "asset_cleanup": {"status": "PASS", "findings": 0}
  },
  "recommendations": []
}
```

## Implementation Files
- `backend/tests/test_privacy.py` - Automated privacy tests
- `scripts/privacy_audit.py` - CLI audit tool
- `docs/guides/privacy.md` - Privacy documentation
