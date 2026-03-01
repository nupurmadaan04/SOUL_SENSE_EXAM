from ..config import get_settings_instance
from datetime import datetime, timedelta, timezone
import time
import logging
import secrets
import hashlib
from typing import Optional, Dict, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from ..schemas import UserCreate

from fastapi import Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import OperationalError
from .audit_service import AuditService
from ..utils.db_transaction import transactional, retry_on_transient
from ..utils.security import get_password_hash, verify_password, is_hashed, check_password_history
from ..utils.race_condition_protection import with_row_lock
from ..models import User, LoginAttempt, PersonalProfile, RefreshToken, PasswordHistory
from ..constants.security_constants import PASSWORD_HISTORY_LIMIT, REFRESH_TOKEN_EXPIRE_DAYS
from .db_router import mark_write

settings = get_settings_instance()

logger = logging.getLogger("api.auth")

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_username_available(self, username: str) -> tuple[bool, str]:
        """
        Check if a username is available for registration.
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
        stmt = select(User).filter(User.username == username_norm)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            return False, "Username is already taken"
            
        return True, "Username is available"


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

        # 3. Try fetching by username first
        stmt = select(User).filter(User.username == identifier_lower).options(selectinload(User.personal_profile))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        # 4. If not found, try fetching by email (via PersonalProfile)
        if not user:
            profile_stmt = select(PersonalProfile).filter(PersonalProfile.email == identifier_lower)
            profile_result = await self.db.execute(profile_stmt)
            profile = profile_result.scalar_one_or_none()
            if profile:
                user_stmt = select(User).filter(User.id == profile.user_id).options(selectinload(User.personal_profile))
                user_result = await self.db.execute(user_stmt)
                user = user_result.scalar_one_or_none()
        
        # 5. Timing attack protection: Always hash something even if user not found
        if not user:
            # Dummy verify to consume time
            verify_password("dummy", "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW")
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="User not found")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )

        # 6. Verify password
        if not verify_password(password, user.password_hash):
            await self._record_login_attempt(identifier_lower, False, ip_address, reason="Invalid password")
            raise AuthException(
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Incorrect username or password"
            )
        
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
            logger.info(f"♻️ Reactivating soft-deleted account: {user.username}")
            user.is_deleted = False
            user.deleted_at = None
            user.is_active = True
        
        # 7. Success - Update last login & Audit
        await self._record_login_attempt(identifier_lower, True, ip_address)
        await self.update_last_login(user.id)
        
        # Comprehensive Audit Log
        await AuditService.log_auth_event(
            'login',
            user.username,
            details={"method": "password", "outcome": "success"},
            ip_address=ip_address,
            user_agent=user_agent,
            db_session=self.db
        )

        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a new JWT access token with unique JTI (#1101) and Tenant ID (#1084)."""
        from jose import jwt
        import uuid

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
            
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
        
        # 3. Create Pre-Auth Token
        return self.create_pre_auth_token(user.id)

    async def verify_2fa_login(self, pre_auth_token: str, code: str, ip_address: str = "0.0.0.0") -> User:
        """Verify pre-auth token and OTP code."""
        from jose import jwt, JWTError
        from .otp_manager import OTPManager
        
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

    async def _is_account_locked(self, username: str) -> Tuple[bool, Optional[str], int]:
        """Check if an account is locked based on recent failed attempts."""
        thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)

        stmt = select(LoginAttempt).filter(
            LoginAttempt.username == username,
            LoginAttempt.is_successful == False,
            LoginAttempt.timestamp >= thirty_mins_ago
        ).order_by(LoginAttempt.timestamp.desc())
        
        result = await self.db.execute(stmt)
        failed_attempts = list(result.scalars().all())

        count = len(failed_attempts)
        lockout_duration = 0
        if count >= 7:
            lockout_duration = 300  # 5 minutes
        elif count >= 5:
            lockout_duration = 120  # 2 minutes
        elif count >= 3:
            lockout_duration = 30   # 30 seconds

        if lockout_duration > 0:
            last_attempt = failed_attempts[0].timestamp
            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(tzinfo=timezone.utc)

            elapsed = datetime.now(timezone.utc) - last_attempt
            remaining = int(lockout_duration - elapsed.total_seconds())

            if remaining > 0:
                logger.warning(f"Account locked", extra={
                    "username": username,
                    "failed_attempts": count,
                    "remaining_seconds": remaining
                })
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

    def register_user(self, user_data: 'UserCreate') -> Tuple[bool, Optional[User], str]:
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
        time.sleep(random.uniform(0.1, 0.3))

        username_lower = user_data.username.lower().strip()
        email_lower = user_data.email.lower().strip()

        try:
            # 1. Validation (Does NOT leak existence if we return generic later)
            # But we still do it for integrity.
            existing_username = self.db.query(User).filter(User.username == username_lower).first()
            existing_email = self.db.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first()

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
            with transactional(self.db):
                new_user = User(
                    username=username_lower,
                    password_hash=hashed_pw
                )
                self.db.add(new_user)
                self.db.flush()  # Populate new_user.id before creating profile

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
            self.db.refresh(new_user)
            
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
            self.db.rollback()
            logger.error(f"Database connection error during registration: {str(e)}")
            return False, None, "Service temporarily unavailable. Please try again later."
        except AttributeError as e:
            logger.error(f"Registration Model Mismatch: {e}")
            return False, None, "A configuration error occurred on the server."
        except Exception as e:
            import traceback
            self.db.rollback()
            logger.error(f"Registration failed error: {str(e)}")
            return False, None, "An internal error occurred. Please try again later."

    async def create_refresh_token(self, user_id: int, commit: bool = True) -> str:
        """Generate a secure refresh token, hash it, and store it in the DB."""
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

    def revoke_access_token(self, token: str) -> None:
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
                self.db.commit()
                logger.info(f"Access token also revoked in database for user: {payload.get('sub')}")

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
            logger.error(f"Error in initiate_password_reset: {e}")
            return False, "An error occurred. Please try again."

    async def complete_password_reset(self, email: str, otp_code: str, new_password: str) -> tuple[bool, str]:
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
            created_at=datetime.now(timezone.utc).isoformat()
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
        
    def parse_name(self, name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Parse full name into first and last."""
        if not name:
            return None, None
        parts = name.split()
        first = parts[0] if parts else None
        last = " ".join(parts[1:]) if len(parts) > 1 else None
        return first, last

import asyncio
