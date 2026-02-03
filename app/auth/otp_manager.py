import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from app.db import get_session
from app.models import OTP, User

logger = logging.getLogger(__name__)

from typing import Optional

class OTPManager:
    """
    Manages generation, storage, and verification of One-Time Passwords.
    Implements rate limiting, secure hashing, and expiry.
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
                attempts=0
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
    def verify_otp(cls, user_id: int, code: str, purpose: str, db_session=None) -> bool:
        """
        Verify an OTP code.
        INVALIDATES the OTP if successful (is_used=True).
        Increments attempt count on failure.
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
                return False
                
            # Check attempts
            if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                logger.warning(f"OTP verification blocked: Max attempts exceeded for user {user_id}")
                return False
                
            # Verify Hash
            if otp.code_hash == input_hash:
                otp.is_used = True
                session.commit()
                logger.info(f"OTP Verified successfully for user {user_id}")
                return True
            else:
                otp.attempts += 1
                session.commit()
                logger.info(f"OTP verification failed: Invalid code for user {user_id}")
                return False
                
        except Exception as e:
            # Only roll back our transaction part? 
            # If we share session, rollback rolls back everything.
            session.rollback()
            logger.error(f"Error validating OTP: {e}")
            return False
        finally:
            if should_close:
                session.close()
