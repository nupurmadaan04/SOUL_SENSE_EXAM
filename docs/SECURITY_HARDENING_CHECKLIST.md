# Security Hardening Checklist

> **Authoritative reference** for every security control in SoulSense.
> Run `python scripts/check_security_hardening.py` to get a live status report.
> **Last reviewed:** 2026-03-07 · **Update policy:** Review on every security-related PR.

---

## How to Use This Checklist

| Symbol  | Meaning                           |
| ------- | --------------------------------- |
| **[x]** | Implemented and verified          |
| **[ ]** | Not yet implemented               |
| **[~]** | Partially implemented — see notes |

**Workflow:**

1. Run `python scripts/check_security_hardening.py` for an automated status snapshot.
2. Before every release, verify all critical checks pass (exit code 0).
3. When opening a security-related PR, update the relevant rows and paste the script output.

Update this file as part of every **security-related PR** (see PR template).

---

## 1. Authentication

- [x] Password hashing with bcrypt (12 rounds) — `app/auth/crypto.py`
- [x] Automatic per-password salt generation — `app/auth/crypto.py`
- [x] Account lockout after 5 failed attempts (5-min duration) — `app/security_config.py`, `app/auth/auth.py`
- [x] Timing-attack-safe login (dummy verify on missing user) — `app/auth/auth.py`
- [x] Password complexity enforcement (8-128 chars, upper/lower/digit/special) — `app/validation.py`
- [x] Secure password entry in UI (no copy/paste/right-click) — `app/auth/app_auth.py`
- [x] Password strength meter — `app/auth/app_auth.py`
- [x] Identifier normalization (lowercase usernames/emails) — `app/auth/auth.py`

## 2. Two-Factor Authentication (2FA / OTP)

- [x] OTP generation with 6-digit codes, 5-min expiry — `app/auth/otp_manager.py`
- [x] OTP hashed before storage (SHA-256) — `app/auth/otp_manager.py`
- [x] Max 3 verification attempts per OTP — `app/auth/otp_manager.py`
- [x] Rate limit on OTP generation (60 s) — `app/auth/otp_manager.py`
- [x] Per-user 2FA enable/disable — `app/auth/auth.py`

## 3. Session Management

- [x] 256-bit cryptographically secure session IDs — `app/auth/auth.py`
- [x] 24-hour session expiry — `app/security_config.py`
- [x] Session invalidation on logout — `app/auth/auth.py`
- [x] Multi-session tracking per user — `app/auth/session_storage.py`
- [x] Last-accessed timestamp updates — `app/auth/session_storage.py`
- [x] Bulk session cleanup utilities — `session_manager.py`

## 4. Authorization / RBAC

- [~] Reserved username list (`admin`, `root`, etc.) — `app/validation.py`
- [~] Admin user protection (User ID 1 exempt from lifecycle ops) — `app/services/lifecycle.py`
- [ ] Explicit role/permission model (roles table, permission grants)
- [ ] Endpoint-level authorization middleware
- [ ] Granular permission groups

## 5. Rate Limiting

- [x] OTP generation rate limit (60 s between requests) — `app/auth/otp_manager.py`
- [x] Login attempt throttling (5 failures → lockout) — `app/auth/auth.py`
- [x] General API rate limit (60 req/min per IP) — `app/security_config.py`
- [x] Analytics API rate limit (30 req/min per IP) — `backend/fastapi/api/middleware/rate_limiter.py`
- [ ] Redis-backed rate limiting for multi-instance deployments

## 6. Input Validation & Sanitization

- [x] SQL injection pattern detection (6 patterns) — `app/validation.py`
- [x] XSS pattern detection (4 patterns) — `app/validation.py`
- [x] HTML entity escaping via `sanitize_text()` — `app/validation.py`
- [x] Username format validation (3-20 alphanum + underscore) — `app/validation.py`
- [x] Email RFC validation with TLD check — `app/validation.py`
- [x] Phone number format validation — `app/validation.py`
- [x] Age range validation (13-120) — `app/validation.py`
- [x] Max input length enforcement (1000 chars) — `app/security_config.py`

