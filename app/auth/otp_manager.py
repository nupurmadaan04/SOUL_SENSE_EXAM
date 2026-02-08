import hashlib
import secrets
import logging
from datetime import datetime, timedelta, UTC
from app.db import get_session
from app.models import OTP, User

logger = logging.getLogger(__name__)

from typing import Optional

class OTPManager:
    """
    Manages generation, storage, and verification of One-Time Passwords.
    Implements rate limiting, secure hashing, expiry, and attempt locking.
    """
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    MAX_VERIFY_ATTEMPTS = 3
    RATE_LIMIT_SECONDS = 60
    
    @staticmethod
    def _hash_code(code: str) -> str:
        """Securely hash the OTP code for storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    @classmethod
    def generate_otp(cls, user_id: int, purpose: str, db_session=None) -> tuple[Optional[str], Optional[str]]:
        """
        Generate a new OTP for a user.
        
        Args:
            user_id: The user ID
            purpose: The type of OTP (e.g., 'RESET_PASSWORD')
            db_session: Optional existing DB session to use
            
        Returns:
            tuple: (raw_code, error_message)
        """
        session = db_session if db_session else get_session()
        # Track if we own the session and should close it
        should_close = db_session is None
        
        try:
            # 1. Rate Limiting Check
            last_otp = session.query(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose
            ).order_by(OTP.created_at.desc()).first()
            
            if last_otp:
                time_since = datetime.utcnow() - last_otp.created_at
                if time_since.total_seconds() < cls.RATE_LIMIT_SECONDS:
                    return None, f"Please wait {cls.RATE_LIMIT_SECONDS - int(time_since.total_seconds())}s before requesting a new code."

            # 2. Generate Secure Code
            digits = "0123456789"
            code = "".join(secrets.choice(digits) for _ in range(cls.OTP_LENGTH))
            code_hash = cls._hash_code(code)
            
            # 3. Store in DB
            new_otp = OTP(
                user_id=user_id,
                code_hash=code_hash,
                type=purpose,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=cls.OTP_EXPIRY_MINUTES),
                is_used=False,
                attempts=0,
                is_locked=False
            )
            session.add(new_otp)
            # Only commit if we own the session or if explicitly needed?
            # Ideally verify_otp commits its own change. 
            # But generate_otp needs to save the OTP.
            session.commit()
            
            logger.info(f"Generated OTP for user {user_id} (Type: {purpose})")
            return code, None
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to generate OTP: {e}")
            return None, "Internal error generating code."
        finally:
            if should_close:
                session.close()

    @classmethod
    def is_otp_locked(cls, user_id: int, purpose: str, db_session=None) -> tuple[bool, str]:
        """
        Check if the OTP is locked due to too many failed attempts.
        
        Returns:
            tuple: (is_locked, message)
        """
        session = db_session if db_session else get_session()
        should_close = db_session is None
        
        try:
            otp = session.query(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow()
            ).order_by(OTP.created_at.desc()).first()
            
            if not otp:
                return False, "No active OTP found."
            
            if otp.is_locked:
                return True, "Too many failed attempts. Please request a new code."
            
            if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                otp.is_locked = True
                session.commit()
                return True, "Too many failed attempts. Please request a new code."
            
            return False, f"{cls.MAX_VERIFY_ATTEMPTS - otp.attempts} attempts remaining."
            
        except Exception as e:
            logger.error(f"Error checking OTP lock status: {e}")
            return False, "Error checking OTP status."
        finally:
            if should_close:
                session.close()

    @classmethod
    def get_cooldown_remaining(cls, user_id: int, purpose: str, db_session=None) -> int:
        """
        Return remaining cooldown seconds before a new OTP can be requested.
        Returns 0 if no cooldown is active.
        """
        session = db_session if db_session else get_session()
        should_close = db_session is None
        try:
            last_otp = session.query(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose
            ).order_by(OTP.created_at.desc()).first()

            if last_otp:
                time_since = datetime.utcnow() - last_otp.created_at
                remaining = cls.RATE_LIMIT_SECONDS - int(time_since.total_seconds())
                return max(0, remaining)
            return 0
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return 0
        finally:
            if should_close:
                session.close()

    @classmethod
    def get_remaining_attempts(cls, user_id: int, purpose: str, db_session=None) -> int:
        """
        Return remaining verification attempts for the current OTP.
        Returns 0 if no active OTP or OTP is locked.
        """
        session = db_session if db_session else get_session()
        should_close = db_session is None
        
        try:
            otp = session.query(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose,
                OTP.is_used == False,
                OTP.is_locked == False,
                OTP.expires_at > datetime.utcnow()
            ).order_by(OTP.created_at.desc()).first()
            
            if not otp:
                return 0
            
            remaining = max(0, cls.MAX_VERIFY_ATTEMPTS - otp.attempts)
            return remaining
            
        except Exception as e:
            logger.error(f"Error getting remaining attempts: {e}")
            return 0
        finally:
            if should_close:
                session.close()

    @classmethod
    def verify_otp(cls, user_id: int, code: str, purpose: str, db_session=None) -> tuple[bool, str]:
        """
        Verify an OTP code.
        INVALIDATES the OTP if successful (is_used=True).
        Increments attempt count on failure.
        Locks OTP after MAX_VERIFY_ATTEMPTS failed attempts.
        
        Returns:
            tuple: (success, message)
        """
        session = db_session if db_session else get_session()
        should_close = db_session is None
        
        try:
            input_hash = cls._hash_code(code)
            
            # Find the valid OTP
            otp = session.query(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow()
            ).order_by(OTP.created_at.desc()).first()
            
            if not otp:
                logger.info(f"OTP verification failed: No valid code found for user {user_id}")
                return False, "Invalid or expired code."
                
            # Check if already locked
            if otp.is_locked:
                logger.warning(f"OTP verification blocked: OTP is locked for user {user_id}")
                return False, "Too many failed attempts. Please request a new code."
                
            # Check attempts and lock if needed
            if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                otp.is_locked = True
                session.commit()
                logger.warning(f"OTP verification blocked: Max attempts exceeded for user {user_id}")
                return False, "Too many failed attempts. Please request a new code."
                
            # Verify Hash
            if otp.code_hash == input_hash:
                otp.is_used = True
                session.commit()
                logger.info(f"OTP Verified successfully for user {user_id}")
                return True, "Verification successful."
            else:
                otp.attempts += 1
                # Lock if this was the last attempt
                if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                    otp.is_locked = True
                    session.commit()
                    logger.warning(f"OTP locked after max attempts for user {user_id}")
                    return False, "Too many failed attempts. This code is now locked. Please request a new code."
                else:
                    remaining = cls.MAX_VERIFY_ATTEMPTS - otp.attempts
                    session.commit()
                    logger.info(f"OTP verification failed: Invalid code for user {user_id} ({remaining} attempts remaining)")
                    return False, f"Invalid code. {remaining} attempt(s) remaining."
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error validating OTP: {e}")
            return False, "Verification failed due to an error."
        finally:
            if should_close:
                session.close()
