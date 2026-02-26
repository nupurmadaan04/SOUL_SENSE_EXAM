from datetime import datetime, timedelta, UTC, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from app.models import User
from app.models import User, UserSession, PersonalProfile
from app.security_config import PASSWORD_HASH_ROUNDS, LOCKOUT_DURATION_MINUTES, PASSWORD_HISTORY_LIMIT
from app.services.audit_service import AuditService
from app.validation import validate_username, validate_email_strict, validate_password_security
import logging
import bcrypt
import secrets
import time

class AuthManager:
    def __init__(self):
        self.current_user = None
        self.session_token = None
        self.session_expiry = None
        self.current_session_id = None
        self.failed_attempts = {}
        self.lockout_duration = LOCKOUT_DURATION_MINUTES * 60
    
    def _generate_session_id(self):
        """Generate a secure random session ID using secrets module"""
        # Generate a 32-byte (256-bit) secure random token
        return secrets.token_urlsafe(32)

    def hash_password(self, password):
        """Hash password using bcrypt with configurable rounds."""
        salt = bcrypt.gensalt(rounds=PASSWORD_HASH_ROUNDS)
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password, password_hash):
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception as e:
            logging.error(f"Password verification failed: {e}")
            return False

    async def register_user(self, username, email, first_name, last_name, age, gender, password):
        # 1. Centralized Validation (Strict Rules)
        is_valid, error = validate_username(username)
        if not is_valid:
            return False, error, "REG003"
            
        is_valid, error = validate_email_strict(email)
        if not is_valid:
            return False, error, "REG004"
            
        is_valid, error = validate_password_security(password)
        if not is_valid:
            return False, error, "REG005"
            
        if len(first_name) < 1:
            return False, "First name is required", "REG006"
            
        if age < 13 or age > 120:
            return False, "Age must be between 13 and 120", "REG007"
            
        if gender not in ["M", "F", "Other", "Prefer not to say"]:
            return False, "Invalid gender selection", "REG008"

        async with await get_async_session() as session:
            try:
                # 1. Normalize identifiers for security consistency
                username_lower = username.strip().lower()
                email_lower = email.strip().lower()
                logging.debug(f"Registering user: {username_lower}, email: {email_lower}")

                # 2. Check if username already exists
                stmt = select(User).where(User.username == username_lower)
                result = await session.execute(stmt)
                if result.scalars().first():
                    logging.warning(f"Registration failed: Username {username_lower} already taken")
                    return False, "Username already taken", "REG001"

                # 3. Check if email already exists
                from app.models import PersonalProfile
                stmt = select(PersonalProfile).where(PersonalProfile.email == email_lower)
                result = await session.execute(stmt)
                if result.scalars().first():
                    logging.warning(f"Registration failed: Email {email_lower} already registered")
                    return False, "Email already registered", "REG002"

                password_hash = self.hash_password(password)
                
                # 4. Create User
                new_user = User(
                    username=username_lower,
                    password_hash=password_hash,
                    created_at=datetime.now(UTC).isoformat()
                )
                session.add(new_user)
                await session.flush()  # Get the user id
                logging.debug(f"Created user with ID: {new_user.id}")
                
                # 5. Create personal profile
                profile = PersonalProfile(
                    user_id=new_user.id,
                    email=email_lower,
                    first_name=first_name,
                    last_name=last_name,
                    age=age,
                    gender=gender,
                    last_updated=datetime.now(UTC).isoformat()
                )
                session.add(profile)
                
                # Save initial password to history
                await self._save_password_to_history(new_user.id, password_hash, session)
                
                await session.commit()
                logging.debug(f"Committed user and profile for {username_lower}")
                
                # Audit Log
                await AuditService.log_event(new_user.id, "REGISTER", details={"status": "success", "username": username_lower}, db_session=session)
                await session.commit()
                
                logging.info(f"Registration successful for user {username_lower}")
                return True, "Registration successful", None

            except Exception as e:
                await session.rollback()
                logging.error(f"Registration failed for {username}: {e}", exc_info=True)
                return False, "Registration failed", "REG009"

    async def login_user(self, identifier, password):
        # Check rate limiting
        if await self._is_locked_out(identifier):
            return False, "Account temporarily locked due to failed attempts", "AUTH002"

        async with await get_async_session() as session:
            try:
                # Normalize identifier
                id_lower = identifier.strip().lower()

                # 1. Try fetching by username
                stmt = select(User).where(User.username == id_lower)
                result = await session.execute(stmt)
                user = result.scalars().first()

                # 2. If not found, try fetching by email
                if not user:
                    from app.models import PersonalProfile
                    stmt = select(PersonalProfile).where(PersonalProfile.email == id_lower)
                    result = await session.execute(stmt)
                    profile = result.scalars().first()
                    if profile:
                        stmt = select(User).where(User.id == profile.user_id)
                        result = await session.execute(stmt)
                        user = result.scalars().first()

                if user and self.verify_password(password, user.password_hash):
                    # PR 1: Check if account is active
                    if hasattr(user, 'is_active') and not user.is_active:
                        await self._record_login_attempt(session, id_lower, False, reason="account_deactivated")
                        await session.commit()
                        return False, "Account is deactivated. Please contact support.", "AUTH003"

                    # PR 4: 2FA Check
                    if user.is_2fa_enabled:
                        # Resolve email for OTP
                        from app.auth.otp_manager import OTPManager
                        from app.services.email_service import EmailService
                        from app.models import PersonalProfile
                        
                        email_to_send = None
                        if "@" in id_lower:
                             email_to_send = id_lower
                        else:
                             stmt = select(PersonalProfile).where(PersonalProfile.user_id == user.id)
                             result = await session.execute(stmt)
                             profile = result.scalars().first()
                             if profile:
                                 email_to_send = profile.email
                        
                        if not email_to_send:
                            logging.error(f"2FA enabled but no email found for user {user.username}")
                            return False, "2FA Error: Mobile/Email not configured.", "AUTH004"

                        code, _ = await OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=session)
                        if code:
                            EmailService.send_otp(email_to_send, code, "Login Verification")
                            await session.commit()
                            return False, "2FA Verification Required", "AUTH_2FA_REQUIRED"
                        else:
                            await session.rollback()
                            return False, "Failed to generate 2FA code. Please wait.", "AUTH005"

                    # Update last login
                    try:
                        now = datetime.now(timezone.utc)
                        now_iso = now.isoformat()
                        user.last_login = now_iso
                        # PR 2: Update last_ activity on login (Issue fix)
                        user.last_activity = now_iso
                        
                        # Generate unique session ID and create session record
                        session_id = self._generate_session_id()
                        new_session = UserSession(
                            session_id=session_id,
                            user_id=user.id,
                            username=user.username,
                            created_at=now,
                            last_activity=now,
                            is_active=True
                        )
                        session.add(new_session)
                        await self._record_login_attempt(session, id_lower, True)
                        await AuditService.log_event(user.id, "LOGIN", details={"method": "password"}, db_session=session)
                        await session.commit()
                        
                        # Store session ID for this auth instance
                        self.current_session_id = session_id
                    except Exception as e:
                        logging.error(f"Failed to update login metadata: {e}")
                        
                    self.current_user = user.username # Return canonical username
                    self._generate_session_token()
                    return True, "Login successful", None
                else:
                    await self._record_login_attempt(session, id_lower, False, reason="invalid_credentials")
                    await session.commit()
                    return False, "Incorrect username or password", "AUTH001"

            except Exception as e:
                logging.error(f"Login failed: {e}")
                return False, "Internal error occurred", "GLB001"
            finally:
                await session.close()

    async def logout_user(self):
        # PR 2: Update last_activity on logout to capture session end
        if self.current_user:
            try:
                async with await get_async_session() as session:
                    stmt = select(User).where(User.username == self.current_user)
                    result = await session.execute(stmt)
                    user = result.scalars().first()
                    if user:
                        now_iso = datetime.now(UTC).isoformat()
                        user.last_activity = now_iso
                        
                        # Invalidate current session if one exists
                        if self.current_session_id:
                            stmt = select(UserSession).filter_by(
                                session_id=self.current_session_id
                            )
                            result = await session.execute(stmt)
                            user_session = result.scalars().first()
                            if user_session:
                                user_session.is_active = False
                                user_session.logged_out_at = now_iso
                        
                        # Audit Logout
                        await AuditService.log_event(user.id, "LOGOUT", db_session=session)
                        await session.commit()
            except Exception as e:
                logging.error(f"Failed to update logout time: {e}")

        self.current_user = None
        self.session_token = None
        self.session_expiry = None
        self.current_session_id = None
        # Clear saved Remember Me session
        from app.auth import session_storage
        session_storage.clear_session()

    def is_logged_in(self):
        if self.current_user is None:
            return False
        if self.session_expiry and datetime.now(UTC) > self.session_expiry:
            self.logout_user()
            return False
        return True

    def _validate_password_strength(self, password):
        """Validate password contains required character types"""
        import re
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True

    def _generate_session_token(self):
        """Generate secure session token"""
        self.session_token = secrets.token_urlsafe(32)
        self.session_expiry = datetime.now(UTC) + timedelta(hours=24)

    async def _is_locked_out(self, username):
        """Check if user is locked out based on recent failed attempts in DB with progressive lockout."""
        async with await get_async_session() as session:
            try:
                from app.models import LoginAttempt

                # Check failed attempts within the last 30 minutes
                thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)

                stmt = select(LoginAttempt).filter(
                    LoginAttempt.username == username,
                    LoginAttempt.is_successful == False,
                    LoginAttempt.timestamp >= thirty_mins_ago
                ).order_by(LoginAttempt.timestamp.desc())
                
                result = await session.execute(stmt)
                recent_failures = result.scalars().all()

                count = len(recent_failures)

                # Determine if locked out based on attempt count
                if count >= 3:
                    # Find when the last attempt happened
                    last_attempt = recent_failures[0].timestamp
                    if last_attempt.tzinfo is None:
                        last_attempt = last_attempt.replace(tzinfo=timezone.utc)

                    # Determine lockout duration based on count
                    if count >= 7:
                        lockout_duration = 300
                    elif count >= 5:
                        lockout_duration = 120
                    else:  # count >= 3
                        lockout_duration = 30

                    elapsed = datetime.now(timezone.utc) - last_attempt
                    return elapsed.total_seconds() < lockout_duration

                return False
            except Exception as e:
                logging.error(f"Lockout check failed: {e}")
                return False
            finally:
                await session.close()

    async def get_lockout_remaining_seconds(self, username):
        """
        Return seconds remaining in lockout, or 0 if not locked out.
        Used by GUI to display countdown timer.
        """
        async with await get_async_session() as session:
            try:
                from app.models import LoginAttempt

                # Check failed attempts within the last 30 minutes
                thirty_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=30)

                stmt = select(LoginAttempt).filter(
                    LoginAttempt.username == username,
                    LoginAttempt.is_successful == False,
                    LoginAttempt.timestamp >= thirty_mins_ago
                ).order_by(LoginAttempt.timestamp.desc())
                
                result = await session.execute(stmt)
                recent_failures = result.scalars().all()

                count = len(recent_failures)

                if count >= 3:
                    # Get the most recent failed attempt
                    last_attempt = recent_failures[0].timestamp
                    if last_attempt.tzinfo is None:
                        last_attempt = last_attempt.replace(tzinfo=timezone.utc)

                    # Determine lockout duration based on count
                    if count >= 7:
                        lockout_duration = 300
                    elif count >= 5:
                        lockout_duration = 120
                    else:  # count >= 3
                        lockout_duration = 30

                    elapsed = datetime.now(timezone.utc) - last_attempt
                    remaining = lockout_duration - elapsed.total_seconds()
                    return max(0, int(remaining))

                return 0
            except Exception as e:
                logging.error(f"Lockout remaining check failed: {e}")
                return 0
            finally:
                await session.close()

    async def _record_login_attempt(self, session, username, success, reason=None):
        """Record login attempt to DB."""
        try:
            from app.models import LoginAttempt
            attempt = LoginAttempt(
                username=username,
                is_successful=success,
                timestamp=datetime.now(timezone.utc),
                ip_address="desktop",
                failure_reason=reason
            )
            session.add(attempt)
        except Exception as e:
            logging.error(f"Failed to record attempt: {e}")

    # PR 3: Password Reset Flow
    async def initiate_password_reset(self, email):
        """
        Trigger the password reset flow.
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        from app.models import PersonalProfile, User

        async with (await get_async_session()) as session:
            try:
                # Normalize email
                email_lower = email.lower().strip()
                
                # Find user via profile
                stmt = select(PersonalProfile).where(PersonalProfile.email == email_lower)
                result = await session.execute(stmt)
                profile = result.scalars().first()
                
                user = None
                if profile:
                    stmt = select(User).where(User.id == profile.user_id)
                    result = await session.execute(stmt)
                    user = result.scalars().first()
                
                if not user:
                    logging.info(f"Password reset requested for unknown email: {email_lower}")
                    return True, "If an account exists with this email, a reset code has been sent."

                # Generate OTP
                code, error = await OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=session)
                
                if not code:
                    return False, error or "Too many requests. Please wait."
                    
                # Send Email
                if EmailService.send_otp(email_lower, code, "Password Reset"):
                    return True, "If an account exists with this email, a reset code has been sent."
                else:
                    return False, "Failed to send email. Please try again later."
                    
            except Exception as e:
                logging.error(f"Error in initiate_password_reset: {e}")
                return False, "An error occurred. Please try again."

    async def verify_2fa_login(self, username, code):
        """
        Verify the 2FA code and complete the login process.
        Returns: (success, message, session_token)
        """
        from app.auth.otp_manager import OTPManager

        async with (await get_async_session()) as session:
            try:
                # Find User
                username_lower = username.lower().strip()
                stmt = select(User).where(User.username == username_lower)
                result = await session.execute(stmt)
                user = result.scalars().first()
                
                if not user:
                    return False, "User not found", None
                    
                # Verify Code
                success, verify_msg = await OTPManager.verify_otp(user.id, code, "LOGIN_CHALLENGE", db_session=session)
                if success:
                    # Success!
                    user.last_login = datetime.now(UTC).isoformat()
                    await self._record_login_attempt(session, username_lower, True, reason="2fa_success")
                    await AuditService.log_event(user.id, "LOGIN_2FA", details={"method": "totp"}, db_session=session)
                    await session.commit()
                    
                    self.current_user = user.username
                    self._generate_session_token()
                    return True, "Login successful", self.session_token
                else:
                    # Failed
                    await self._record_login_attempt(session, username_lower, False, reason="2fa_failed")
                    await session.commit()
                    return False, verify_msg, None
                    
            except Exception as e:
                await session.rollback()
                logging.error(f"2FA Verify Error: {e}")
                return False, "Verification failed", None

    async def resend_2fa_login_otp(self, username):
        """
        Resend the 2FA login OTP for a user.
        Returns: (success, message)
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        from app.models import PersonalProfile

        async with (await get_async_session()) as session:
            try:
                username_lower = username.lower().strip()
                stmt = select(User).where(User.username == username_lower)
                result = await session.execute(stmt)
                user = result.scalars().first()
                if not user:
                    return False, "User not found."

                stmt = select(PersonalProfile).where(PersonalProfile.user_id == user.id)
                result = await session.execute(stmt)
                profile = result.scalars().first()
                
                email_to_send = profile.email if profile else None
                if not email_to_send:
                    return False, "No email configured for this account."

                code, error = await OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=session)
                if not code:
                    return False, error or "Please wait before requesting a new code."

                if EmailService.send_otp(email_to_send, code, "Login Verification"):
                    return True, "A new verification code has been sent."
                else:
                    return False, "Failed to send email. Please try again."
            except Exception as e:
                logging.error(f"Resend 2FA OTP Error: {e}")
                return False, "An error occurred. Please try again."

    async def complete_password_reset(self, email, otp_code, new_password):
        """
        Verify OTP and update password.
        """
        from app.auth.otp_manager import OTPManager
        from app.models import PersonalProfile, User
        from app.validation import is_weak_password
        
        # Block weak/common passwords
        if is_weak_password(new_password):
            return False, "This password is too common. Please choose a stronger password."
        
        # Validation
        if not self._validate_password_strength(new_password):
            return False, "Password does not meet complexity requirements."
            
        async with (await get_async_session()) as session:
            try:
                email_lower = email.lower().strip()
                
                # Find User
                stmt = select(PersonalProfile).where(PersonalProfile.email == email_lower)
                result = await session.execute(stmt)
                profile = result.scalars().first()
                if not profile:
                    return False, "Invalid request."
                
                stmt = select(User).where(User.id == profile.user_id)
                result = await session.execute(stmt)
                user = result.scalars().first()
                if not user:
                    return False, "Invalid request."
                    
                # Verify OTP
                success, verify_msg = await OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=session)
                if not success:
                    return False, verify_msg
                
                # Check if new password matches current password
                if self.verify_password(new_password, user.password_hash):
                    return False, "New password cannot be the same as your current password."

                # Check password history
                if await self._is_password_in_history(user.id, new_password, session):
                    return False, f"This password was used recently. Please choose a password you haven't used in the last {PASSWORD_HISTORY_LIMIT} changes."

                # Save current password to history before changing
                await self._save_password_to_history(user.id, user.password_hash, session)

                # Update Password
                user.password_hash = self.hash_password(new_password)
                
                # Security: Invalidate tokens
                try:
                    from app.models import RefreshToken
                    from sqlalchemy import update
                    stmt = update(RefreshToken).where(RefreshToken.user_id == user.id).values(is_revoked=True)
                    await session.execute(stmt)
                except Exception as e:
                     logging.warning(f"Could not invalidate sessions during desktop reset: {e}")

                await session.commit()
                logging.info(f"Password reset successfully for user {user.username}")
                
                await AuditService.log_event(user.id, "PASSWORD_RESET", details={"status": "success"}, db_session=session)
                await session.commit()
                
                return True, "Password reset successfully. You can now login."
                
            except Exception as e:
                await session.rollback()
                logging.error(f"Error in complete_password_reset: {e}")
                return False, f"Internal error: {str(e)}"

    async def send_2fa_setup_otp(self, username):
        """Generate and send OTP for 2FA setup."""
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        from app.models import PersonalProfile, User

        async with (await get_async_session()) as session:
            try:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalars().first()
                if not user:
                    return False, "User not found"
                
                # Get email
                stmt = select(PersonalProfile).where(PersonalProfile.user_id == user.id)
                result = await session.execute(stmt)
                profile = result.scalars().first()
                if not profile or not profile.email:
                    return False, "Email not configured in profile. Please update profile first."

                code, error = await OTPManager.generate_otp(user.id, "2FA_SETUP", db_session=session)
                if not code:
                    return False, error or "Failed to generate OTP"

                if EmailService.send_otp(profile.email, code, "2FA Setup"):
                    return True, "Verification code sent to email."
                else:
                    return False, "Failed to send email."
            except Exception as e:
                logging.error(f"2FA Setup Error: {e}")
                return False, f"Error: {str(e)}"

    async def enable_2fa(self, username, code):
        """Verify code and enable 2FA."""
        from app.auth.otp_manager import OTPManager
        from app.models import User

        async with (await get_async_session()) as session:
            try:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalars().first()
                if not user:
                    return False, "User not found"

                # Verify Code
                success, verify_msg = await OTPManager.verify_otp(user.id, code, "2FA_SETUP", db_session=session)
                if success:
                    user.is_2fa_enabled = True
                    await AuditService.log_event(user.id, "2FA_ENABLE", details={"method": "OTP"}, db_session=session)
                    await session.commit()
                    return True, "Two-Factor Authentication Enabled!"
                else:
                    return False, verify_msg
            except Exception as e:
                await session.rollback()
                logging.error(f"Enable 2FA Error: {e}")
                return False, f"Error: {str(e)}"

    async def disable_2fa(self, username):
        """Disable 2FA for user."""
        from app.models import User
        async with (await get_async_session()) as session:
            try:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalars().first()
                if not user:
                    return False, "User not found"

                user.is_2fa_enabled = False
                await AuditService.log_event(user.id, "2FA_DISABLE", db_session=session)
                await session.commit()
                return True, "Two-Factor Authentication Disabled"
            except Exception as e:
                await session.rollback()
                logging.error(f"Disable 2FA Error: {e}")
                return False, f"Error: {str(e)}"

    # ==================== PASSWORD HISTORY ====================

    async def _save_password_to_history(self, user_id, password_hash, db_session):
        """Store a password hash in the user's password history."""
        from app.models import PasswordHistory
        try:
            entry = PasswordHistory(
                user_id=user_id,
                password_hash=password_hash,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(entry)

            # Prune old entries beyond the configured limit
            stmt = select(PasswordHistory).where(
                PasswordHistory.user_id == user_id
            ).order_by(PasswordHistory.created_at.desc())
            
            result = await db_session.execute(stmt)
            history = result.scalars().all()

            if len(history) > PASSWORD_HISTORY_LIMIT:
                for old_entry in history[PASSWORD_HISTORY_LIMIT:]:
                    await db_session.delete(old_entry)
        except Exception as e:
            logging.error(f"Failed to save password history: {e}")

    async def _is_password_in_history(self, user_id, new_password, db_session):
        """Check if a plaintext password matches any of the user's recent password hashes."""
        from app.models import PasswordHistory
        try:
            stmt = select(PasswordHistory).where(
                PasswordHistory.user_id == user_id
            ).order_by(PasswordHistory.created_at.desc()).limit(PASSWORD_HISTORY_LIMIT)
            
            result = await db_session.execute(stmt)
            history = result.scalars().all()

            for entry in history:
                if self.verify_password(new_password, entry.password_hash):
                    return True
            return False
        except Exception as e:
            logging.error(f"Password history check failed: {e}")
            return False

    # ==================== CHANGE PASSWORD ====================

    async def change_password(self, username, current_password, new_password):
        """
        Change password for a logged-in user.
        Validates current password, checks history, and updates.
        Returns: (success: bool, message: str)
        """
        from app.models import User

        # Validate new password strength
        is_valid, error = validate_password_security(new_password)
        if not is_valid:
            return False, error

        async with await get_async_session() as session:
            try:
                id_lower = username.strip().lower()
                stmt = select(User).where(User.username == id_lower)
                result = await session.execute(stmt)
                user = result.scalars().first()

                # If not found by username, try by email (user may have logged in with email)
                if not user:
                    from app.models import PersonalProfile
                    stmt = select(PersonalProfile).where(PersonalProfile.email == id_lower)
                    result = await session.execute(stmt)
                    profile = result.scalars().first()
                    if profile:
                        stmt = select(User).where(User.id == profile.user_id)
                        result = await session.execute(stmt)
                        user = result.scalars().first()

                if not user:
                    return False, "User not found."

                # Verify current password
                if not self.verify_password(current_password, user.password_hash):
                    return False, "Current password is incorrect."

                # Check if new password matches current password
                if self.verify_password(new_password, user.password_hash):
                    return False, f"New password cannot be the same as your current password."

                # Check password history
                if await self._is_password_in_history(user.id, new_password, session):
                    return False, f"This password was used recently. Please choose a password you haven't used in the last {PASSWORD_HISTORY_LIMIT} changes."

                # Save current password to history before changing
                await self._save_password_to_history(user.id, user.password_hash, session)

                # Update password
                user.password_hash = self.hash_password(new_password)

                await AuditService.log_event(user.id, "PASSWORD_CHANGE", details={"status": "success"}, db_session=session)
                await session.commit()

                logging.info(f"Password changed successfully for user {username}")
                return True, "Password changed successfully."

            except Exception as e:
                await session.rollback()
                logging.error(f"Change password failed: {e}")
                return False, "An error occurred while changing your password."
            finally:
                await session.close()
    async def validate_session(self, session_id):
        """
        Validate a session ID and check if it's still active.
        Sessions expire after 24 hours of inactivity.
        
        Args:
            session_id (str): The session ID to validate
            
        Returns:
            tuple: (bool, str, dict|None) - (is_valid, message, session_data)
        """
        async with await get_async_session() as session:
            try:
                stmt = select(UserSession).where(UserSession.session_id == session_id)
                result = await session.execute(stmt)
                user_session = result.scalars().first()
                
                if not user_session:
                    return False, "Invalid session ID", None
                
                if not user_session.is_active:
                    return False, "Session has been terminated", None
                
                # Check if session is expired (24 hours)
                last_accessed = datetime.fromisoformat(user_session.last_accessed)
                if datetime.now(UTC) - last_accessed > timedelta(hours=24):
                    user_session.is_active = False
                    await session.commit()
                    return False, "Session expired", None
                
                # Update last accessed time
                user_session.last_accessed = datetime.now(UTC).isoformat()
                await session.commit()
                
                session_data = {
                    'session_id': user_session.session_id,
                    'username': user_session.username,
                    'user_id': user_session.user_id,
                    'created_at': user_session.created_at,
                    'last_accessed': user_session.last_accessed
                }
                
                return True, "Session valid", session_data
                
            except Exception as e:
                logging.error(f"Session validation error: {e}")
                return False, "Validation error", None
            finally:
                await session.close()
    
    async def cleanup_old_sessions(self, hours=24):
        """
        Remove or mark as inactive sessions older than specified hours.
        """
        async with await get_async_session() as session:
            try:
                cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
                cutoff_iso = cutoff_time.isoformat()
                
                stmt = select(UserSession).filter(
                    UserSession.last_accessed < cutoff_iso,
                    UserSession.is_active == True
                )
                result = await session.execute(stmt)
                old_sessions = result.scalars().all()
                
                count = len(old_sessions)
                for old_session in old_sessions:
                    old_session.is_active = False
                    old_session.logged_out_at = datetime.now(UTC).isoformat()
                
                await session.commit()
                return count
                
            except Exception as e:
                await session.rollback()
                logging.error(f"Cleanup error: {e}")
                return 0
            finally:
                await session.close()
    
    async def get_active_sessions(self, username):
        """
        Get all active sessions for a user.
        """
        async with await get_async_session() as session:
            try:
                stmt = select(UserSession).filter_by(
                    username=username,
                    is_active=True
                )
                result = await session.execute(stmt)
                active_sessions = result.scalars().all()
                
                res = []
                for sess in active_sessions:
                    res.append({
                        'session_id': sess.session_id,
                        'created_at': sess.created_at,
                        'last_accessed': sess.last_accessed,
                        'ip_address': sess.ip_address,
                        'user_agent': sess.user_agent
                    })
                
                return res
                
            except Exception as e:
                logging.error(f"Get sessions error: {e}")
                return []
            finally:
                await session.close()
    
    async def invalidate_user_sessions(self, username):
        """
        Invalidate all active sessions for a user.
        """
        async with await get_async_session() as session:
            try:
                stmt = select(UserSession).filter_by(
                    username=username,
                    is_active=True
                )
                result = await session.execute(stmt)
                active_sessions = result.scalars().all()
                
                count = len(active_sessions)
                now_iso = datetime.now(UTC).isoformat()
                
                for sess in active_sessions:
                    sess.is_active = False
                    sess.logged_out_at = now_iso
                
                await session.commit()
                return count
                
            except Exception as e:
                await session.rollback()
                logging.error(f"Invalidate sessions error: {e}")
                return 0
            finally:
                await session.close()
