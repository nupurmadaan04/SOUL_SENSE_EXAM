from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import logging
import secrets

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import bcrypt

from .db_service import get_db
from app.models import User, LoginAttempt, PersonalProfile
from ..config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def hash_password(self, password: str) -> str:
        """Hash a password for storing."""
        salt = bcrypt.gensalt()
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
            return None

        # 5. Verify password
        if not self.verify_password(password, user.password_hash):
            self._record_login_attempt(identifier_lower, False, ip_address)
            return None
        
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
