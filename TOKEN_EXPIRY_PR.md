## 📌 Description
This PR implements client-side JWT expiry checking and a proactive token refresh mechanism during the application boot sequence. It prevents the "avalanche of broken API requests" that occurs when a user resumes a session with an expired token, which previously led to chaotic 401 errors across the board.

**Key Changes:**
- **JWT Expiry Utility**: Added `isTokenExpired` in `sessionStorage.ts` to decode JWT payloads and check the `exp` claim without external dependencies.
- **Proactive Root Refresh**: Modified `useAuth.tsx` to check for token expiration during `initAuth`. It now attempts a background refresh before allowing the dashboard to mount.
- **Defensive API Client**: Updated `apiClient` to intercept expired tokens before transmission, triggering the refresh flow immediately.
- **Safe Fallbacks**: Implemented silent logout and redirection to `/login` if a refresh fails or the token is malformed.

Fixes: #35

---

## 🔧 Type of Change
- [ ] 🐛 Bug fix
- [x] ✨ New feature
- [ ] 📝 Documentation update
- [x] ♻️ Refactor / Code cleanup
- [x] 🚀 Other (Security Hardening): Prevents unauthenticated network chatter.

---

## 🧪 How Has This Been Tested?
- [x] Manual testing by simulating expired tokens.
- [x] Verified that `isLoading` remains true during proactive refresh.
- [x] Confirmed that unauthenticated API requests are blocked if the token is known to be expired.

---

## ✅ Checklist
- [x] My code follows the project’s coding style
- [x] I have tested my changes
- [x] I have updated documentation where necessary
- [x] This PR does not introduce breaking changes

---

## 📝 Additional Notes
The `isTokenExpired` utility handles Base64Url encoding variations natively, ensuring compatibility with standard FastAPI/Jose JWT outputs.
