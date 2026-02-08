import bcrypt
import secrets
import time
from datetime import datetime, timedelta, UTC, timezone
from app.db import get_session
from app.models import User
from app.security_config import PASSWORD_HASH_ROUNDS, LOCKOUT_DURATION_MINUTES, PASSWORD_HISTORY_LIMIT
from app.models import User, UserSession
from app.security_config import PASSWORD_HASH_ROUNDS, LOCKOUT_DURATION_MINUTES
from app.services.audit_service import AuditService
from app.validation import validate_username, validate_email_strict, validate_password_security
import logging

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

    def register_user(self, username, email, first_name, last_name, age, gender, password):
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

        session = get_session()
        try:
            # 1. Normalize identifiers for security consistency
            username_lower = username.strip().lower()
            email_lower = email.strip().lower()

            # 2. Check if username already exists
            if session.query(User).filter(User.username == username_lower).first():
                return False, "Username already taken", "REG001"

            # 3. Check if email already exists
            from app.models import PersonalProfile
            if session.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first():
                return False, "Email already registered", "REG002"

            password_hash = self.hash_password(password)
            
            # 4. Create User
            new_user = User(
                username=username_lower,
                password_hash=password_hash,
                created_at=datetime.now(UTC).isoformat()
            )
            session.add(new_user)
            session.flush()  # Get the user id
            
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
            self._save_password_to_history(new_user.id, password_hash, session)
            
            session.commit()
            
            # Audit Log
            AuditService.log_event(new_user.id, "REGISTER", details={"status": "success", "username": username_lower}, db_session=session)
            
            return True, "Registration successful", None

        except Exception as e:
            session.rollback()
            logging.error(f"Registration failed: {e}")
            return False, "Registration failed", "REG009"
        finally:
            session.close()

    def login_user(self, identifier, password):
        # Check rate limiting
        if self._is_locked_out(identifier):
            return False, "Account temporarily locked due to failed attempts", "AUTH002"

        session = get_session()
        try:
            # Normalize identifier
            id_lower = identifier.strip().lower()

            # 1. Try fetching by username
            user = session.query(User).filter(User.username == id_lower).first()

            # 2. If not found, try fetching by email
            if not user:
                from app.models import PersonalProfile
                profile = session.query(PersonalProfile).filter(PersonalProfile.email == id_lower).first()
                if profile:
                    user = session.query(User).filter(User.id == profile.user_id).first()

            if user and self.verify_password(password, user.password_hash):
                # PR 1: Check if account is active
                if hasattr(user, 'is_active') and not user.is_active:
                    self._record_login_attempt(session, id_lower, False, reason="account_deactivated")
                    session.commit()
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
                         profile = session.query(PersonalProfile).filter(PersonalProfile.user_id == user.id).first()
                         if profile:
                             email_to_send = profile.email
                    
                    if not email_to_send:
                        logging.error(f"2FA enabled but no email found for user {user.username}")
                        return False, "2FA Error: Mobile/Email not configured.", "AUTH004"

                    code, _ = OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=session)
                    if code:
                        EmailService.send_otp(email_to_send, code, "Login Verification")
                        session.commit()
                        return False, "2FA Verification Required", "AUTH_2FA_REQUIRED"
                    else:
                        session.rollback()
                        return False, "Failed to generate 2FA code. Please wait.", "AUTH005"

                # Update last login
                try:
                    now_iso = datetime.now(UTC).isoformat()
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
                        created_at=now_iso,
                        last_accessed=now_iso,
                        is_active=True
                    )
                    session.add(new_session)
                    
                    # Audit success (Legacy LoginAttempt + New AuditLog)
                    self._record_login_attempt(session, id_lower, True)
                    AuditService.log_event(user.id, "LOGIN", details={"method": "password"}, db_session=session)
                    session.commit()
                    
                    # Store session ID for this auth instance
                    self.current_session_id = session_id
                except Exception as e:
                    logging.error(f"Failed to update login metadata: {e}")
                    
                self.current_user = user.username # Return canonical username
                self._generate_session_token()
                return True, "Login successful", None
            else:
                self._record_login_attempt(session, id_lower, False, reason="invalid_credentials")
                session.commit()
                return False, "Incorrect username or password", "AUTH001"

        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False, "Internal error occurred", "GLB001"
        finally:
            session.close()

    def logout_user(self):
        # PR 2: Update last_activity on logout to capture session end
        if self.current_user:
            try:
                session = get_session()
                user = session.query(User).filter(User.username == self.current_user).first()
                if user:
                    user.last_activity = datetime.now(UTC).isoformat()
                    
                    # Invalidate current session if one exists
                    if self.current_session_id:
                        user_session = session.query(UserSession).filter_by(
                            session_id=self.current_session_id
                        ).first()
                        if user_session:
                            user_session.is_active = False
                            user_session.logged_out_at = datetime.now(UTC).isoformat()
                    
                    user.last_activity = datetime.now(timezone.utc).isoformat()
                    # Audit Logout
                    AuditService.log_event(user.id, "LOGOUT", db_session=session)
                    session.commit()
                session.close()
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

    def _is_locked_out(self, username):
        """Check if user is locked out based on recent failed attempts in DB."""
        session = get_session()
        try:
            from app.models import LoginAttempt
            
            # Count recent failed attempts
            since_time = datetime.now(UTC) - timedelta(seconds=self.lockout_duration)
            # USE TIMEZONE-AWARE DATETIME TO PREVENT CRASH
            since_time = datetime.now(timezone.utc) - timedelta(seconds=self.lockout_duration)
            
            recent_failures = session.query(LoginAttempt).filter(
                LoginAttempt.username == username,
                LoginAttempt.is_successful == False,
                LoginAttempt.timestamp >= since_time
            ).count()
            
            return recent_failures >= 5
        except Exception as e:
            logging.error(f"Lockout check failed: {e}")
            return False
        finally:
            session.close()

    def get_lockout_remaining_seconds(self, username):
        """
        Return seconds remaining in lockout, or 0 if not locked out.
        Used by GUI to display countdown timer.
        """
        session = get_session()
        try:
            from app.models import LoginAttempt
            
            since_time = datetime.now(UTC) - timedelta(seconds=self.lockout_duration)
            
            # Get the most recent failed attempt
            recent_failures = session.query(LoginAttempt).filter(
                LoginAttempt.username == username,
                LoginAttempt.is_successful == False,
                LoginAttempt.timestamp >= since_time
            ).order_by(LoginAttempt.timestamp.desc()).all()
            
            if len(recent_failures) >= 5:
                # Find the 5th most recent failed attempt (the one that triggered lockout)
                fifth_failure = recent_failures[4]
                lockout_end = fifth_failure.timestamp + timedelta(seconds=self.lockout_duration)
                remaining = (lockout_end - datetime.now(UTC)).total_seconds()
                
                # Ensure comparison is done with aware datetimes
                failure_time = fifth_failure.timestamp
                if failure_time.tzinfo is None:
                    failure_time = failure_time.replace(tzinfo=timezone.utc)
                
                lockout_end = failure_time + timedelta(seconds=self.lockout_duration)
                remaining = (lockout_end - datetime.now(timezone.utc)).total_seconds()
                return max(0, int(remaining))
            return 0
        except Exception as e:
            logging.error(f"Lockout remaining check failed: {e}")
            return 0
        finally:
            session.close()

    def _record_login_attempt(self, session, username, success, reason=None):
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
    def initiate_password_reset(self, email):
        """
        Trigger the password reset flow.
        1. Find user by email.
        2. Generate OTP.
        3. Send OTP via EmailService.
        Privacy: Always returns success message to prevent enumeration.
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        from app.models import PersonalProfile, User

        session = get_session()
        try:
            # Normalize email
            email_lower = email.lower().strip()
            
            # Find user via profile
            profile = session.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first()
            user = None
            if profile:
                user = session.query(User).filter(User.id == profile.user_id).first()
            
            # Privacy: If user not found, we still return success-like message,
            # but we don't send anything (or maybe send a generic 'account not found' to that email if we wanted)
            # For now, just logging internal check.
            # Privacy: If user not found, we still return success-like message,
            # but we don't send anything (or maybe send a generic 'account not found' to that email if we wanted)
            # For now, just logging internal check.
            if not user:
                logging.info(f"Password reset requested for unknown email: {email_lower}")
                print(f"DEBUG: User not found for email {email_lower}")
                return True, "If an account exists with this email, a reset code has been sent."

            print(f"DEBUG: User found: {user.username} (ID: {user.id})")

            # Generate OTP
            # Pass session to prevent premature closing of shared session
            code, error = OTPManager.generate_otp(user.id, "RESET_PASSWORD", db_session=session)
            print(f"DEBUG: OTP Generate Result: Code={code}, Error={error}")
            
            if not code:
                # Rate limit hit or error
                return False, error or "Too many requests. Please wait."
                
            # Send Email
            if EmailService.send_otp(email_lower, code, "Password Reset"):
                print(f"DEBUG: EmailService.send_otp returned True")
                return True, "If an account exists with this email, a reset code has been sent."
            else:
                print(f"DEBUG: EmailService.send_otp returned False")
                return False, "Failed to send email. Please try again later."
                
        except Exception as e:
            logging.error(f"Error in initiate_password_reset: {e}")
            return False, "An error occurred. Please try again."
        finally:
            session.close()

    def verify_2fa_login(self, username, code):
        """
        Verify the 2FA code and complete the login process.
        Returns: (success, message, session_token)
        """
        from app.auth.otp_manager import OTPManager

        session = get_session()
        try:
            # Find User
            username_lower = username.lower().strip()
            user = session.query(User).filter(User.username == username_lower).first()
            
            if not user:
                return False, "User not found", None
                
            # Verify Code
            success, verify_msg = OTPManager.verify_otp(user.id, code, "LOGIN_CHALLENGE", db_session=session)
            if success:
                # Success!
                user.last_login = datetime.now(UTC).isoformat()
                self._record_login_attempt(session, username_lower, True, reason="2fa_success")
                AuditService.log_event(user.id, "LOGIN_2FA", details={"method": "totp"}, db_session=session)
                session.commit()
                
                self.current_user = user.username
                self._generate_session_token()
                return True, "Login successful", self.session_token
            else:
                # Failed
                self._record_login_attempt(session, username_lower, False, reason="2fa_failed")
                session.commit()
                return False, verify_msg, None
                
        except Exception as e:
            session.rollback()
            logging.error(f"2FA Verify Error: {e}")
            return False, "Verification failed", None
        finally:
            session.close()

    def resend_2fa_login_otp(self, username):
        """
        Resend the 2FA login OTP for a user.
        Returns: (success, message)
        """
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        from app.models import PersonalProfile

        session = get_session()
        try:
            username_lower = username.lower().strip()
            user = session.query(User).filter(User.username == username_lower).first()
            if not user:
                return False, "User not found."

            profile = session.query(PersonalProfile).filter(PersonalProfile.user_id == user.id).first()
            email_to_send = profile.email if profile else None
            if not email_to_send:
                return False, "No email configured for this account."

            code, error = OTPManager.generate_otp(user.id, "LOGIN_CHALLENGE", db_session=session)
            if not code:
                return False, error or "Please wait before requesting a new code."

            if EmailService.send_otp(email_to_send, code, "Login Verification"):
                return True, "A new verification code has been sent."
            else:
                return False, "Failed to send email. Please try again."
        except Exception as e:
            logging.error(f"Resend 2FA OTP Error: {e}")
            return False, "An error occurred. Please try again."
        finally:
            session.close()

    def complete_password_reset(self, email, otp_code, new_password):
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
            
        session = get_session()
        try:
            email_lower = email.lower().strip()
            
            # Find User
            profile = session.query(PersonalProfile).filter(PersonalProfile.email == email_lower).first()
            if not profile:
                return False, "Invalid request."
            
            user = session.query(User).filter(User.id == profile.user_id).first()
            if not user:
                return False, "Invalid request."
                
            # Verify OTP
            # PASS THE SESSION so OTPManager doesn't close it!
            success, verify_msg = OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=session)
            if not success:
                return False, verify_msg
            
            # Check if new password matches current password
            if self.verify_password(new_password, user.password_hash):
                return False, "New password cannot be the same as your current password."

            # Check password history
            if self._is_password_in_history(user.id, new_password, session):
                return False, f"This password was used recently. Please choose a password you haven't used in the last {PASSWORD_HISTORY_LIMIT} changes."

            # Save current password to history before changing
            self._save_password_to_history(user.id, user.password_hash, session)

            # Update Password
            # Now 'user' is still attached because verify_otp didn't close the session
            print(f"DEBUG: Updating password for user {user.username}")
            user.password_hash = self.hash_password(new_password)
            
            # Security: Invalidate all existing sessions (Refresh Tokens - if they exist from Web usage)
            # Desktop app might not usage these yet, but good practice.
            # Need to import RefreshToken local or root
            # session.query(RefreshToken).filter ...
            # Wait, Desktop app uses `app.models`. Let's assume RefreshToken is there.
            try:
                from app.models import RefreshToken
                session.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({RefreshToken.is_revoked: True})
            except ImportError:
                 # If model doesn't exist broadly or query fails, just log/ignore for desktop-only context
                 pass
            except Exception as e:
                 logging.warning(f"Could not invalidate sessions during desktop reset: {e}")

            session.commit()
            
            # This access should now work because session is still alive (even if commit expired it, it can refresh)
            logging.info(f"Password reset successfully for user {user.username}")
            
            AuditService.log_event(user.id, "PASSWORD_RESET", details={"status": "success"}, db_session=session)
            
            return True, "Password reset successfully. You can now login."
            
        except Exception as e:
            session.rollback()
            logging.error(f"Error in complete_password_reset: {e}")
            print(f"DEBUG Error in complete_password_reset: {e}") 
            return False, f"Internal error: {str(e)}"
        finally:
            session.close()

    def send_2fa_setup_otp(self, username):
        """Generate and send OTP for 2FA setup."""
        from app.auth.otp_manager import OTPManager
        from app.services.email_service import EmailService
        from app.models import PersonalProfile, User

        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return False, "User not found"
            
            # Get email
            profile = session.query(PersonalProfile).filter_by(user_id=user.id).first()
            if not profile or not profile.email:
                return False, "Email not configured in profile. Please update profile first."

            code, error = OTPManager.generate_otp(user.id, "2FA_SETUP", db_session=session)
            if not code:
                return False, error or "Failed to generate OTP"

            if EmailService.send_otp(profile.email, code, "2FA Setup"):
                return True, "Verification code sent to email."
            else:
                return False, "Failed to send email."
        except Exception as e:
            logging.error(f"2FA Setup Error: {e}")
            return False, f"Error: {str(e)}"
        finally:
            session.close()

    def enable_2fa(self, username, code):
        """Verify code and enable 2FA."""
        from app.auth.otp_manager import OTPManager
        from app.models import User

        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return False, "User not found"

            # Verify Code
            success, verify_msg = OTPManager.verify_otp(user.id, code, "2FA_SETUP", db_session=session)
            if success:
                user.is_2fa_enabled = True
                
                AuditService.log_event(user.id, "2FA_ENABLE", details={"method": "OTP"}, db_session=session)
                
                session.commit()
                return True, "Two-Factor Authentication Enabled!"
            else:
                return False, verify_msg
        except Exception as e:
            session.rollback()
            logging.error(f"Enable 2FA Error: {e}")
            return False, f"Error: {str(e)}"
        finally:
            session.close()

    def disable_2fa(self, username):
        """Disable 2FA for user."""
        from app.models import User
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return False, "User not found"

            user.is_2fa_enabled = False
            
            AuditService.log_event(user.id, "2FA_DISABLE", db_session=session)
            
            session.commit()
            return True, "Two-Factor Authentication Disabled"
        except Exception as e:
            session.rollback()
            logging.error(f"Disable 2FA Error: {e}")
            return False, f"Error: {str(e)}"
        finally:
            session.close()

    # ==================== PASSWORD HISTORY ====================

    def _save_password_to_history(self, user_id, password_hash, db_session):
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
            history = db_session.query(PasswordHistory).filter(
                PasswordHistory.user_id == user_id
            ).order_by(PasswordHistory.created_at.desc()).all()

            if len(history) > PASSWORD_HISTORY_LIMIT:
                for old_entry in history[PASSWORD_HISTORY_LIMIT:]:
                    db_session.delete(old_entry)
        except Exception as e:
            logging.error(f"Failed to save password history: {e}")

    def _is_password_in_history(self, user_id, new_password, db_session):
        """Check if a plaintext password matches any of the user's recent password hashes."""
        from app.models import PasswordHistory
        try:
            history = db_session.query(PasswordHistory).filter(
                PasswordHistory.user_id == user_id
            ).order_by(PasswordHistory.created_at.desc()).limit(PASSWORD_HISTORY_LIMIT).all()

            for entry in history:
                if self.verify_password(new_password, entry.password_hash):
                    return True
            return False
        except Exception as e:
            logging.error(f"Password history check failed: {e}")
            return False

    # ==================== CHANGE PASSWORD ====================

    def change_password(self, username, current_password, new_password):
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

        session = get_session()
        try:
            id_lower = username.strip().lower()
            user = session.query(User).filter(User.username == id_lower).first()

            # If not found by username, try by email (user may have logged in with email)
            if not user:
                from app.models import PersonalProfile
                profile = session.query(PersonalProfile).filter(PersonalProfile.email == id_lower).first()
                if profile:
                    user = session.query(User).filter(User.id == profile.user_id).first()

            if not user:
                return False, "User not found."

            # Verify current password
            if not self.verify_password(current_password, user.password_hash):
                return False, "Current password is incorrect."

            # Check if new password matches current password
            if self.verify_password(new_password, user.password_hash):
                return False, f"New password cannot be the same as your current password."

            # Check password history
            if self._is_password_in_history(user.id, new_password, session):
                return False, f"This password was used recently. Please choose a password you haven't used in the last {PASSWORD_HISTORY_LIMIT} changes."

            # Save current password to history before changing
            self._save_password_to_history(user.id, user.password_hash, session)

            # Update password
            user.password_hash = self.hash_password(new_password)

            AuditService.log_event(user.id, "PASSWORD_CHANGE", details={"status": "success"}, db_session=session)
            session.commit()

            logging.info(f"Password changed successfully for user {username}")
            return True, "Password changed successfully."

        except Exception as e:
            session.rollback()
            logging.error(f"Change password failed: {e}")
            return False, "An error occurred while changing your password."
    
    def validate_session(self, session_id):
        """
        Validate a session ID and check if it's still active.
        Sessions expire after 24 hours of inactivity.
        
        Args:
            session_id (str): The session ID to validate
            
        Returns:
            tuple: (bool, str, dict|None) - (is_valid, message, session_data)
        """
        session = get_session()
        try:
            user_session = session.query(UserSession).filter_by(session_id=session_id).first()
            
            if not user_session:
                return False, "Invalid session ID", None
            
            if not user_session.is_active:
                return False, "Session has been terminated", None
            
            # Check if session is expired (24 hours)
            last_accessed = datetime.fromisoformat(user_session.last_accessed)
            if datetime.now(UTC) - last_accessed > timedelta(hours=24):
                user_session.is_active = False
                session.commit()
                return False, "Session expired", None
            
            # Update last accessed time
            user_session.last_accessed = datetime.now(UTC).isoformat()
            session.commit()
            
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
            session.close()
    
    def cleanup_old_sessions(self, hours=24):
        """
        Remove or mark as inactive sessions older than specified hours.
        
        Args:
            hours (int): Age threshold in hours (default: 24)
            
        Returns:
            int: Number of sessions cleaned up
        """
        session = get_session()
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
            cutoff_iso = cutoff_time.isoformat()
            
            old_sessions = session.query(UserSession).filter(
                UserSession.last_accessed < cutoff_iso,
                UserSession.is_active == True
            ).all()
            
            count = len(old_sessions)
            for old_session in old_sessions:
                old_session.is_active = False
                old_session.logged_out_at = datetime.now(UTC).isoformat()
            
            session.commit()
            return count
            
        except Exception as e:
            session.rollback()
            logging.error(f"Cleanup error: {e}")
            return 0
        finally:
            session.close()
    
    def get_active_sessions(self, username):
        """
        Get all active sessions for a user.
        
        Args:
            username (str): Username to query
            
        Returns:
            list: List of active session dictionaries
        """
        session = get_session()
        try:
            active_sessions = session.query(UserSession).filter_by(
                username=username,
                is_active=True
            ).all()
            
            result = []
            for sess in active_sessions:
                result.append({
                    'session_id': sess.session_id,
                    'created_at': sess.created_at,
                    'last_accessed': sess.last_accessed,
                    'ip_address': sess.ip_address,
                    'user_agent': sess.user_agent
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Get sessions error: {e}")
            return []
        finally:
            session.close()
    
    def invalidate_user_sessions(self, username):
        """
        Invalidate all active sessions for a user.
        Useful for forcing re-authentication after password change or security breach.
        
        Args:
            username (str): Username whose sessions to invalidate
            
        Returns:
            int: Number of sessions invalidated
        """
        session = get_session()
        try:
            active_sessions = session.query(UserSession).filter_by(
                username=username,
                is_active=True
            ).all()
            
            count = len(active_sessions)
            now_iso = datetime.now(UTC).isoformat()
            
            for sess in active_sessions:
                sess.is_active = False
                sess.logged_out_at = now_iso
            
            session.commit()
            return count
            
        except Exception as e:
            session.rollback()
            logging.error(f"Invalidate sessions error: {e}")
            return 0
        finally:
            session.close()
