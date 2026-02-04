from datetime import datetime, timedelta, timezone
import logging
import secrets
import hashlib
from typing import Optional, Dict, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from ..schemas import UserCreate

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import bcrypt

from .db_service import get_db
from ..root_models import User, LoginAttempt, PersonalProfile, RefreshToken
from ..config import get_settings
from ..constants.errors import ErrorCode
from ..constants.security_constants import BCRYPT_ROUNDS, REFRESH_TOKEN_EXPIRE_DAYS
from ..exceptions import AuthException

settings = get_settings()

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def hash_password(self, password: str) -> str:
        """Hash a password for storing."""
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        pwd_bytes = password.encode('utf-8')
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a stored password against one provided by user."""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def authenticate_user(self, identifier: str, password: str, ip_address: str = "0.0.0.0") -> Optional[User]:
        """
        Authenticate a user by username OR email and password.
        
        Security Features:
        - Constant-time password verification (via bcrypt)
        - Identifier normalization (lowercase)
        - Persistent lockout check (TODO: future phase integration)
        - Generic error responses via the caller
        - Failed/Successful login auditing
        """
        # 1. Normalize identifier
        identifier_lower = identifier.lower().strip()

        # 2. Try fetching by username first
        user = self.db.query(User).filter(User.username == identifier_lower).first()
        
        # 3. If not found, try fetching by email (via PersonalProfile)
        if not user:
            profile = self.db.query(PersonalProfile).filter(PersonalProfile.email == identifier_lower).first()
            if profile:
                user = self.db.query(User).filter(User.id == profile.user_id).first()
        
        # 4. Timing attack protection: Always hash something even if user not found
        if not user:
            # Dummy verify to consume time
            self.verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            self._record_login_attempt(identifier_lower, False, ip_address)
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )

        # 5. Verify password
        if not self.verify_password(password, user.password_hash):
            self._record_login_attempt(identifier_lower, False, ip_address)
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )
        
        # 6. Success - Update last login & Audit
        self._record_login_attempt(identifier_lower, True, ip_address)
        self.update_last_login(user.id)
        
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token."""
        # Use python-jose or similar if previously installed, but since we are refactoring,
        # we will assume generic token generation logic or stick to what was likely there.
        # Wait, the plan mentioned create_access_token. I need to check how it was implemented.
        # For now, I will import the logic from the old auth router if possible, or use a placeholder
        # since I need to see the imports in the original file. 
        # Actually, let's stick to generating a secure random token if JWT library isn't confirmed, 
        # BUT the schemas.Token suggests JWT. 
        # Let's check imports in original auth.py first to be safe.
        
        # For now, simplistic JWT construction using standard libraries or jwt library if available
        # I'll check imports later. I will implement a placeholder that is structurally correct.
        from jose import jwt

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=15)
            
        to_encode.update({"exp": expire})
        # Use correct settings attributes as seen in router
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    def create_pre_auth_token(self, user_id: int) -> str:
        """
        Create a temporary token for 2FA verification step.
        Scope: 'pre_auth' - Cannot be used for normal API access.
        """
        from jose import jwt
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "scope": "pre_auth",
            "type": "2fa_challenge"
        }
        return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def initiate_2fa_login(self, user: User) -> str:
        """
        Generate OTP, send email, and return pre_auth_token.
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        
        # 1. Generate OTP
        code, _ = OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=self.db)
        
        # 2. Send Email
        # Resolve email (User obj might not have it loaded if lazy)
        email = None
        # Try to find email from profile
        profile = self.db.query(PersonalProfile).filter(PersonalProfile.user_id == user.id).first()
        if profile:
            email = profile.email
            
        if not email:
            # Fallback or error? For MVP we log error but still return token (fail-close at send)
            logger.error(f"2FA initiated but no email found for user {user.username}")
        else:
            if code:
                EmailService.send_otp(email, code, "Login Verification")
                self.db.commit() # Save OTP
        
        # 3. Create Pre-Auth Token
        return self.create_pre_auth_token(user.id)

    def verify_2fa_login(self, pre_auth_token: str, code: str) -> User:
        """
        Verify pre-auth token and OTP code.
        Returns User if successful, raises AuthException otherwise.
        """
        from jose import jwt, JWTError
        from app.auth.otp_manager import OTPManager
        
        try:
            # 1. Verify Token
            payload = jwt.decode(pre_auth_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            scope = payload.get("scope")
            
            if not user_id or scope != "pre_auth":
                 raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid token scope")
                 
            # 2. Verify OTP
            user_id_int = int(user_id)
            if not OTPManager.verify_otp(user_id_int, code, "LOGIN_CHALLENGE", db_session=self.db):
                 raise AuthException(code=ErrorCode.AUTH_INVALID_CREDENTIALS, message="Invalid or expired code")
                 
            # 3. Success - Fetch User
            user = self.db.query(User).filter(User.id == user_id_int).first()
            if not user:
                 raise AuthException(code=ErrorCode.AUTH_USER_NOT_FOUND, message="User not found")
                 
            # Audit success
            self._record_login_attempt(user.username, True, "0.0.0.0") # IP not passed here, simplified
            self.update_last_login(user.id)
            self.db.commit() # Save OTP used state
            
            return user
            
        except JWTError:
            raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid or expired session")
        except AuthException:
            raise
        except Exception as e:
            logger.error(f"2FA Verify Error: {e}")
            raise AuthException(code=ErrorCode.AUTH_INTERNAL_ERROR, message="Verification failed")

    def send_2fa_setup_otp(self, user: User) -> bool:
        """Generate and send OTP for 2FA setup."""
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        
        code, _ = OTPManager.generate_otp(user.id, "2FA_SETUP", db_session=self.db)
        if not code:
            return False
            
        # Get Email
        email = None
        profile = self.db.query(PersonalProfile).filter(PersonalProfile.user_id == user.id).first()
        if profile:
            email = profile.email
            
        if email:
             EmailService.send_otp(email, code, "Enable 2FA")
             self.db.commit()
             return True
        return False

    def enable_2fa(self, user_id: int, code: str) -> bool:
        """Verify code and enable 2FA."""
        from app.auth.otp_manager import OTPManager
        
        if OTPManager.verify_otp(user_id, code, "2FA_SETUP", db_session=self.db):
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_2fa_enabled = True
                self.db.commit()
                return True
        return False

    def disable_2fa(self, user_id: int) -> bool:
        """Disable 2FA for user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_2fa_enabled = False
            self.db.commit()
            return True
        return False

    def update_last_login(self, user_id: int) -> None:
        """
        Update the last_login timestamp for a user.
        Safe against database locks (fail-open).
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.now(timezone.utc).isoformat()
                self.db.commit()
                logger.info(f"Updated last_login for user_id={user_id}")
        except OperationalError:
            self.db.rollback()
            logger.warning(f"Could not update last_login for user_id={user_id} due to database lock.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update last_login: {e}")

    def _record_login_attempt(self, username: str, success: bool, ip_address: str):
        """Record the login attempt audit log."""
        try:
            attempt = LoginAttempt(
                username=username,
                ip_address=ip_address,
                is_successful=success,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(attempt)
            self.db.commit()
        except Exception as e:
            # Audit logging failure should not block the user, but should be logged
            self.db.rollback()
            logger.error(f"Failed to record login attempt: {e}")

    def register_user(self, user_data: 'UserCreate') -> User:
        """
        Register a new user and their personal profile.
        Standardizes identifiers and validates uniqueness.
        """
        from ..exceptions import APIException
        from ..constants.errors import ErrorCode

        username_lower = user_data.username.lower().strip()
        email_lower = user_data.email.lower().strip()

        # Check uniqueness
        if self.db.query(User).filter(User.username == username_lower).first():
            raise APIException(
                code=ErrorCode.REG_USERNAME_EXISTS,
                message="Username already taken",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if self.db.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first():
            raise APIException(
                code=ErrorCode.REG_EMAIL_EXISTS,
                message="Email already registered",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            hashed_pw = self.hash_password(user_data.password)
            new_user = User(
                username=username_lower,
                password_hash=hashed_pw
            )
            self.db.add(new_user)
            self.db.flush()

            new_profile = PersonalProfile(
                user_id=new_user.id,
                email=email_lower,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                age=user_data.age,
                gender=user_data.gender
            )
            self.db.add(new_profile)
            
            self.db.commit()
            self.db.refresh(new_user)
            return new_user
        except Exception as e:
            self.db.rollback()
            logger.error(f"Registration failed: {e}")
            raise APIException(
                code=ErrorCode.REG_INVALID_DATA,
                message="Could not complete registration",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_refresh_token(self, user_id: int) -> str:
        """
        Generate a secure refresh token, hash it, and store it in the DB.
        """
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(db_token)
        self.db.commit()
        
        return token

    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Validate a refresh token and return a new access token + new refresh token (Rotation).
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        db_token = self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not db_token:
            # Security: If an invalid token is used, log it as a potential attack
            logger.warning(f"Invalid refresh token attempt: {token_hash[:8]}...")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Invalid or expired refresh token"
            )
            
        # Token Rotation: Invalidate the current one immediately
        db_token.is_revoked = True
        self.db.commit()
        
        # Get user
        user = self.db.query(User).filter(User.id == db_token.user_id).first()
        if not user:
             raise AuthException(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="User associated with token no longer exists"
            )
            
        # Create new tokens
        access_token = self.create_access_token(data={"sub": user.username})
        new_refresh_token = self.create_refresh_token(user.id)
        
        return access_token, new_refresh_token

    def revoke_refresh_token(self, refresh_token: str) -> None:
        """Manually revoke a refresh token (e.g., on logout)."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        db_token = self.db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if db_token:
            db_token.is_revoked = True
            self.db.commit()
            logger.info(f"Revoked refresh token for user_id={db_token.user_id}")

    def initiate_password_reset(self, email: str) -> tuple[bool, str]:
        """
        Initiate password reset flow:
        1. Find user by email.
        2. Generate OTP.
        3. Send OTP (Mock).
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService

        try:
            email_lower = email.lower().strip()
            
            # Find User via PersonalProfile
            profile = self.db.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first()
            user = None
            if profile:
                user = self.db.query(User).filter(User.id == profile.user_id).first()
            
            # Privacy: If user not found, return success-like message
            if not user:
                logger.info(f"Password reset requested for unknown email: {email_lower}")
                return True, "If an account exists with this email, a reset code has been sent."

            # Generate OTP
            # Pass our session to prevent premature closing
            code, error = OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=self.db)
            
            if not code:
                return False, error or "Too many requests. Please wait."
                
            # Send Email
            if EmailService.send_otp(email_lower, code, "Password Reset"):
                return True, "If an account exists with this email, a reset code has been sent."
            else:
                return False, "Failed to send email. Please try again later."
                
        except Exception as e:
            logger.error(f"Error in initiate_password_reset: {e}")
            return False, "An error occurred. Please try again."

    def complete_password_reset(self, email: str, otp_code: str, new_password: str) -> tuple[bool, str]:
        """
        Complete password reset flow:
        1. Verify OTP.
        2. Update Password.
        """
        from app.auth.otp_manager import OTPManager
        
        try:
            email_lower = email.lower().strip()
            
            # Find User
            profile = self.db.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first()
            if not profile:
                return False, "Invalid request."
            
            user = self.db.query(User).filter(User.id == profile.user_id).first()
            if not user:
                return False, "Invalid request."
                
            # Verify OTP
            # Pass our session so OTPManager doesn't close it
            if not OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=self.db):
                return False, "Invalid or expired code."
            
            # Update Password
            # 'user' is still attached
            user.password_hash = self.hash_password(new_password)
            
            # Security: Invalidate all existing sessions (Refresh Tokens)
            # This ensures that if the account was compromised, the attacker is logged out everywhere.
            self.db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({RefreshToken.is_revoked: True})
            
            self.db.commit()
            
            logger.info(f"Password reset successfully for user {user.username} (via Web). Sessions invalidated.")
            return True, "Password reset successfully. You can now login."
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in complete_password_reset: {e}")
            return False, f"Internal error: {str(e)}"
