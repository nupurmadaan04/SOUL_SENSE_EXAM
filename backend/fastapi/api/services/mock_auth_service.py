"""
Mock Authentication Service for Testing and Development

This service provides a simplified authentication flow for testing purposes.
It bypasses real password verification and database operations while maintaining
the same interface as the real AuthService.

Usage:
    Set MOCK_AUTH_MODE=true in environment variables to enable mock authentication.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, Dict, Tuple, Any, cast
from jose import jwt
from ..constants.errors import ErrorCode
from ..exceptions import AuthException

from ..config import get_settings
from ..services.db_service import get_db
from ..schemas import UserCreate
from ..models import User
from sqlalchemy.orm import Session

settings = get_settings()

# CRITICAL SECURITY GUARD: Prevent MockAuthService from loading in production
if settings.ENVIRONMENT == "production":
    raise RuntimeError("CRITICAL SECURITY VIOLATION: MockAuthService cannot be loaded in a production environment!")

logger = logging.getLogger(__name__)

# Mock users for testing
# Note: User model only has: id, username, password_hash, created_at, last_login, is_active, is_2fa_enabled
# Email, first_name, last_name, age, gender are in PersonalProfile
MOCK_USERS = {
    "test@example.com": {
        "id": 1,
        "username": "testuser",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # Mock hash
        "is_active": True,
        "is_2fa_enabled": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_login": None,
    },
    "admin@example.com": {
        "id": 2,
        "username": "admin",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "is_active": True,
        "is_2fa_enabled": False,
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_login": None,
    },
    "2fa@example.com": {
        "id": 3,
        "username": "twofa",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "is_active": True,
        "is_2fa_enabled": True,
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_login": None,
    },
}

# Mock user profiles (separate from User model)
MOCK_PROFILES = {
    1: {"email": "test@example.com", "first_name": "Test", "last_name": "User", "age": 25, "gender": "M"},
    2: {"email": "admin@example.com", "first_name": "Admin", "last_name": "User", "age": 30, "gender": "F"},
    3: {"email": "2fa@example.com", "first_name": "TwoFA", "last_name": "User", "age": 28, "gender": "M"},
}

# Mock OTP codes for testing
MOCK_OTP_CODES = {
    "test@example.com": "123456",
    "admin@example.com": "654321",
    "2fa@example.com": "999999",
}

# Mock refresh tokens
MOCK_REFRESH_TOKENS: Dict[str, int] = {}


class MockAuthService:
    """
    Mock authentication service for testing and development.
    
    This service simulates authentication without requiring a database or real credentials.
    It maintains the same interface as AuthService for easy swapping.
    """

    def __init__(self, db: Optional[Session] = None):
        """Initialize mock auth service."""
        self.db = db
        logger.info("🎭 Mock Authentication Service initialized")

    def authenticate_user(
        self, 
        identifier: str, 
        password: str, 
        ip_address: str = "0.0.0.0",
        user_agent: str = "Unknown"
    ) -> Optional[User]:
        """
        Mock user authentication.
        
        Args:
            identifier: Username or email
            password: Any non-empty password (not validated in mock mode)
            ip_address: Client IP address (logged but not used)
            user_agent: Client user agent (logged but not used)
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        logger.info(f"🎭 Mock authentication attempt for: {identifier}")
        
        # Accept any password in mock mode, just check if user exists
        identifier_lower = identifier.lower()
        
        # Check by email
        if identifier_lower in MOCK_USERS:
            user_data = MOCK_USERS[identifier_lower]
            logger.info(f"✅ Mock authentication successful for: {identifier}")
            user = User(**user_data)
            user.email = identifier_lower
            return user
        
        # Check by username
        for email, user_data in MOCK_USERS.items():
            if user_data["username"].lower() == identifier_lower:
                logger.info(f"✅ Mock authentication successful for: {identifier}")
                user = User(**user_data)
                user.email = email
                return user
        
        logger.warning(f"❌ Mock authentication failed for: {identifier}")
        raise AuthException(
            code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="Incorrect username or password"
        )

    def create_access_token(
        self, 
        data: dict, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a mock JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Optional expiration time delta
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "mock": True  # Flag to identify mock tokens
        })
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        
        logger.debug(f"🎭 Created mock access token for user_id: {data.get('sub')}")
        return encoded_jwt

    def create_pre_auth_token(self, user_id: int) -> str:
        """
        Create a mock pre-authentication token for 2FA flow.
        
        Args:
            user_id: User ID
            
        Returns:
            Pre-auth JWT token
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        to_encode = {
            "sub": str(user_id),
            "scope": "pre_auth",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "mock": True
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        logger.debug(f"🎭 Created mock pre-auth token for user_id: {user_id}")
        return encoded_jwt

    def initiate_2fa_login(self, user: User) -> Tuple[str, str]:
        """
        Mock 2FA login initiation.
        
        Args:
            user: User object
            
        Returns:
            Tuple of (pre_auth_token, mock_otp_code)
        """
        pre_auth_token = self.create_pre_auth_token(cast(Any, user.id))
        
        # Get email from profile
        profile = MOCK_PROFILES.get(cast(Any, user.id), {})
        email = str(profile.get("email", "unknown@example.com"))
        otp_code = MOCK_OTP_CODES.get(email, "123456")
        
        logger.info(f"🎭 Mock 2FA initiated for {email}. OTP: {otp_code}")
        return pre_auth_token, otp_code

    def verify_2fa_login(self, pre_auth_token: str, code: str) -> Optional[User]:
        """
        Mock 2FA verification.
        
        Args:
            pre_auth_token: Pre-authentication token
            code: OTP code
            
        Returns:
            User object if verification succeeds, None otherwise
        """
        try:
            payload = jwt.decode(
                pre_auth_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            
            user_id = int(payload.get("sub"))
            scope = payload.get("scope")
            
            if scope != "pre_auth":
                logger.warning("🎭 Invalid token scope for 2FA verification")
                return None
            
            # Find user by ID
            for user_data in MOCK_USERS.values():
                if user_data["id"] == user_id:
                    # Get email from profile
                    profile = MOCK_PROFILES.get(user_id, {})
                    email = str(profile.get("email", ""))
                    expected_code = MOCK_OTP_CODES.get(email, "123456")
                    
                    if code == expected_code:
                        logger.info(f"✅ Mock 2FA verification successful for user_id: {user_id}")
                        return User(**user_data)
                    else:
                        logger.warning(f"❌ Mock 2FA code mismatch for user_id: {user_id}")
                        return None
            
            logger.warning(f"❌ User not found for user_id: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"🎭 Mock 2FA verification error: {e}")
            return None

    def register_user(self, user_data: UserCreate) -> tuple[bool, Optional[User], str]:
        """
        Mock user registration.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user object
        """
        new_user_id = len(MOCK_USERS) + 1
        
        user_dict = {
            "id": new_user_id,
            "username": user_data.username,
            "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
            "is_active": True,
            "is_2fa_enabled": False,
            "created_at": "2026-01-01T00:00:00+00:00",
            "last_login": None,
        }
        
        # Add to mock users
        MOCK_USERS[user_data.email.lower()] = user_dict
        
        # Store profile data separately
        MOCK_PROFILES[new_user_id] = {
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "age": user_data.age,
            "gender": user_data.gender,
        }
        
        logger.info(f"🎭 Mock user registered: {user_data.email}")
        user = User(**user_dict)
        user.email = user_data.email
        return True, user, "User registered successfully (Mock)"

    def create_refresh_token(self, user_id: int, commit: bool = True) -> str:
        """
        Create a mock refresh token.
        
        Args:
            user_id: User ID
            commit: Ignored in mock implementation
            
        Returns:
            Refresh token string
        """
        import secrets
        token = secrets.token_urlsafe(32)
        MOCK_REFRESH_TOKENS[token] = user_id
        
        logger.debug(f"🎭 Created mock refresh token for user_id: {user_id}")
        return token

    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Mock refresh token validation and rotation.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        user_id = MOCK_REFRESH_TOKENS.get(refresh_token)
        
        if not user_id:
            raise ValueError("Invalid refresh token")
        
        # Find user
        for user_data in MOCK_USERS.values():
            if user_data["id"] == user_id:
                # Create new tokens
                access_token = self.create_access_token({"sub": str(user_id)})
                new_refresh_token = self.create_refresh_token(user_id)
                
                # Invalidate old refresh token
                del MOCK_REFRESH_TOKENS[refresh_token]
                
                logger.info(f"🎭 Mock token refresh successful for user_id: {user_id}")
                return access_token, new_refresh_token
        
        raise ValueError("User not found")

    def revoke_refresh_token(self, refresh_token: str) -> None:
        """
        Mock refresh token revocation.
        
        Args:
            refresh_token: Token to revoke
        """
        if refresh_token in MOCK_REFRESH_TOKENS:
            del MOCK_REFRESH_TOKENS[refresh_token]
            logger.info("🎭 Mock refresh token revoked")

    def revoke_access_token(self, token: str) -> None:
        """Mock access token revocation."""
        logger.info("🎭 Mock access token revoked")

    async def initiate_password_reset(self, email: str, background_tasks: Any) -> Tuple[bool, str]:
        """
        Mock password reset initiation.
        
        Args:
            email: User email
            background_tasks: Background tasks (ignored in mock)
            
        Returns:
            Tuple of (Success, Message)
        """
        otp_code = MOCK_OTP_CODES.get(email.lower(), "123456")
        logger.info(f"🎭 Mock password reset initiated for {email}. OTP: {otp_code}")
        
        # Consistent with real AuthService: Generic message for enumeration protection
        return True, "If an account with that email exists, we have sent a reset link to it."

    def complete_password_reset(
        self, 
        email: str, 
        otp_code: str, 
        new_password: str
    ) -> bool:
        """
        Mock password reset completion.
        
        Args:
            email: User email
            otp_code: OTP code
            new_password: New password
            
        Returns:
            True if successful, False otherwise
        """
        expected_code = MOCK_OTP_CODES.get(email.lower(), "123456")
        
        if otp_code == expected_code:
            logger.info(f"✅ Mock password reset successful for {email}")
            return True
        else:
            logger.warning(f"❌ Mock password reset failed for {email}")
            return False

    def send_2fa_setup_otp(self, user: User) -> str:
        """
        Mock 2FA setup OTP generation.
        
        Args:
            user: User object
            
        Returns:
            Mock OTP code
        """
        otp_code = "888888"  # Fixed code for 2FA setup
        profile = MOCK_PROFILES.get(cast(Any, user.id), {})
        email = profile.get("email", "unknown@example.com")
        logger.info(f"🎭 Mock 2FA setup OTP for {email}: {otp_code}")
        return otp_code

    def enable_2fa(self, user_id: int, code: str) -> bool:
        """
        Mock 2FA enablement.
        
        Args:
            user_id: User ID
            code: OTP code
            
        Returns:
            True if successful, False otherwise
        """
        if code == "888888":
            logger.info(f"✅ Mock 2FA enabled for user_id: {user_id}")
            return True
        else:
            logger.warning(f"❌ Mock 2FA enable failed for user_id: {user_id}")
            return False

    def disable_2fa(self, user_id: int) -> None:
        """
        Mock 2FA disablement.
        
        Args:
            user_id: User ID
        """
        logger.info(f"🎭 Mock 2FA disabled for user_id: {user_id}")

    def update_last_login(self, user_id: int) -> None:
        """
        Mock last login update.
        
        Args:
            user_id: User ID
        """
        logger.debug(f"🎭 Mock last login updated for user_id: {user_id}")
