import bcrypt
import secrets
import time
from datetime import datetime, timedelta
from app.db import get_session
from app.models import User
import logging

class AuthManager:
    def __init__(self):
        self.current_user = None
        self.session_token = None
        self.session_expiry = None
        self.failed_attempts = {}
        self.lockout_duration = 300  # 5 minutes
    
    def hash_password(self, password):
        """Hash password using bcrypt with configurable rounds (default: 12)."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    def verify_password(self, password, password_hash):
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception as e:
            logging.error(f"Password verification failed: {e}")
            return False
    
    def register_user(self, username, password):
        # Enhanced validation
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not self._validate_password_strength(password):
            return False, "Password must contain uppercase, lowercase, number and special character"
        
        session = get_session()
        try:
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                return False, "Username already exists"
            
            password_hash = self.hash_password(password)
            new_user = User(
                username=username,
                password_hash=password_hash,
                created_at=datetime.utcnow().isoformat()
            )
            session.add(new_user)
            session.commit()
            return True, "Registration successful"
        
        except Exception as e:
            session.rollback()
            logging.error(f"Registration failed: {e}")
            return False, "Registration failed"
        finally:
            session.close()
    
    def login_user(self, username, password):
        # Check rate limiting
        if self._is_locked_out(username):
            return False, "Account temporarily locked due to failed attempts"
            
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            
            if user and self.verify_password(password, user.password_hash):
                user.last_login = datetime.utcnow().isoformat()
                session.commit()
                self.current_user = username
                self._generate_session_token()
                self._reset_failed_attempts(username)
                return True, "Login successful"
            else:
                self._record_failed_attempt(username)
                return False, "Invalid username or password"
        
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False, "Login failed"
        finally:
            session.close()
    
    def logout_user(self):
        self.current_user = None
        self.session_token = None
        self.session_expiry = None
    
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
        """Check if user is locked out due to failed attempts"""
        if username not in self.failed_attempts:
            return False
        attempts, last_attempt = self.failed_attempts[username]
        if attempts >= 5 and (time.time() - last_attempt) < self.lockout_duration:
            return True
        return False
    
    def _record_failed_attempt(self, username):
        """Record failed login attempt"""
        current_time = time.time()
        if username in self.failed_attempts:
            attempts, _ = self.failed_attempts[username]
            self.failed_attempts[username] = (attempts + 1, current_time)
        else:
            self.failed_attempts[username] = (1, current_time)
    
    def _reset_failed_attempts(self, username):
        """Reset failed attempts on successful login"""
        if username in self.failed_attempts:
            del self.failed_attempts[username]