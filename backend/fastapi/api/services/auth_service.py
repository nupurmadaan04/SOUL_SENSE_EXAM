from datetime import datetime, timedelta, timezone
import time
import logging
import secrets
import hashlib
import random
from typing import Optional, Dict, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from ..schemas import UserCreate

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
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
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def check_username_available(self, username: str) -> tuple[bool, str]:
        """
        Check if a username is available for registration.
        Includes normalization, regex validation, reserved list check, and DB lookup.
        """
        import re
        username_norm = username.strip().lower()
        
        # 1. Length check
        if len(username_norm) < 3:
            return False, "Username must be at least 3 characters"
        if len(username_norm) > 20:
            return False, "Username must not exceed 20 characters"
            
        # 2. Regex check
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username_norm):
            return False, "Username must start with a letter and contain only alphanumeric characters and underscores"
            
        # 3. Reserved Words
        reserved = {'admin', 'root', 'support', 'soulsense', 'system', 'official'}
        if username_norm in reserved:
            return False, "This username is reserved"
            
        # 4. DB Lookup
        result = await self.db.execute(select(User).filter(User.username == username_norm))
        if result.scalar_one_or_none():
            return False, "Username is already taken"
            
        return True, "Username is available"

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

    async def authenticate_user(self, identifier: str, password: str, ip_address: str = "0.0.0.0", user_agent: str = "Unknown") -> Optional[User]:
        """
        Authenticate a user by username OR email and password.
        
        Security Features:
        - Constant-time password verification (via bcrypt)
        - Identifier normalization (lowercase)
        - Persistent lockout check with exponential backoff
        - Generic error responses via the caller
        - Failed/Successful login auditing
        """
        # 1. Normalize identifier
        identifier_lower = identifier.lower().strip()

        # 2. Check for Lockout (Pre-Auth)
        is_locked, lockdown_msg, wait_seconds = await self._is_account_locked(identifier_lower)
        if is_locked:
            raise AuthException(
                code=ErrorCode.AUTH_ACCOUNT_LOCKED,
                message=lockdown_msg,
                details={"wait_seconds": wait_seconds} if wait_seconds else None
            )

        # 3. Try fetching by username first
        result = await self.db.execute(select(User).filter(User.username == identifier_lower))
        user = result.scalar_one_or_none()
        
        # 4. If not found, try fetching by email (via PersonalProfile)
        if not user:
            profile_result = await self.db.execute(select(PersonalProfile).filter(PersonalProfile.email == identifier_lower))
            profile = profile_result.scalar_one_or_none()
            if profile:
                user_result = await self.db.execute(select(User).filter(User.id == profile.user_id))
                user = user_result.scalar_one_or_none()
        
        # 5. Timing attack protection: Always hash something even if user not found
        if not user:
            # Dummy verify to consume time
            self.verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="User not found")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )

        # 6. Verify password
        if not self.verify_password(password, user.password_hash):
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="Invalid password")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )
        
        # 6.5 Reactivate account if soft-deleted
        if getattr(user, "is_deleted", False):
            logger.info(f"♻️ Reactivating soft-deleted account: {user.username}")
            user.is_deleted = False
            user.deleted_at = None
            user.is_active = True
        
        # 7. Success - Update last login & Audit
        await self._record_login_attempt(identifier_lower, True, ip_address)
        await self.update_last_login(user.id)
        
        # SoulSense Audit Log
        from app.services.audit_service import AuditService
        # AuditService needs to be async or made to handle AsyncSession
        await AuditService.log_event(
            user.id,
            "LOGIN",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"method": "password", "status": "success"},
            db_session=self.db
        )

        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token."""
        from jose import jwt

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.jwt_algorithm)
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
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.jwt_algorithm)

    async def initiate_2fa_login(self, user: User) -> str:
        """
        Generate OTP, send email, and return pre_auth_token.
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        
        # 1. Generate OTP
        code, _ = await OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=self.db)
        
        # 2. Send Email
        email = None
        profile_result = await self.db.execute(select(PersonalProfile).filter(PersonalProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()
        if profile:
            email = profile.email
            
        if not email:
            logger.error(f"2FA initiated but no email found for user {user.username}")
        else:
            if code:
                await EmailService.send_otp(email, code, "Login Verification")
                await self.db.commit() # Save OTP
        
        # 3. Create Pre-Auth Token
        return self.create_pre_auth_token(user.id)

    async def verify_2fa_login(self, pre_auth_token: str, code: str) -> User:
        """
        Verify pre-auth token and OTP code.
        Returns User if successful, raises AuthException otherwise.
        """
        from jose import jwt, JWTError
        from app.auth.otp_manager import OTPManager
        
        try:
            # 1. Verify Token
            payload = jwt.decode(pre_auth_token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            scope = payload.get("scope")
            
            if not user_id or scope != "pre_auth":
                 raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid token scope")
                 
            # 2. Verify OTP
            user_id_int = int(user_id)
            if not await OTPManager.verify_otp(user_id_int, code, "LOGIN_CHALLENGE", db_session=self.db):
                 raise AuthException(code=ErrorCode.AUTH_INVALID_CREDENTIALS, message="Invalid or expired code")
                 
            # 3. Success - Fetch User
            result = await self.db.execute(select(User).filter(User.id == user_id_int))
            user = result.scalar_one_or_none()
            if not user:
                 raise AuthException(code=ErrorCode.AUTH_USER_NOT_FOUND, message="User not found")
                 
            # Audit success
            await self._record_login_attempt(user.username, True, "0.0.0.0")
            await self.update_last_login(user.id)
            await self.db.commit() # Save OTP used state
            
            return user
            
        except JWTError:
            raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid or expired session")
        except AuthException:
            raise
        except Exception as e:
            logger.error(f"2FA Verify Error: {e}")
            raise AuthException(code=ErrorCode.AUTH_INTERNAL_ERROR, message="Verification failed")

    async def send_2fa_setup_otp(self, user: User) -> bool:
        """Generate and send OTP for 2FA setup."""
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        
        code, _ = await OTPManager.generate_otp(user.id, "2FA_SETUP", db_session=self.db)
        if not code:
            return False
            
        # Get Email
        email = None
        profile_result = await self.db.execute(select(PersonalProfile).filter(PersonalProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()
        if profile:
            email = profile.email
            
        if email:
             await EmailService.send_otp(email, code, "Enable 2FA")
             await self.db.commit()
             return True
        return False

    async def enable_2fa(self, user_id: int, code: str) -> bool:
        """Verify code and enable 2FA."""
        from app.auth.otp_manager import OTPManager
        
        if await OTPManager.verify_otp(user_id, code, "2FA_SETUP", db_session=self.db):
            result = await self.db.execute(select(User).filter(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.is_2fa_enabled = True
                await self.db.commit()
                return True
        return False

    async def disable_2fa(self, user_id: int) -> bool:
        """Disable 2FA for user."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_2fa_enabled = False
            await self.db.commit()
            return True
        return False

    async def update_last_login(self, user_id: int) -> None:
        """
        Update the last_login timestamp for a user.
        Safe against database locks (fail-open).
        """
        try:
            result = await self.db.execute(select(User).filter(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.last_login = datetime.now(timezone.utc).isoformat()
                await self.db.commit()
                logger.info(f"Updated last_login for user_id={user_id}")
        except OperationalError:
            await self.db.rollback()
            logger.warning(f"Could not update last_login for user_id={user_id} due to database lock.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update last_login: {e}")

    async def _is_account_locked(self, username: str) -> Tuple[bool, Optional[str], int]:
        """
        Check if an account is locked based on recent failed attempts.
        Implements progressive lockout with increasing durations.
        """
        thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)

        result = await self.db.execute(
            select(LoginAttempt).filter(
                LoginAttempt.username == username,
                LoginAttempt.is_successful == False,
                LoginAttempt.timestamp >= thirty_mins_ago
            ).order_by(LoginAttempt.timestamp.desc())
        )
        failed_attempts = result.scalars().all()
        count = len(failed_attempts)

        lockout_duration = 0
        if count >= 7:
            lockout_duration = 300
        elif count >= 5:
            lockout_duration = 120
        elif count >= 3:
            lockout_duration = 30

        if lockout_duration > 0:
            last_attempt = failed_attempts[0].timestamp
            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=timezone.utc)

            elapsed = datetime.now(timezone.utc) - last_attempt
            remaining = int(lockout_duration - elapsed.total_seconds())

            if remaining > 0:
                logger.warning(f"Account locked: {username} ({count} failed attempts, {remaining}s remaining)")
                return True, "Too many failed attempts. Try again later.", remaining

        return False, None, 0

    async def _record_login_attempt(self, username: str, success: bool, ip_address: str, reason: Optional[str] = None):
        """Record the login attempt audit log."""
        try:
            attempt = LoginAttempt(
                username=username,
                ip_address=ip_address,
                is_successful=success,
                failure_reason=reason,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(attempt)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record login attempt: {e}")

    async def register_user(self, user_data: 'UserCreate') -> Tuple[bool, Optional[User], str]:
        """
        Register a new user and their personal profile.
        """
        # Timing Jitter
        time.sleep(random.uniform(0.1, 0.3))

        username_lower = user_data.username.lower().strip()
        email_lower = user_data.email.lower().strip()

        result_user = await self.db.execute(select(User).filter(User.username == username_lower))
        existing_username = result_user.scalar_one_or_none()
        
        result_email = await self.db.execute(select(PersonalProfile).filter(PersonalProfile.email == email_lower))
        existing_email = result_email.scalar_one_or_none()

        if existing_username or existing_email:
            logger.info(f"Registration attempt for existing identity: {username_lower} / {email_lower}")
            return True, None, "Account creation initiated. Please check your email for verification link."

        from .security_service import SecurityService
        if SecurityService.is_disposable_email(email_lower):
            return False, None, "Registration with disposable email domains is not allowed"

        try:
            hashed_pw = self.hash_password(user_data.password)
            new_user = User(
                username=username_lower,
                password_hash=hashed_pw
            )
            self.db.add(new_user)
            await self.db.flush()

            new_profile = PersonalProfile(
                user_id=new_user.id,
                email=email_lower,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                age=user_data.age,
                gender=user_data.gender
            )
            self.db.add(new_profile)
            
            await self.db.commit()
            await self.db.refresh(new_user)
            
            return True, new_user, "Registration successful. Please verify your email."
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Registration failed error: {str(e)}")
            return False, None, "An internal error occurred. Please try again later."

    async def create_refresh_token(self, user_id: int, commit: bool = True) -> str:
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
        if commit:
            await self.db.commit()
        
        return token

    async def has_multiple_active_sessions(self, user_id: int) -> bool:
        result = await self.db.execute(
            select(func.count(RefreshToken.id)).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
        )
        active_sessions = result.scalar_one()
        return active_sessions > 1

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Validate a refresh token and return a new access token + new refresh token (Rotation).
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        result = await self.db.execute(
            select(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
        )
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            logger.warning(f"Invalid refresh token attempt: {token_hash[:8]}...")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="Invalid or expired refresh token"
            )
            
        user_result = await self.db.execute(select(User).filter(User.id == db_token.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
             raise AuthException(
                code=ErrorCode.AUTH_INVALID_TOKEN,
                message="User associated with token no longer exists"
            )
        
        try:
            db_token.is_revoked = True
            access_token = self.create_access_token(data={"sub": user.username})
            new_refresh_token = await self.create_refresh_token(user.id, commit=False)
            
            await self.db.commit()
            return access_token, new_refresh_token
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to rotate refresh token for user {db_token.user_id}: {str(e)}")
            raise AuthException(
                code=ErrorCode.AUTH_TOKEN_ROTATION_FAILED,
                message="Token rotation failed. Please try logging in again."
            )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Manually revoke a refresh token (e.g., on logout)."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await self.db.execute(select(RefreshToken).filter(RefreshToken.token_hash == token_hash))
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.is_revoked = True
            await self.db.commit()
            logger.info(f"Revoked refresh token for user_id={db_token.user_id}")

    async def initiate_password_reset(self, email: str) -> tuple[bool, str]:
        """
        Initiate password reset flow.
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService

        try:
            email_lower = email.lower().strip()
            
            profile_result = await self.db.execute(select(PersonalProfile).filter(PersonalProfile.email == email_lower))
            profile = profile_result.scalar_one_or_none()
            user = None
            if profile:
                user_result = await self.db.execute(select(User).filter(User.id == profile.user_id))
                user = user_result.scalar_one_or_none()
            
            if not user:
                time.sleep(secrets.SystemRandom().uniform(0.1, 0.3))
                logger.info(f"Password reset requested for unknown email: {email_lower}")
                return True, "If an account exists with this email, a reset code has been sent."

            code, error = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=self.db)
            
            if not code:
                return False, error or "Too many requests. Please wait."
                
            if await EmailService.send_otp(email_lower, code, "Password Reset"):
                return True, "If an account exists with this email, a reset code has been sent."
            else:
                return False, "Failed to send email. Please try again later."
                
        except Exception as e:
            logger.error(f"Error in initiate_password_reset: {e}")
            return False, "An error occurred. Please try again."

    async def complete_password_reset(self, email: str, otp_code: str, new_password: str) -> tuple[bool, str]:
        """
        Complete password reset flow.
        """
        from app.auth.otp_manager import OTPManager
        from ..utils.weak_passwords import WEAK_PASSWORDS
        
        if new_password.lower() in WEAK_PASSWORDS:
            return False, "This password is too common. Please choose a stronger password."
        
        try:
            email_lower = email.lower().strip()
            
            profile_result = await self.db.execute(select(PersonalProfile).filter(PersonalProfile.email == email_lower))
            profile = profile_result.scalar_one_or_none()
            if not profile:
                return False, "Invalid request."
            
            user_result = await self.db.execute(select(User).filter(User.id == profile.user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                return False, "Invalid request."
                
            if not await OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=self.db):
                return False, "Invalid or expired code."
            
            user.password_hash = self.hash_password(new_password)
            
            await self.db.execute(
                update(RefreshToken).filter(RefreshToken.user_id == user.id).values(is_revoked=True)
            )
            
            await self.db.commit()
            
            logger.info(f"Password reset successfully for user {user.username} (via Web). Sessions invalidated.")
            return True, "Password reset successfully. You can now login."
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error in complete_password_reset: {e}")
            return False, f"Internal error: {str(e)}"


