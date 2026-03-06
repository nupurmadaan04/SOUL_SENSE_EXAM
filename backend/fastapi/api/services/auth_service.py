from ..config import get_settings_instance
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
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


settings = get_settings()
logger = logging.getLogger("api.auth")

class AuthService:
    """Service for handling authentication and session management (Async)."""
    
    def __init__(self, db: AsyncSession = Depends(get_db)):
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import OperationalError
from .audit_service import AuditService
from .auth_anomaly_service import AuthAnomalyService
from ..utils.db_transaction import transactional, async_transactional, retry_on_transient
from ..utils.security import get_password_hash, verify_password, is_hashed, check_password_history
from ..utils.race_condition_protection import with_row_lock
from ..utils.timestamps import utc_now_iso
from ..models import User, LoginAttempt, PersonalProfile, RefreshToken, PasswordHistory, UserSession, StepUpToken
from ..constants.security_constants import PASSWORD_HISTORY_LIMIT, REFRESH_TOKEN_EXPIRE_DAYS
from .db_router import mark_write

settings = get_settings()
logger = logging.getLogger("api.auth")

class AuthService:
    """Service for handling authentication and session management (Async)."""
    
settings = get_settings_instance()

logger = logging.getLogger("api.auth")

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_username_available(self, username: str) -> tuple[bool, str]:
        """Check if a username is available for registration (Async)."""
        """
        Check if a username is available for registration.
        """
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
            
        # 4. DB Lookup
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

    async def authenticate_user(self, identifier: str, password: str, ip_address: str = "0.0.0.0", user_agent: str = "Unknown") -> Optional[User]:
        """
        Authenticate a user by username OR email and password.
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

        # Try fetching by username
        stmt = select(User).filter(User.username == identifier_lower)
        # 3. Try fetching by username first
        stmt = select(User).filter(User.username == identifier_lower).options(selectinload(User.personal_profile))
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
            profile_stmt = select(PersonalProfile).filter(PersonalProfile.email == identifier_lower)
            profile_result = await self.db.execute(profile_stmt)
            profile = profile_result.scalar_one_or_none()
            if profile:
                user_stmt = select(User).filter(User.id == profile.user_id).options(selectinload(User.personal_profile))
                user_result = await self.db.execute(user_stmt)
                user = user_result.scalar_one_or_none()
        
        if not user:
            # Timing attack protection
            await self.verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="User not found")
            logger.warning(f"Login failed: User not found {identifier_lower}")
            # Dummy verify to consume time
            self.verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            await self._record_login_attempt(identifier_lower, False, ip_address)
            verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="User not found")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )

        # 5. Verify password
        if not self.verify_password(password, user.password_hash):
            await self._record_login_attempt(identifier_lower, False, ip_address)
        if not await self.verify_password(password, user.password_hash):
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="Invalid password")
            logger.warning(f"Login failed: Invalid password {identifier_lower}")
        # 6. Verify password
        if not verify_password(password, user.password_hash):
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="Invalid password")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )
        
        # 6. Success - Update last login & Audit
        await self._record_login_attempt(identifier_lower, True, ip_address)
        await self.update_last_login(user.id)
        
        # 6.1 Legacy Password Migration (Issue #996)
        # If password was stored in plain text, migrate it to a hash now
        if not is_hashed(user.password_hash):
            logger.info(f"⚡ Migrating legacy plain-text password for user: {user.username}")
            user.password_hash = get_password_hash(password)
            # Log to history too
            self.db.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
            await self.db.commit()
        
        # 6.5 Reactivate account if soft-deleted
        if getattr(user, "is_deleted", False):
            logger.info(f"Reactivating soft-deleted account: {user.username}")
            user.is_deleted = False
            user.deleted_at = None
            user.is_active = True
        
        await self._record_login_attempt(identifier_lower, True, ip_address, user_id=user.id)
        await self.update_last_login(user.id)
        
        # Comprehensive Audit Log
        await AuditService.log_event(
            user.id,
            "LOGIN",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"method": "password", "device_fingerprint": device_fingerprint}
        )
        await self._record_login_attempt(identifier_lower, True, ip_address, user_id=user.id)
        await self.update_last_login(user.id)

        # Anomaly Detection (#1263) - Check for suspicious behavior after successful auth
        try:
            anomaly_service = AuthAnomalyService(self.db)
            risk_score = await anomaly_service.calculate_risk_score(
                user_id=user.id,
                identifier=identifier_lower,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=""  # Could be enhanced with actual fingerprint
            )

            # Log anomalies for monitoring
            if risk_score.risk_level.value in ['medium', 'high', 'critical']:
                from ..services.auth_anomaly_service import AnomalyType
                await anomaly_service.log_anomaly_event(
                    user_id=user.id,
                    anomaly_type=AnomalyType.BRUTE_FORCE if "Brute Force" in str(risk_score.triggered_rules) else AnomalyType.SUSPICIOUS_IP,
                    risk_score=risk_score,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"post_auth_check": True, "successful_login": True}
                )

        except Exception as e:
            logger.error(f"Error in post-auth anomaly detection: {e}")
            # Don't fail authentication if anomaly detection has issues

        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token (Synchronous as it's computation only)."""
        from jose import jwt
        """Create a new JWT access token with unique JTI (#1101) and Tenant ID (#1084)."""
        from jose import jwt
        import uuid

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
        jti = str(uuid.uuid4())
        # Ensure tid is a string for JWT encoding
        tid = to_encode.get("tid")
        if tid and not isinstance(tid, str):
            to_encode["tid"] = str(tid)
            
        to_encode.update({
            "exp": expire,
            "jti": jti
        })
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    def create_pre_auth_token(self, user_id: int) -> str:
        """Create a temporary token for 2FA verification step."""
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
        """Generate OTP, send email, and return pre_auth_token."""
        from .otp_manager import OTPManager
        from .email_service import EmailService
        
        # 1. Generate OTP
        code, _ = await OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=self.db)
        
        # 2. Send Email
        profile_stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
        profile_result = await self.db.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()
        
        email = profile.email if profile else None
            
        if email and code:
            EmailService.send_otp(email, code, "Login Verification")
            await self.db.commit() # Save OTP
        
        return self.create_pre_auth_token(user.id)

    def create_pre_auth_token(self, user_id: int) -> str:
        """Create temporary 2FA token."""
        from jose import jwt
        expire = datetime.now(timezone.utc) + timedelta(minutes=5)
        to_encode = {"sub": str(user_id), "exp": expire, "scope": "pre_auth", "type": "2fa_challenge"}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.jwt_algorithm)

    async def verify_2fa_login(self, pre_auth_token: str, code: str, ip_address: str = "0.0.0.0") -> User:
        """Verify 2FA and return User (Async)."""
    async def verify_2fa_login(self, pre_auth_token: str, code: str, ip_address: str = "0.0.0.0") -> User:
        """Verify pre-auth token and OTP code."""
        from jose import jwt, JWTError
        from .otp_manager import OTPManager
        
        try:
            # 1. Verify Token
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
            
                 
            stmt = select(User).filter(User.id == user_id_int)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                 raise AuthException(code=ErrorCode.AUTH_USER_NOT_FOUND, message="User not found")
                 
            await self._record_login_attempt(user.username, True, ip_address)
            await self.update_last_login(user.id)
            await AuditService.log_event(user.id, "LOGIN_2FA", ip_address=ip_address, details={"method": "2fa", "status": "success"}, db_session=self.db)
            
            if not await OTPManager.verify_otp(user_id_int, code, "LOGIN_CHALLENGE", db_session=self.db):
                 raise AuthException(code=ErrorCode.AUTH_INVALID_CREDENTIALS, message="Invalid or expired code")
                 
            # 3. Success - Fetch User
            user_stmt = select(User).filter(User.id == user_id_int).options(selectinload(User.personal_profile))
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                 raise AuthException(code=ErrorCode.AUTH_USER_NOT_FOUND, message="User not found")
                 
            # Audit success
            await self._record_login_attempt(user.username, True, ip_address)
            await self.update_last_login(user.id)
            
            # SoulSense Audit Log
            await AuditService.log_event(
                user.id,
                "LOGIN_2FA",
                ip_address=ip_address,
                details={"method": "2fa", "status": "success"},
                db_session=self.db
            )
            
            await self.db.commit() # Save OTP used state
            return user
        except JWTError:
            raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid or expired session")

    async def update_last_login(self, user_id: int) -> None:
        """Update last login timestamp (Async)."""
    async def send_2fa_setup_otp(self, user: User) -> bool:
        """Generate and send OTP for 2FA setup."""
        from .otp_manager import OTPManager
        from .email_service import EmailService
        
        code, _ = await OTPManager.generate_otp(user.id, "2FA_SETUP", db_session=self.db)
        if not code:
            return False
            
        profile_stmt = select(PersonalProfile).filter(PersonalProfile.user_id == user.id)
        profile_result = await self.db.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()
            
        if profile and profile.email:
             EmailService.send_otp(profile.email, code, "Enable 2FA")
             await self.db.commit()
             return True
        return False

    async def enable_2fa(self, user_id: int, code: str) -> bool:
        """Verify code and enable 2FA."""
        from .otp_manager import OTPManager
        
        if await OTPManager.verify_otp(user_id, code, "2FA_SETUP", db_session=self.db):
            stmt = select(User).filter(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.is_2fa_enabled = True
                user.version = (getattr(user, 'version', 0) or 1) + 1
                await self.db.commit()
                
                from .cache_service import cache_service
                await cache_service.update_version("user", user.id, user.version)
                await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
                return True
        return False

    async def disable_2fa(self, user_id: int) -> bool:
        """Disable 2FA for user."""
        stmt = select(User).filter(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.is_2fa_enabled = False
            user.version = (getattr(user, 'version', 0) or 1) + 1
            await self.db.commit()
            
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
            return True
        return False

    async def update_last_login(self, user_id: int) -> None:
        """Update the last_login timestamp for a user."""
        try:
            stmt = select(User).filter(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.last_login = datetime.now(timezone.utc).isoformat()
                await self.db.commit()
                user.version = (getattr(user, 'version', 0) or 1) + 1
                await self.db.commit()
                logger.info(f"Updated last_login for user_id={user_id} (v={user.version})")
                
                try:
                    from .cache_service import cache_service
                    await cache_service.update_version("user", user_id, user.version)
                    await mark_write(user.username)
                except Exception as e:
                    logger.warning(f"Failed to record version/mark write in Redis: {e}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update last_login: {e}")

    async def _record_login_attempt(self, username: str, success: bool, ip_address: str):
    async def _is_account_locked(self, username: str) -> Tuple[bool, Optional[str], int]:
        """Check progressive lockout (Async)."""
        thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
        """Check if an account is locked based on recent failed attempts."""
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

    async def _record_login_attempt(self, username: str, success: bool, ip_address: str, reason: Optional[str] = None, user_id: Optional[int] = None):
        """Record login attempt (Async)."""
        """Record the login attempt audit log."""
        try:
            attempt = LoginAttempt(
                user_id=user_id,
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

    async def register_user(self, user_data: 'UserCreate') -> User:
    async def register_user(self, user_data: 'UserCreate') -> Tuple[bool, Optional[User], str]:
        """
        Register a new user and their personal profile.
        Standardizes identifiers and validates uniqueness.

        Security:
        - Generic status return to prevent enumeration.
        - Timing jitter to prevent response-time analysis.
        """
        import time
        import random
        from ..exceptions import APIException
        from ..constants.errors import ErrorCode
        from sqlalchemy.exc import OperationalError, DatabaseError

        # Timing Jitter: Artificial delay baseline (100-300ms)
        # This masks the difference between a DB hit (fast) and a bcrypt hash (slowish)
        # Though bcrypt is ~100ms+, so we just add a bit of noise.
        await asyncio.sleep(random.uniform(0.1, 0.3))

        username_lower = user_data.username.lower().strip()
        email_lower = user_data.email.lower().strip()

        stmt_u = select(User).filter(User.username == username_lower)
        res_u = await self.db.execute(stmt_u)
        
        stmt_e = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
        res_e = await self.db.execute(stmt_e)

        if res_u.scalar_one_or_none() or res_e.scalar_one_or_none():
            logger.info(f"Registration attempt for existing identity: {username_lower}")
            return True, None, "Account creation initiated. Check email."

        # 3. Disposable Email Check
        from .security_service import SecurityService
        if SecurityService.is_disposable_email(email_lower):
            raise APIException(
                code=ErrorCode.REG_DISPOSABLE_EMAIL,
                message="Registration with disposable email domains is not allowed",
                status_code=status.HTTP_400_BAD_REQUEST
            )

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
            self.db.refresh(new_user)
            return new_user
            await self.db.commit()
            await self.db.refresh(new_user)

            return True, new_user, "Registration successful."
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Registration failed: {e}")
            return False, None, "Internal error."

    async def create_refresh_token(self, user_id: int) -> str:
        """
        Generate a secure refresh token, hash it, and store it in the DB.
        """
        """Create refresh token (Async)."""
        try:
            # 1. Validation (Does NOT leak existence if we return generic later)
            # But we still do it for integrity.
            from sqlalchemy import select
            stmt = select(User).filter(User.username == username_lower)
            result = await self.db.execute(stmt)
            existing_username = result.scalar_one_or_none()
            
            stmt = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
            result = await self.db.execute(stmt)
            existing_email = result.scalar_one_or_none()

            if existing_username or existing_email:
                # ENUMERATION PROTECTION:
                # We don't raise an error. We return "Success" but don't create.
                # In a real app, we would send an "Already registered" email here.
                logger.info(f"Registration attempt for existing identity: {username_lower} / {email_lower}")
                return True, None, "Account creation initiated. Please check your email for verification link."

            # 2. Disposable Email Check (This remains an error as it's a policy failure, not enumeration)
            from .security_service import SecurityService
            if SecurityService.is_disposable_email(email_lower):
                return False, None, "Registration with disposable email domains is not allowed"

            hashed_pw = self.hash_password(user_data.password)

            # ── ATOMIC WRITE ─────────────────────────────────────────────────
            # User + PersonalProfile must both succeed or neither persists.
            # A failure mid-way (e.g. FK violation, DB crash) would otherwise
            # leave an orphan User row with no associated PersonalProfile.
            async with async_transactional(self.db):
                new_user = User(
                    username=username_lower,
                    password_hash=hashed_pw
                )
                self.db.add(new_user)
                await self.db.flush()  # Populate new_user.id before creating profile

                new_profile = PersonalProfile(
                    user_id=new_user.id,
                    email=email_lower,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    age=user_data.age,
                    gender=user_data.gender
                )
                self.db.add(new_profile)
            # ─────────────────────────────────────────────────────────────────

            # Refresh to get the latest data after transaction commit
            await self.db.refresh(new_user)
            
            # CONSISTENCY: Ensure initial version (1) is in Redis truth mapping (#1143)
            try:
                from .cache_service import cache_service
                await cache_service.update_version("user", new_user.id, new_user.version)
                await mark_write(new_user.username)
            except Exception as e:
                logger.warning(f"Failed to seed version/mark write in Redis: {e}")
            
            return True, new_user, "Registration successful. Please verify your email."
        except (OperationalError, DatabaseError) as e:
            # Handle database connection/operational errors
            await self.db.rollback()
            logger.error(f"Database connection error during registration: {str(e)}")
            return False, None, "Service temporarily unavailable. Please try again later."
        except AttributeError as e:
            logger.error(f"Registration Model Mismatch: {e}")
            return False, None, "A configuration error occurred on the server."
        except Exception as e:
            import traceback
            await self.db.rollback()
            logger.error(f"Registration failed error: {str(e)}")
            return False, None, "An internal error occurred. Please try again later."

    async def create_refresh_token(self, user_id: int, commit: bool = True) -> str:
        """Generate a secure refresh token, hash it, and store it in the DB."""
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

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke refresh token (Async)."""
        if commit:
            await self.db.commit()
        return token

    async def has_multiple_active_sessions(self, user_id: int) -> bool:
        stmt = select(func.count(RefreshToken.id)).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        return (result.scalar() or 0) > 1

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """Validate a refresh token and return a new access token + new refresh token (Rotation)."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        # Use row-level locking to prevent concurrent refresh operations
        async with self.db.begin():
            # Lock the refresh token row to prevent concurrent operations
            lock_stmt = text("""
                SELECT id FROM refresh_tokens
                WHERE token_hash = :token_hash AND is_revoked = false AND expires_at > NOW()
                FOR UPDATE
            """)
            await self.db.execute(lock_stmt, {"token_hash": token_hash})

            # Now check if token exists and is valid
            stmt = select(RefreshToken).filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc)
            )
            result = await self.db.execute(stmt)
            db_token = result.scalar_one_or_none()

            if not db_token:
                raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="Invalid or expired refresh token")

            user_stmt = select(User).filter(User.id == db_token.user_id)
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user:
                 raise AuthException(code=ErrorCode.AUTH_INVALID_TOKEN, message="User not found")

            try:
                # ── ATOMIC TOKEN ROTATION ────────────────────────────────────────
                # Revocation of the old token and creation of the new one must be
                # committed as a single unit.  If the commit fails after revocation
                # but before the new token is stored, the user would be logged out
                # with no valid refresh token to recover from.
                # Revoke current token
                db_token.is_revoked = True

                # Create new tokens (added to session but not committed yet)
                access_token = self.create_access_token(data={"sub": user.username})
                new_refresh_token = self.create_refresh_token(user.id, commit=False)
                # ─────────────────────────────────────────────────────────────────

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
        """Manually revoke a refresh token."""
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
    async def revoke_access_token(self, token: str) -> None:
        """Revoke an access token by adding it to the Redis blacklist."""
        try:
            # Use Redis blacklist for fast lookups
            from ..utils.jwt_blacklist import get_jwt_blacklist
            blacklist = get_jwt_blacklist()

            # Blacklist in Redis (async operation, but we'll make it sync for now)
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(blacklist.blacklist_token(token))
            loop.close()

            if success:
                logger.info(f"Access token blacklisted in Redis")
            else:
                logger.warning("Failed to blacklist token in Redis, falling back to database")

            # Also store in database as backup (for tokens without JTI)
            from jose import jwt
            from ..root_models import TokenRevocation
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

        except Exception as e:
            logger.error(f"Failed to revoke access token: {e}")
            # Don't raise exception - logout should succeed even if revocation fails
    




    async def initiate_password_reset(self, email: str, background_tasks: BackgroundTasks) -> tuple[bool, str]:
        """Initiate password reset flow."""
        from .otp_manager import OTPManager
        from .email_service import EmailService

        GENERIC_SUCCESS_MSG = "If an account with that email exists, we have sent a reset link to it."
        try:
            email_lower = email.lower().strip()
            profile_stmt = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
            profile_res = await self.db.execute(profile_stmt)
            profile = profile_res.scalar_one_or_none()
            
            if not profile:
                return True, GENERIC_SUCCESS_MSG

            code, error = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=self.db)
            if not code:
                return False, error or "Too many requests."
                
            background_tasks.add_task(EmailService.send_otp, email_lower, code, "Password Reset")
            return True, "If an account exists, email sent."
            user_stmt = select(User).filter(User.id == profile.user_id)
            user_res = await self.db.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            
            if not user:
                return True, GENERIC_SUCCESS_MSG

            code, error = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=self.db)
            if not code:
                return False, error or "Too many requests. Please wait."
                
            background_tasks.add_task(EmailService.send_otp, email_lower, code, "Password Reset")
            return True, GENERIC_SUCCESS_MSG
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


        """Complete password reset flow."""
        from .otp_manager import OTPManager
        from ..utils.weak_passwords import WEAK_PASSWORDS
        
        if new_password.lower() in WEAK_PASSWORDS:
            return False, "This password is too common."
        
        try:
            email_lower = email.lower().strip()
            profile_stmt = select(PersonalProfile).filter(PersonalProfile.email == email_lower)
            profile_res = await self.db.execute(profile_stmt)
            profile = profile_res.scalar_one_or_none()
            
            if not profile:
                return False, "Invalid request."
            
            user_stmt = select(User).filter(User.id == profile.user_id)
            user_res = await self.db.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            
            if not user:
                return False, "Invalid request."
                
            if not await OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=self.db):
                return False, "Invalid or expired code."
            
            # Check password history
            from sqlalchemy import desc
            stmt = select(PasswordHistory.password_hash).filter(
                PasswordHistory.user_id == user.id
            ).order_by(desc(PasswordHistory.created_at)).limit(PASSWORD_HISTORY_LIMIT)
            result = await self.db.execute(stmt)
            history = result.scalars().all()
            
            if check_password_history(new_password, history):
                return False, f"Cannot reuse any of your last {PASSWORD_HISTORY_LIMIT} passwords."

            user.password_hash = get_password_hash(new_password)
            user.version = (getattr(user, 'version', 0) or 1) + 1
            self.db.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
            await self.db.execute(
                update(RefreshToken).filter(RefreshToken.user_id == user.id).values(is_revoked=True)
            )
            await self.db.commit()
            
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
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


    async def get_or_create_oauth_user(self, user_info: dict) -> User:
        """Get or create user from OAuth info."""
        sub = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")
        
        if not sub:
            raise ValueError("Missing 'sub' in user info")
        
        stmt = select(User).filter(User.oauth_sub == sub)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            return user
        
        if email:
            profile_stmt = select(PersonalProfile).filter(PersonalProfile.email == email.lower())
            profile_res = await self.db.execute(profile_stmt)
            profile = profile_res.scalar_one_or_none()
            if profile:
                user_stmt = select(User).filter(User.id == profile.user_id)
                user_res = await self.db.execute(user_stmt)
                user = user_res.scalar_one_or_none()
                if user:
                    user.oauth_sub = sub
                    user.version = (getattr(user, 'version', 0) or 1) + 1
                    await self.db.commit()
                    
                    from .cache_service import cache_service
                    await cache_service.update_version("user", user.id, user.version)
                    await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
                    return user
        
        username = await self.generate_oauth_username(email or sub)
        first_name, last_name = self.parse_name(name)
        
        user = User(
            username=username,
            password_hash="",
            oauth_sub=sub,
            created_at=utc_now_iso()
        )
        self.db.add(user)
        await self.db.flush()
        
        profile = PersonalProfile(
            user_id=user.id,
            email=email.lower() if email else None,
            first_name=first_name,
            last_name=last_name
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
        return username
    
    async def logout(self, token: str, db: AsyncSession):
        """Revoke the current access token on logout (#1101)."""
        from jose import jwt, JWTError
        from .revocation_service import revocation_service
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # Convert exp timestamp to datetime
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                await revocation_service.revoke_token(jti, expires_at, db)
                logger.info(f"Token {jti} revoked successfully on logout")
                return True
        except JWTError:
            pass # Token already invalid
        except Exception as e:
            logger.error(f"Error during logout revocation: {e}")
            
        return False
        
    async def create_user_session(
        self,
        user_id: int,
        username: str,
        ip_address: str,
        user_agent: str,
        device_fingerprint: 'DeviceFingerprint',
        db_session: AsyncSession
    ) -> str:
        """
        Create a new user session with device fingerprinting (#1230).
        
        Returns the session ID for use in JWT tokens.
        """
        import uuid
        from ..utils.device_fingerprinting import DeviceFingerprint
        
        session_id = str(uuid.uuid4())
        
        # Create new session
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint_hash=device_fingerprint.fingerprint_hash,
            device_user_agent=device_fingerprint.user_agent,
            device_accept_language=device_fingerprint.accept_language,
            device_accept_encoding=device_fingerprint.accept_encoding,
            device_screen_resolution=device_fingerprint.screen_resolution,
            device_timezone_offset=device_fingerprint.timezone_offset,
            device_platform=device_fingerprint.platform,
            device_plugins_hash=device_fingerprint.plugins,
            device_canvas_fingerprint=device_fingerprint.canvas_fingerprint,
            device_webgl_fingerprint=device_fingerprint.webgl_fingerprint,
            device_fingerprint_created_at=device_fingerprint.created_at,
            is_active=True
        )
        
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)
        
        logger.info(f"Created session {session_id} for user {username} with device fingerprint")
        
        return session_id
        
    async def initiate_step_up_auth(
        self, 
        user: User, 
        session_id: str, 
        purpose: str,
        ip_address: str = "0.0.0.0",
        user_agent: str = "Unknown"
    ) -> str:
        """
        Initiate step-up authentication for privileged actions (#1245).
        
        Creates a time-bound token that requires 2FA verification for sensitive operations.
        
        Args:
            user: The authenticated user requesting step-up auth
            session_id: Current active session ID
            purpose: Description of the privileged action (e.g., "delete_account")
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Step-up token for verification
            
        Raises:
            ValueError: If user doesn't have 2FA enabled
        """
        if not user.is_2fa_enabled:
            raise ValueError("Step-up authentication requires 2FA to be enabled")
            
        # Generate secure token
        step_up_token = secrets.token_urlsafe(32)
        
        # Create step-up token record (expires in 10 minutes)
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        
        step_up_record = StepUpToken(
            token=step_up_token,
            user_id=user.id,
            session_id=session_id,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(step_up_record)
        await self.db.commit()
        
        logger.info(f"Step-up auth initiated for user {user.username}, purpose: {purpose}")
        
        return step_up_token
    
    async def verify_step_up_auth(
        self, 
        step_up_token: str, 
        otp_code: str,
        ip_address: str = "0.0.0.0"
    ) -> bool:
        """
        Verify step-up authentication token with OTP code (#1245).
        
        Args:
            step_up_token: The step-up token from initiation
            otp_code: 6-digit OTP code from user's authenticator
            ip_address: Client IP address for audit logging
            
        Returns:
            True if verification successful
            
        Raises:
            ValueError: If token is invalid, expired, or already used
        """
        # Find the step-up token
        stmt = select(StepUpToken).filter(
            StepUpToken.token == step_up_token,
            StepUpToken.is_used == False
        )
        result = await self.db.execute(stmt)
        token_record = result.scalar_one_or_none()
        
        if not token_record:
            logger.warning(f"Invalid or used step-up token attempted: {step_up_token[:8]}...")
            raise ValueError("Invalid step-up token")
            
        # Check expiration
        if datetime.now(UTC) > token_record.expires_at:
            logger.warning(f"Expired step-up token attempted for user {token_record.user_id}")
            raise ValueError("Step-up token has expired")
            
        # Get user for 2FA verification
        stmt = select(User).filter(User.id == token_record.user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_2fa_enabled or not user.otp_secret:
            raise ValueError("User 2FA configuration invalid")
            
        # Verify OTP code
        import pyotp
        totp = pyotp.TOTP(user.otp_secret)
        
        if not totp.verify(otp_code, valid_window=1):  # Allow 30-second window
            logger.warning(f"Invalid OTP code for step-up auth, user {user.username}")
            raise ValueError("Invalid OTP code")
            
        # Mark token as used
        token_record.is_used = True
        token_record.used_at = datetime.now(UTC)
        
        await self.db.commit()
        
        logger.info(f"Step-up auth verified for user {user.username}, purpose: {token_record.purpose}")
        
        return True
    
    async def check_step_up_auth_valid(
        self, 
        user_id: int, 
        session_id: str, 
        purpose: str,
        max_age_minutes: int = 30
    ) -> bool:
        """
        Check if user has valid step-up authentication for a specific purpose.
        
        Args:
            user_id: User ID
            session_id: Current session ID
            purpose: The privileged action purpose
            max_age_minutes: Maximum age of valid step-up auth (default 30 minutes)
            
        Returns:
            True if user has valid step-up auth for this purpose/session
        """
        cutoff_time = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        
        stmt = select(StepUpToken).filter(
            StepUpToken.user_id == user_id,
            StepUpToken.session_id == session_id,
            StepUpToken.purpose == purpose,
            StepUpToken.is_used == True,
            StepUpToken.used_at >= cutoff_time
        ).order_by(StepUpToken.used_at.desc()).limit(1)
        
        result = await self.db.execute(stmt)
        recent_token = result.scalar_one_or_none()
        
        return recent_token is not None
        
    def parse_name(self, name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Parse full name into first and last."""
        if not name:
            return None, None
        parts = name.split()
        first = parts[0] if parts else None
        last = " ".join(parts[1:]) if len(parts) > 1 else None
        return first, last

import asyncio