## 7. File Security

- [x] File extension whitelist (jpg, jpeg, png, gif) — `app/security_config.py`
- [x] Max file size enforcement (5 MB) — `app/security_config.py`
- [x] Path traversal prevention — `app/utils/file_validation.py`
- [x] Windows reserved filename handling — `app/utils/file_validation.py`
- [x] Dangerous character removal in filenames — `app/utils/file_validation.py`

## 8. Secrets & Cryptography

- [x] Fernet symmetric encryption (AES-128) — `app/auth/crypto.py`
- [x] PBKDF2-HMAC-SHA256 key derivation (100k iterations) — `app/auth/crypto.py`
- [x] JWT with HS256, min-32-char secret from env — `backend/fastapi/api/config.py`
- [x] Refresh tokens hashed (SHA-256) before storage — `backend/fastapi/api/services/auth_service.py`
- [x] Session IDs via `secrets.token_urlsafe(32)` — `app/auth/auth.py`
- [x] Secrets directory in `.gitignore` — `.gitignore`

## 9. Security Headers & CORS

- [x] `X-Content-Type-Options: nosniff` — `app/security_config.py`
- [x] `X-Frame-Options: DENY` — `app/security_config.py`
- [x] `X-XSS-Protection: 1; mode=block` — `app/security_config.py`
- [x] `Strict-Transport-Security` (HSTS) — `app/security_config.py`
- [x] `Referrer-Policy: strict-origin-when-cross-origin` — `backend/fastapi/api/middleware/security.py`
- [x] SecurityHeadersMiddleware on all responses — `backend/fastapi/api/middleware/security.py`
- [x] CORS with configurable allowed origins — `backend/fastapi/api/main.py`
- [x] Preflight cache (3600 s) — `backend/fastapi/api/main.py`
- [ ] Content-Security-Policy (CSP) header

## 10. PII Redaction & Data Protection

- [x] Audit log detail-field allowlist filtering — `app/services/audit_service.py`
- [x] User-agent truncation (250 chars max) — `app/services/audit_service.py`
- [x] Passwords never stored or logged in plaintext — `app/auth/crypto.py`
- [x] OTPs never stored in plaintext — `app/auth/otp_manager.py`
- [ ] PII masking in application log files (emails, phone numbers)

## 11. Audit Logging

- [x] Centralized audit service with event tracking — `app/services/audit_service.py`
- [x] Login/logout/register/password-reset/2FA events logged — `app/services/audit_service.py`
- [x] IP address and user-agent captured per event — `app/services/audit_service.py`
- [x] UTC ISO 8601 timestamps — `app/services/audit_service.py`
- [x] 90-day log retention with configurable cleanup — `app/services/audit_service.py`
- [x] DB-failure fallback logging — `app/services/audit_service.py`

## 12. Error Handling

- [x] Custom exception hierarchy (`SoulSenseError` base) — `app/exceptions.py`
- [x] Severity-level classification (LOW → CRITICAL) — `app/error_handler.py`
- [x] Friendly user-facing messages (no raw tracebacks in production) — `app/error_handler.py`
- [x] `@safe_operation()` decorator for auto error handling — `app/error_handler.py`
- [x] Context capture (user ID, IP, operation) — `app/error_handler.py`

## 13. Infrastructure & Deployment

- [ ] CSRF token protection for state-changing operations
- [ ] Dependency vulnerability scanning (Snyk / Dependabot)
- [ ] Security headers tested in CI/CD
- [ ] WAF integration for production

---

## Release Gate

Before every release that touches security-related code, verify:

1. Run `python scripts/check_security_hardening.py` — all critical checks must pass.
2. Review this checklist for any newly added `[ ]` items.
3. Confirm no secrets are committed (check `.gitignore` coverage).
4. Ensure all tests in `tests/` pass, including security-specific tests.

---

## Updating This Checklist

When submitting a security-related PR:

1. Add or update the relevant line(s) in this checklist.
2. Run the automated status script and paste the summary in the PR description.
3. Get a security-focused review from at least one maintainer.
