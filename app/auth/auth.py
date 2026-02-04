import bcrypt
import secrets
import time
from datetime import datetime, timedelta
from app.db import get_session
from app.models import User
from app.security_config import PASSWORD_HASH_ROUNDS, LOCKOUT_DURATION_MINUTES
import logging

class AuthManager:
    def __init__(self):
        self.current_user = None
        self.session_token = None
        self.session_expiry = None
        self.session_expiry = None
        self.failed_attempts = {}
        self.lockout_duration = LOCKOUT_DURATION_MINUTES * 60

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
        # Enhanced validation
        if len(username) < 3:
            return False, "Username must be at least 3 characters", "REG003"
        if len(first_name) < 1:
            return False, "First name is required", "REG004"
        if len(password) < 8:
            return False, "Password must be at least 8 characters", "REG005"
        if not self._validate_password_strength(password):
            return False, "Password must contain uppercase, lowercase, number and special character", "REG006"
        if age < 13 or age > 120:
            return False, "Age must be between 13 and 120", "REG007"
        if gender not in ["M", "F", "Other", "Prefer not to say"]:
            return False, "Invalid gender selection", "REG008"

        session = get_session()
        try:
            # 1. Normalize
            username_lower = username.lower().strip()
            email_lower = email.lower().strip()

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
                created_at=datetime.utcnow().isoformat()
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
                last_updated=datetime.utcnow().isoformat()
            )
            session.add(profile)
            
            session.commit()
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
            # Normalize
            id_lower = identifier.lower().strip()

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
                    now_iso = datetime.utcnow().isoformat()
                    user.last_login = now_iso
                    # PR 2: Update last_activity on login (Issue fix)
                    user.last_activity = now_iso
                    
                    # Audit success
                    self._record_login_attempt(session, id_lower, True)
                    session.commit()
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
                    user.last_activity = datetime.utcnow().isoformat()
                    session.commit()
                session.close()
            except Exception as e:
                logging.error(f"Failed to update logout time: {e}")

        self.current_user = None
        self.session_token = None
        self.session_expiry = None
        # Clear saved Remember Me session
        from app.auth import session_storage
        session_storage.clear_session()

    def is_logged_in(self):
        if self.current_user is None:
            return False
        if self.session_expiry and datetime.utcnow() > self.session_expiry:
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
        self.session_expiry = datetime.utcnow() + timedelta(hours=24)

    def _is_locked_out(self, username):
        """Check if user is locked out based on recent failed attempts in DB."""
        session = get_session()
        try:
            from app.models import LoginAttempt
            
            # Count recent failed attempts
            since_time = datetime.utcnow() - timedelta(seconds=self.lockout_duration)
            
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

    def _record_login_attempt(self, session, username, success, reason=None):
        """Record login attempt to DB."""
        try:
            from app.models import LoginAttempt
            attempt = LoginAttempt(
                username=username,
                is_successful=success,
                timestamp=datetime.utcnow(),
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
            if OTPManager.verify_otp(user.id, code, "LOGIN_CHALLENGE", db_session=session):
                # Success!
                user.last_login = datetime.utcnow().isoformat()
                self._record_login_attempt(session, username_lower, True, reason="2fa_success")
                session.commit()
                
                self.current_user = user.username
                self._generate_session_token()
                return True, "Login successful", self.session_token
            else:
                # Failed
                self._record_login_attempt(session, username_lower, False, reason="2fa_failed")
                session.commit()
                return False, "Invalid code", None
                
        except Exception as e:
            session.rollback()
            logging.error(f"2FA Verify Error: {e}")
            return False, "Verification failed", None
        finally:
            session.close()

    def complete_password_reset(self, email, otp_code, new_password):
        """
        Verify OTP and update password.
        """
        from app.auth.otp_manager import OTPManager
        from app.models import PersonalProfile, User
        
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
            if not OTPManager.verify_otp(user.id, otp_code, "RESET_PASSWORD", db_session=session):
                return False, "Invalid or expired code."
            
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
            if OTPManager.verify_otp(user.id, code, "2FA_SETUP", db_session=session):
                user.is_2fa_enabled = True
                session.commit()
                return True, "Two-Factor Authentication Enabled!"
            else:
                return False, "Invalid validation code"
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
            session.commit()
            return True, "Two-Factor Authentication Disabled"
        except Exception as e:
            session.rollback()
            logging.error(f"Disable 2FA Error: {e}")
            return False, f"Error: {str(e)}"
        finally:
            session.close()
