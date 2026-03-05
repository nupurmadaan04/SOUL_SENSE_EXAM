from datetime import datetime, timedelta, timezone
import asyncio
import time
import logging
import secrets
import hashlib
from typing import Optional, Dict, TYPE_CHECKING, Tuple, List

if TYPE_CHECKING:
    from ..schemas import UserCreate

from fastapi import Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import OperationalError, IntegrityError
import bcrypt

from .db_service import get_db
from ..models import User, LoginAttempt, PersonalProfile, RefreshToken
from ..config import get_settings
from ..constants.errors import ErrorCode
from ..constants.security_constants import BCRYPT_ROUNDS, REFRESH_TOKEN_EXPIRE_DAYS
from ..exceptions import AuthException
from .audit_service import AuditService
from ..utils.db_transaction import transactional, retry_on_transient

settings = get_settings()
logger = logging.getLogger("api.auth")

class AuthService:
    """Service for handling authentication and session management (Async)."""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_username_available(self, username: str) -> tuple[bool, str]:
        """Check if a username is available for registration (Async)."""
        import re
        username_norm = username.strip().lower()
        
        if len(username_norm) < 3:
            return False, "Username must be at least 3 characters"
        if len(username_norm) > 20:
            return False, "Username must not exceed 20 characters"
            
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username_norm):
            return False, "Username must start with a letter and contain only alphanumeric and underscores"
            
        reserved = {'admin', 'root', 'support', 'soulsense', 'system', 'official'}
        if username_norm in reserved:
            return False, "This username is reserved"
            
        stmt = select(User).filter(User.username == username_norm)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            return False, "Username is already taken"
            
        return True, "Username is available"

    async def hash_password(self, password: str) -> str:
        """Hash a password (Offloaded to thread)."""
        def _hash():
            salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            pwd_bytes = password.encode('utf-8')
            return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
        return await asyncio.to_thread(_hash)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password (Offloaded to thread)."""
        def _verify():
            try:
                return bcrypt.checkpw(
                    plain_password.encode('utf-8'), 
                    hashed_password.encode('utf-8')
                )
            except Exception as e:
                logger.error(f"Error verifying password: {e}")
                return False
        return await asyncio.to_thread(_verify)

    async def authenticate_user(self, identifier: str, password: str, ip_address: str = "0.0.0.0", user_agent: str = "Unknown") -> Optional[User]:
        """Authenticate user (Async)."""
        identifier_lower = identifier.lower().strip()

        # Check for Lockout
        is_locked, lockdown_msg, wait_seconds = await self._is_account_locked(identifier_lower)
        if is_locked:
            raise AuthException(
                code=ErrorCode.AUTH_ACCOUNT_LOCKED,
                message=lockdown_msg,
                details={"wait_seconds": wait_seconds} if wait_seconds else None
            )

        # Try fetching by username
        stmt = select(User).filter(User.username == identifier_lower)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        # Try fetching by email
        if not user:
            stmt_p = select(PersonalProfile).filter(PersonalProfile.email == identifier_lower)
            res_p = await self.db.execute(stmt_p)
            profile = res_p.scalar_one_or_none()
            if profile:
                stmt_u = select(User).filter(User.id == profile.user_id)
                res_u = await self.db.execute(stmt_u)
                user = res_u.scalar_one_or_none()
        
        if not user:
            # Timing attack protection
            await self.verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="User not found")
            logger.warning(f"Login failed: User not found {identifier_lower}")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )

        if not await self.verify_password(password, user.password_hash):
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="Invalid password")
            logger.warning(f"Login failed: Invalid password {identifier_lower}")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )
        
        if getattr(user, "is_deleted", False):
            logger.info(f"Reactivating soft-deleted account: {user.username}")
            user.is_deleted = False
            user.deleted_at = None
            user.is_active = True
        
        await self._record_login_attempt(identifier_lower, True, ip_address)
        await self.update_last_login(user.id)
        
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
        """Create JWT access token (Synchronous as it's computation only)."""
        from jose import jwt
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
            
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.jwt_algorithm)

    async def initiate_2fa_login(self, user: User) -> str:
        """Generate OTP and return pre_auth token (Async)."""
        from .otp_manager import OTPManager
        from .email_service import EmailService
        
        code, _ = await OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=self.db)
        
        email = None
        stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()
        if profile:
            email = profile.email
            
        if email and code:
            EmailService.send_otp(email, code, "Login Verification")
            await self.db.commit()
        
        return self.create_pre_auth_token(user.id)

    def create_pre_auth_token(self, user_id: int) -> str:
        """Create temporary 2FA token."""
        from jose import jwt
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        to_encode = {"sub": str(user_id), "exp": expire, "scope": "pre_auth", "type": "2fa_challenge"}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.jwt_algorithm)

    async def verify_2fa_login(self, pre_auth_token: str, code: str, ip_address: str = "0.0.0.0") -> User:
        """Verify 2FA and return User (Async)."""
        from jose import jwt, JWTError
        from .otp_manager import OTPManager
        
        try:
            payload = jwt.decode(pre_auth_token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            user_id = payload.get("sub")
            if not user_id or payload.get("scope") != "pre_auth":
                 raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid token scope")
                 
            user_id_int = int(user_id)
            success, msg = await OTPManager.verify_otp(user_id_int, code, "LOGIN_CHALLENGE", db_session=self.db)
            if not success:
                 raise AuthException(code=ErrorCode.AUTH_INVALID_CREDENTIALS, message=msg)
                 
            stmt = select(User).filter(User.id == user_id_int)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                 raise AuthException(code=ErrorCode.AUTH_USER_NOT_FOUND, message="User not found")
                 
            await self._record_login_attempt(user.username, True, ip_address)
            await self.update_last_login(user.id)
            await AuditService.log_event(user.id, "LOGIN_2FA", ip_address=ip_address, details={"method": "2fa", "status": "success"}, db_session=self.db)
            
            return user
        except JWTError:
            raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid or expired session")

    async def update_last_login(self, user_id: int) -> None:
        """Update last login timestamp (Async)."""
        try:
            stmt = select(User).filter(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.last_login = datetime.now(timezone.utc).isoformat()
                await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update last_login: {e}")

    async def _is_account_locked(self, username: str) -> Tuple[bool, Optional[str], int]:
        """Check progressive lockout (Async)."""
        thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
        stmt = select(LoginAttempt).filter(
            LoginAttempt.username == username,
            LoginAttempt.is_successful == False,
            LoginAttempt.timestamp >= thirty_mins_ago
        ).order_by(desc(LoginAttempt.timestamp))
        
        result = await self.db.execute(stmt)
        failed_attempts = result.scalars().all()
        count = len(failed_attempts)

        lockout_duration = 0
        if count >= 7: lockout_duration = 300
        elif count >= 5: lockout_duration = 120
        elif count >= 3: lockout_duration = 30

        if lockout_duration > 0:
            last_attempt = failed_attempts[0].timestamp
            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=timezone.utc)

            elapsed = datetime.now(timezone.utc) - last_attempt
            remaining = int(lockout_duration - elapsed.total_seconds())
            if remaining > 0:
                return True, "Too many failed attempts. Try again later.", remaining

        return False, None, 0

    async def _record_login_attempt(self, username: str, success: bool, ip_address: str, reason: Optional[str] = None):
        """Record login attempt (Async)."""
        try:
            attempt = LoginAttempt(
                username=username, ip_address=ip_address, is_successful=success,
                failure_reason=reason, timestamp=datetime.now(timezone.utc)
            )
            self.db.add(attempt)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record login attempt: {e}")

    async def register_user(self, user_data: 'UserCreate') -> Tuple[bool, Optional[User], str]:
        """Register a new user (Async)."""
        # Timing Jitter
        await asyncio.sleep(secrets.SystemRandom().uniform(0.1, 0.3))

        username_lower = user_data.username.lower().strip()
        email_lower = user_data.email.lower().strip()

        stmt_u = select(User).filter(User.username == username_lower)
        res_u = await self.db.execute(stmt_u)
        
        stmt_e = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
        res_e = await self.db.execute(stmt_e)

        if res_u.scalar_one_or_none() or res_e.scalar_one_or_none():
            logger.info(f"Registration attempt for existing identity: {username_lower}")
            return True, None, "Account creation initiated. Check email."

        try:
            hashed_pw = await self.hash_password(user_data.password)
            
            new_user = User(username=username_lower, password_hash=hashed_pw)
            self.db.add(new_user)
            await self.db.flush()

            new_profile = PersonalProfile(
                user_id=new_user.id, email=email_lower,
                first_name=user_data.first_name, last_name=user_data.last_name,
                age=user_data.age, gender=user_data.gender
            )
            self.db.add(new_profile)
            await self.db.commit()
            await self.db.refresh(new_user)

            return True, new_user, "Registration successful."
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Registration failed: {e}")
            return False, None, "Internal error."

    async def create_refresh_token(self, user_id: int) -> str:
        """Create refresh token (Async)."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(db_token)
        await self.db.commit()
        return token

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """Rotate refresh token (Async)."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stmt = select(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid refresh token")
            
        stmt_u = select(User).filter(User.id == db_token.user_id)
        res_u = await self.db.execute(stmt_u)
        user = res_u.scalar_one_or_none()
        
        if not user:
             raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="User not found")
        
        try:
            db_token.is_revoked = True
            access_token = self.create_access_token(data={"sub": user.username})
            new_refresh_token = await self.create_refresh_token(user.id)
            return access_token, new_refresh_token
        except Exception as e:
            await self.db.rollback()
            raise AuthException(code=ErrorCode.AUTH_TOKEN_ROTATION_FAILED, message="Rotation failed")

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke refresh token (Async)."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stmt = select(RefreshToken).filter(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.is_revoked = True
            await self.db.commit()

    async def revoke_access_token(self, token: str) -> None:
        """Revoke access token (Async)."""
        from jose import jwt
        from ..root_models import TokenRevocation
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            exp = payload.get("exp")
            if exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                revocation = TokenRevocation(token_str=token, expires_at=expires_at)
                self.db.add(revocation)
                await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to revoke access token: {e}")

    async def initiate_password_reset(self, email: str, background_tasks: BackgroundTasks) -> tuple[bool, str]:
        """Initiate password reset (Async)."""
        from .otp_manager import OTPManager
        from .email_service import EmailService

        try:
            email_lower = email.lower().strip()
            stmt_p = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
            res_p = await self.db.execute(stmt_p)
            profile = res_p.scalar_one_or_none()
            
            if not profile:
                return True, "If an account exists, email sent."

            stmt_u = select(User).filter(User.id == profile.user_id)
            res_u = await self.db.execute(stmt_u)
            user = res_u.scalar_one_or_none()
            
            if not user:
                return True, "If an account exists, email sent."

            code, error = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=self.db)
            if not code:
                return False, error or "Too many requests."
                
            background_tasks.add_task(EmailService.send_otp, email_lower, code, "Password Reset")
            return True, "If an account exists, email sent."
        except Exception as e:
            logger.error(f"Reset Error: {e}")
            return False, "An error occurred."

    async def complete_password_reset(self, email: str, otp_code: str, new_password: str) -> tuple[bool, str]:
        """Complete password reset (Async)."""
        from .otp_manager import OTPManager
        
        try:
            email_lower = email.lower().strip()
            stmt_p = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
            res_p = await self.db.execute(stmt_p)
            profile = res_p.scalar_one_or_none()
            if not profile: return False, "Invalid request."
            
            stmt_u = select(User).filter(User.id == profile.user_id)
            res_u = await self.db.execute(stmt_u)
            user = res_u.scalar_one_or_none()
            if not user: return False, "Invalid request."
                
            success, msg = await OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=self.db)
            if not success: return False, msg
            
            user.password_hash = await self.hash_password(new_password)
            await self.db.execute(update(RefreshToken).filter(RefreshToken.user_id == user.id).values(is_revoked=True))
            await self.db.commit()
            return True, "Password reset successfully."
        except Exception as e:
            await self.db.rollback()
            return False, f"Internal error: {str(e)}"

    async def send_2fa_setup_otp(self, user: User) -> bool:
        """Generate and send OTP for 2FA setup (Async)."""
        from .otp_manager import OTPManager
        from .email_service import EmailService
        
        code, _ = await OTPManager.generate_otp(user.id, "2FA_SETUP", db_session=self.db)
        if not code:
            return False
            
        email = None
        stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()
        if profile:
            email = profile.email
            
        if email:
             EmailService.send_otp(email, code, "Enable 2FA")
             await self.db.commit()
             return True
        return False

    async def enable_2fa(self, user_id: int, code: str) -> bool:
        """Verify code and enable 2FA (Async)."""
        from .otp_manager import OTPManager
        
        success, _ = await OTPManager.verify_otp(user_id, code, "2FA_SETUP", db_session=self.db)
        if success:
            stmt = update(User).where(User.id == user_id).values(is_2fa_enabled=True)
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        return False

    async def disable_2fa(self, user_id: int) -> bool:
        """Disable 2FA for user (Async)."""
        stmt = update(User).where(User.id == user_id).values(is_2fa_enabled=False)
        await self.db.execute(stmt)
        await self.db.commit()
        return True


