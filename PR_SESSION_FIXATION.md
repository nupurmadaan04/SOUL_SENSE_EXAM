# Pull Request: Prevent Session Fixation and Enforce Secure Cookies

## Objective
Protect user sessions from fixation attacks and enforce secure cookie practices to mitigate session hijacking and account takeover risks.

## Description
This PR implements session identifier regeneration upon login and enforces modern secure cookie flags across the application.

### Key Changes

#### 1. Backend: Session Fixation Protection
- **Session Revocation on Login**: In `backend/fastapi/api/routers/auth.py`, the `login` and `login/2fa` endpoints now check for an existing `refresh_token` cookie. If present, the corresponding session is revoked in the database before a new one is issued. This ensures that any session identifier obtained prior to authentication is invalidated, preventing session fixation.
- **Improved Token Rotation**: Enhanced the atomic token rotation logic to ensure consistency between revocation and new token issuance.

#### 2. Backend: Secure Cookie Enforcement
- **Dynamic Configuration**: Replaced hardcoded cookie flags with configurable settings from `BaseAppSettings`.
- **Production Safety**: Cookies are now explicitly marked as `Secure` in production environments (via `settings.cookie_secure`).
- **SameSite Compliance**: Added support for the `SameSite` attribute (defaulting to `Lax`), which helps mitigate CSRF attacks.
- **Utility Additions**: Added an `is_production` property to the backend configuration for cleaner environment checks.

#### 3. Frontend: Credentials Support
- **Core API Client**: Updated the unified `apiClient` in `frontend-web/src/lib/api/client.ts` to include `credentials: 'include'` by default. This is critical for supporting `HttpOnly` cookies, especially when the frontend and backend run on different origins (e.g., during local development or staged deployments).

## Technical Implementation Details
- **Regenerate session on login**: Implemented in `/auth/login` and `/auth/login/2fa`.
- **Set Secure, HttpOnly, SameSite flags**: Enforced in all `response.set_cookie` calls within the auth router.
- **Acceptance Criteria**:
  - [x] Session regenerated after login.
  - [x] Secure cookie flags enforced (HttpOnly, Secure, SameSite).

## Recommended Testing
1. **Verify Session Regeneration**:
   - Capture the `refresh_token` cookie before logging in.
   - Login successfully.
   - Verify that the new `refresh_token` is different from the pre-login token.
2. **Inspect Cookie Flags**:
   - Check the `refresh_token` cookie in the browser's developer tools.
   - Confirm `HttpOnly` is checked.
   - Confirm `SameSite` is set to `Lax`.
   - In production/staging, confirm the `Secure` flag is present.
3. **Frontend Refresh**:
   - Verify that the frontend can still successfully refresh tokens (requires `credentials: 'include'` to be working).

## Impact
- Prevents session fixation attacks where an attacker pre-sets a session ID for a victim.
- Hardens the session management against hijacking by restricting cookie access to HTTP requests only and enforcing HTTPS.
