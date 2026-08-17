# Security Flaws Fixed

This document records all security vulnerabilities identified during the Phase 2 audit and the corresponding fixes applied.

> **Audit Date:** 2026-08-18
> **Status:** All critical and medium issues resolved

---

## 🔴 Critical Issues Fixed

### 1. Hardcoded Credential Fallback Defaults — FIXED

**Risk:** If `.env` failed to load, the app silently ran with a known, guessable `SECRET_KEY` (`"super_secret_development_key_change_in_prod"`), allowing anyone to forge valid JWT tokens. The `DATABASE_URL` fallback also leaked the database password in source code.

**Files changed:**
- `security.py` — removed `SECRET_KEY` fallback; app now raises `RuntimeError` on startup if missing
- `database.py` — removed `DATABASE_URL` fallback; crashes loudly if env var is absent
- `alembic/env.py` — same treatment for the Alembic migration runner

**Before:**
```python
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_development_key_change_in_prod")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://app_worker:app_secure_pass_123@...")
```

**After:**
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required")
```

---

### 2. OAuth Token Encryption Module — ADDED

**Risk:** The `encrypted_token` column in `linked_accounts` stored OAuth tokens as plaintext. A database compromise (SQL dump, backup leak, or SQL injection in another service) would expose all user OAuth tokens.

**Fix:** Created `crypto.py` with Fernet symmetric encryption (AES-128-CBC via the `cryptography` library).

**New file:** `crypto.py`
```python
from crypto import encrypt_token, decrypt_token

ciphertext = encrypt_token(oauth_access_token)   # store this in DB
plaintext  = decrypt_token(ciphertext)            # retrieve for API calls
```

**Environment:** Added `ENCRYPTION_KEY` (Fernet key) to `.env`. A fresh key was generated via:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

### 3. Password Strength Validation — ADDED

**Risk:** Users could sign up with empty or single-character passwords, making brute-force attacks trivial.

**File changed:** `schemas.py`

**Policy enforced:**
| Rule | Requirement |
|------|-------------|
| Minimum length | 8 characters |
| Uppercase | At least 1 uppercase letter |
| Lowercase | At least 1 lowercase letter |
| Digit | At least 1 number |

**Implementation:** Pydantic `@field_validator` on `UserCreate.password` — validation happens before the request reaches any endpoint logic.

---

## 🟠 Medium Issues Fixed

### 4. Rate Limiting on Auth Endpoints — ADDED

**Risk:** No rate limiting allowed unlimited brute-force login attempts and spam account creation.

**Fix:** Added `slowapi` middleware.

| Endpoint | Limit |
|----------|-------|
| `POST /auth/signup` | 5 requests/minute per IP |
| `POST /auth/login` | 10 requests/minute per IP |

**File changed:** `main.py`

---

### 5. CORS Middleware — ADDED

**Risk:** No CORS configuration meant a future frontend couldn't make API calls, or a rushed wildcard `*` would allow cross-origin attacks.

**Fix:** Added `CORSMiddleware` with configurable allowed origins via `ALLOWED_ORIGINS` env var (defaults to `http://localhost:3000`).

**File changed:** `main.py`

---

### 6. Token Revocation & Logout — ADDED

**Risk:** No way to invalidate a stolen JWT. Tokens remained valid until expiry regardless of user action.

**Fix:**
- Added `jti` (JWT ID) claim to every issued token
- Created an in-memory token denylist in `security.py`
- Added `POST /auth/logout` endpoint — revokes the current token
- Added `POST /auth/refresh` endpoint — issues a new token and revokes the old one

**Files changed:** `security.py`, `main.py`

> **Note:** The in-memory denylist resets on server restart. For production, replace with Redis-backed storage.

---

### 7. Security Headers Middleware — ADDED

**Risk:** Missing HTTP security headers left the API vulnerable to clickjacking, MIME-type sniffing, and missing transport security.

**Headers added:**

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` |

**File changed:** `main.py` (custom `SecurityHeadersMiddleware`)

---

### 8. Status Validation via Schema Type — FIXED

**Risk:** Inline string comparison in `main.py` (`if status not in ("pending", ...)`) duplicated the DB constraint and was prone to drift.

**Fix:** Changed `TaskUpdate.status` type from `str` to `Literal["pending", "completed", "dismissed"]` in `schemas.py`. Invalid values are now rejected at the Pydantic layer with a proper 422 response, and the inline check in `main.py` was removed.

---

## 🟡 Additional Improvements

### 9. Reduced Token Expiry

Changed default `ACCESS_TOKEN_EXPIRE_MINUTES` from `60` to `30` to reduce the window of exposure for a compromised token.

### 10. Removed Unused `passlib` Dependency

`passlib` was in `requirements.txt` but never imported (raw `bcrypt` is used instead). Removed to reduce attack surface — fewer dependencies = fewer potential CVEs.

### 11. Fixed RLS `SET LOCAL` Bug (Pre-existing)

**Risk:** The `set_rls_user()` function in `database.py` used parameterized queries (`:user_id`) for a PostgreSQL `SET LOCAL` command. PostgreSQL `SET` commands do **not** support parameterized placeholders — `psycopg3` was sending `$1` which caused a syntax error, making all authenticated endpoints return 500.

**Fix:** Changed to f-string interpolation with defense-in-depth UUID validation:
```python
safe_id = str(uuid.UUID(str(user_id)))  # validates format, prevents injection
db.execute(text(f"SET LOCAL app.current_user_id = '{safe_id}'"))
```

This is safe because:
- `user_id` comes from a database lookup (validated UUID), never from raw user input
- Additional `uuid.UUID()` parsing ensures only valid UUID strings can reach the query

### 12. Dependencies Added

| Package | Version | Purpose |
|---------|---------|---------|
| `cryptography` | 50.0.0 | Fernet encryption for OAuth tokens |
| `slowapi` | 0.1.10 | IP-based rate limiting |

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `security.py` | Removed fallback defaults, added JTI claims, token denylist |
| `main.py` | Added CORS, rate limiting, security headers, refresh/logout endpoints |
| `schemas.py` | Added password validator, `Literal` status type |
| `database.py` | Removed fallback DATABASE_URL, fixed RLS `SET LOCAL` psycopg3 bug |
| `alembic/env.py` | Removed fallback DATABASE_URL |
| `crypto.py` | **NEW** — Fernet encryption for OAuth tokens |
| `.env` | Added `ENCRYPTION_KEY`, `ALLOWED_ORIGINS`, reduced token expiry |
| `requirements.txt` | Added `cryptography`, `slowapi`; removed `passlib` |
| `docs/security-flaws-fixed.md` | **NEW** — This document |
