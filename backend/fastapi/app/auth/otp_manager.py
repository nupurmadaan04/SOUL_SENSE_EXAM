import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone

# Python 3.10 compatibility
UTC = timezone.utc
from app.utils.clock_aware_time import ClockAwareTime, is_expired as check_expiry
from app.db import safe_db_context
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
        """Generate a new OTP for a user."""
        if db_session:
            return cls._generate_otp_impl(db_session, user_id, purpose)
        
        try:
            with safe_db_context() as session:
                return cls._generate_otp_impl(session, user_id, purpose)
        except Exception as e:
            logger.error(f"Failed to generate OTP: {e}")
            return None, "Internal error generating code."

    @classmethod
    def _generate_otp_impl(cls, session, user_id: int, purpose: str) -> tuple[Optional[str], Optional[str]]:
        """Internal implementation for generate_otp."""
        # 1. Rate Limiting Check
        last_otp = session.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.purpose == purpose
        ).order_by(OTP.created_at.desc()).first()
        
        if last_otp:
            time_since = ClockAwareTime.get_current_time() - (last_otp.created_at.replace(tzinfo=UTC) if last_otp.created_at.tzinfo is None else last_otp.created_at)
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
            purpose=purpose,
            created_at=ClockAwareTime.get_current_time(),
            expires_at=ClockAwareTime.get_expiry_with_drift_tolerance(cls.OTP_EXPIRY_MINUTES * 60),
            is_used=False,
            attempts=0,
            is_locked=False
        )
        session.add(new_otp)
        
        logger.info(f"Generated OTP for user {user_id} (Type: {purpose})")
        return code, None

    @classmethod
    def is_otp_locked(cls, user_id: int, purpose: str, db_session=None) -> tuple[bool, str]:
        """Check if the OTP is locked due to too many failed attempts."""
        if db_session:
            return cls._is_otp_locked_impl(db_session, user_id, purpose)
        
        try:
            with safe_db_context() as session:
                return cls._is_otp_locked_impl(session, user_id, purpose)
        except Exception as e:
            logger.error(f"Error checking OTP lock status: {e}")
            return False, "Error checking OTP status."

    @classmethod
    def _is_otp_locked_impl(cls, session, user_id: int, purpose: str) -> tuple[bool, str]:
        """Internal implementation for is_otp_locked."""
        otp = session.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.purpose == purpose,
            OTP.is_used == False,
            OTP.expires_at > ClockAwareTime.get_current_time()
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            return False, "No active OTP found."
        
        if otp.is_locked:
            return True, "Too many failed attempts. Please request a new code."
        
        if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
            otp.is_locked = True
            return True, "Too many failed attempts. Please request a new code."
        
        return False, f"{cls.MAX_VERIFY_ATTEMPTS - otp.attempts} attempts remaining."

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
                OTP.purpose == purpose
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
        """Return remaining verification attempts for the current OTP."""
        if db_session:
            return cls._get_remaining_attempts_impl(db_session, user_id, purpose)
        
        try:
            with safe_db_context() as session:
                return cls._get_remaining_attempts_impl(session, user_id, purpose)
        except Exception as e:
            logger.error(f"Error getting remaining attempts: {e}")
            return 0

    @classmethod
    def _get_remaining_attempts_impl(cls, session, user_id: int, purpose: str) -> int:
        """Internal implementation for get_remaining_attempts."""
        otp = session.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.purpose == purpose,
            OTP.is_used == False,
            OTP.is_locked == False,
            OTP.expires_at > ClockAwareTime.get_current_time()
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            return 0
        
        return max(0, cls.MAX_VERIFY_ATTEMPTS - otp.attempts)

    @classmethod
    def verify_otp(cls, user_id: int, code: str, purpose: str, db_session=None) -> tuple[bool, str]:
        """Verify an OTP code."""
        if db_session:
            return cls._verify_otp_impl(db_session, user_id, code, purpose)
        
        try:
            with safe_db_context() as session:
                return cls._verify_otp_impl(session, user_id, code, purpose)
        except Exception as e:
            logger.error(f"Error validating OTP: {e}")
            return False, "Verification failed due to an error."

    @classmethod
    def _verify_otp_impl(cls, session, user_id: int, code: str, purpose: str) -> tuple[bool, str]:
        """Internal implementation for verify_otp."""
        input_hash = cls._hash_code(code)
        
        # Find the valid OTP
        otp = session.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.purpose == purpose,
            OTP.is_used == False,
            OTP.expires_at > ClockAwareTime.get_current_time()
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
            logger.warning(f"OTP verification blocked: Max attempts exceeded for user {user_id}")
            return False, "Too many failed attempts. Please request a new code."
            
        # Verify Hash
        if otp.code_hash == input_hash:
            otp.is_used = True
            logger.info(f"OTP Verified successfully for user {user_id}")
            return True, "Verification successful."
        else:
            otp.attempts += 1
            # Lock if this was the last attempt
            if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                otp.is_locked = True
                logger.warning(f"OTP locked after max attempts for user {user_id}")
                return False, "Too many failed attempts. This code is now locked. Please request a new code."
            else:
                remaining = cls.MAX_VERIFY_ATTEMPTS - otp.attempts
                logger.info(f"OTP verification failed: Invalid code for user {user_id} ({remaining} attempt(s) remaining)")
                return False, f"Invalid code. {remaining} attempt(s) remaining."
