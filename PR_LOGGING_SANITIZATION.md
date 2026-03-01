## 📌 Description

Ensures sensitive information (passwords, tokens, OTPs) is not exposed in logs and ensures structured logging is used consistently across the application.

**Impact:**
- Prevents credential leakage (Passwords, JWTs, OTPs) in log files and console output.
- Ensures observability data is machine-readable (JSON) and sanitized for production environments.
- Protects against sensitive information appearing in stack traces.

**What Changed:**
1. **`backend/fastapi/api/utils/logging_config.py`**
   - Implemented `SensitiveDataFormatter`: A custom JSON formatter that recursively redacts sensitive keys (e.g., `password`, `token`, `otp`, `auth`, `cookie`).
   - Added `mask_sensitive_data` utility to sanitize database URLs and other strings containing credentials.
   - Enhanced stack trace sanitization: Automatically redacts secrets within `exc_info` and error messages.
   - Hardened defaults: Logging now defaults to the most secure (sanitized, structured) mode if the configuration system fails early.

2. **`backend/fastapi/api/services/email_service.py`**
   - Redacted OTP codes from `stdout` and logs. The mock implementation now hides real codes unless explicitly in a gated development environment.
   - Replaced `print()` with structured `logger` calls for better visibility and sanitization.

3. **`backend/fastapi/api/main.py`**
   - Replaced all remaining root-level `print()` statements with structured `logger` calls (e.g., Server Instance ID, Trusted Host configuration).

---

## 🔧 Type of Change
Please mark the relevant option(s):

- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [ ] 📝 Documentation update
- [ ] ♻️ Refactor / Code cleanup
- [ ] 🎨 UI / Styling change
- [x] 🚀 Other (Security Hardening): Implements automated redaction of PII and secrets in application logs.

---

## 🧪 How Has This Been Tested?
Describe the tests you ran to verify your changes.

- [x] Manual testing (verified redacted output for simulated sensitive logs)
- [ ] Automated tests

**Test Cases:**

| # | Test | Input | Expected Result |
|---|------|-------|-----------------|
| 1 | URL Credential Masking | `postgres://user:password@host/db` | `postgres://user:********@host/db` in log |
| 2 | Dict Key Masking | `{"password": "secret123", "user": "test"}` | `{"password": "********", "user": "test"}` in log |
| 3 | OTP Sanitization | Trigger 2FA email send | `Mock email sent to ... with code ******` in logs |
| 4 | Message String Redaction | `logger.info("user password=secret123")` | `user password=********` in log |

---

## ✅ Checklist
Please confirm the following:

- [x] My code follows the project's coding style
- [x] I have tested my changes
- [x] I have updated documentation where necessary
- [x] This PR does not introduce breaking changes

---

## 📝 Additional Notes

- The masking logic is recursive and case-insensitive, ensuring that nested dictionaries and mixed-case keys (e.g., `PASSword`) are correctly captured.
- This is a defence-in-depth measure; developers should still avoid logging sensitive data directly, but the system now provides a automated safety net.
