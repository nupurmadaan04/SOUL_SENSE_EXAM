"""
Verification script for Mock Authentication implementation.
This script verifies that all components are working correctly.
"""

import os
import sys

# Set mock mode before any imports
os.environ["MOCK_AUTH_MODE"] = "true"
os.environ["APP_ENV"] = "development"

print("=" * 60)
print("Mock Authentication Verification Script")
print("=" * 60)

# Test 1: Import mock auth service
print("\n✓ Test 1: Importing MockAuthService...")
try:
    from backend.fastapi.api.services.mock_auth_service import MockAuthService, MOCK_USERS, MOCK_OTP_CODES, MOCK_PROFILES
    print("  ✅ Successfully imported MockAuthService")
    print(f"  ✅ Found {len(MOCK_USERS)} mock users")
    print(f"  ✅ Found {len(MOCK_PROFILES)} mock profiles")
    print(f"  ✅ Found {len(MOCK_OTP_CODES)} OTP codes")
except Exception as e:
    print(f"  ❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Create service instance
print("\n✓ Test 2: Creating MockAuthService instance...")
try:
    auth_service = MockAuthService()
    print("  ✅ Successfully created MockAuthService instance")
except Exception as e:
    print(f"  ❌ Failed to create instance: {e}")
    sys.exit(1)

# Test 3: Authenticate user
print("\n✓ Test 3: Authenticating test user...")
try:
    user = auth_service.authenticate_user("test@example.com", "any_password")
    if user:
        print(f"  ✅ Authentication successful")
        print(f"     - User ID: {user.id}")
        print(f"     - Username: {user.username}")
        print(f"     - Active: {user.is_active}")
    else:
        print("  ❌ Authentication failed")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Error during authentication: {e}")
    sys.exit(1)

# Test 4: Create access token
print("\n✓ Test 4: Creating access token...")
try:
    token = auth_service.create_access_token({"sub": "testuser"})
    if token and len(token) > 0:
        print(f"  ✅ Token created successfully")
        print(f"     - Token length: {len(token)} characters")
    else:
        print("  ❌ Token creation failed")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Error creating token: {e}")
    sys.exit(1)

# Test 5: 2FA flow
print("\n✓ Test 5: Testing 2FA flow...")
try:
    user_2fa = auth_service.authenticate_user("2fa@example.com", "any_password")
    if user_2fa and user_2fa.is_2fa_enabled:
        pre_auth_token, otp = auth_service.initiate_2fa_login(user_2fa)
        verified_user = auth_service.verify_2fa_login(pre_auth_token, otp)
        if verified_user:
            print(f"  ✅ 2FA flow completed successfully")
            print(f"     - OTP Code: {otp}")
        else:
            print("  ❌ 2FA verification failed")
            sys.exit(1)
    else:
        print("  ❌ 2FA user not found or 2FA not enabled")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Error in 2FA flow: {e}")
    sys.exit(1)

# Test 6: Refresh token flow
print("\n✓ Test 6: Testing refresh token flow...")
try:
    refresh_token = auth_service.create_refresh_token(user_id=1)
    access_token, new_refresh_token = auth_service.refresh_access_token(refresh_token)
    if access_token and new_refresh_token and refresh_token != new_refresh_token:
        print(f"  ✅ Refresh token flow completed successfully")
        print(f"     - Token rotation working")
    else:
        print("  ❌ Refresh token flow failed")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Error in refresh token flow: {e}")
    sys.exit(1)

# Test 7: Password reset flow
print("\n✓ Test 7: Testing password reset flow...")
try:
    otp = auth_service.initiate_password_reset("test@example.com")
    success = auth_service.complete_password_reset("test@example.com", otp, "new_password")
    if success:
        print(f"  ✅ Password reset flow completed successfully")
        print(f"     - OTP Code: {otp}")
    else:
        print("  ❌ Password reset failed")
        sys.exit(1)
except Exception as e:
    print(f"  ❌ Error in password reset flow: {e}")
    sys.exit(1)

# Test 8: Configuration check
print("\n✓ Test 8: Checking configuration...")
try:
    from backend.fastapi.api.config import get_settings
    settings = get_settings()
    if settings.mock_auth_mode:
        print(f"  ✅ Mock auth mode is enabled")
        print(f"     - Environment: {settings.app_env}")
    else:
        print("  ⚠️  Mock auth mode is not enabled in settings")
except Exception as e:
    print(f"  ❌ Error checking configuration: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("✅ ALL VERIFICATION TESTS PASSED!")
print("=" * 60)
print("\nMock Authentication is working correctly.")
print("You can now use it for testing and development.")
print("\nTest Users:")
print("  - test@example.com (testuser) - OTP: 123456")
print("  - admin@example.com (admin) - OTP: 654321")
print("  - 2fa@example.com (twofa) - OTP: 999999")
print("\nTo enable in your app:")
print("  Set environment variable: MOCK_AUTH_MODE=true")
print("=" * 60)
