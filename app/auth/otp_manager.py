import hashlib
import secrets
import logging
from datetime import datetime, timedelta, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
    async def generate_otp(cls, user_id: int, purpose: str, db_session: AsyncSession) -> tuple[Optional[str], Optional[str]]:
        """
        Generate a new OTP for a user.
        
        Args:
            user_id: The user ID
            purpose: The type of OTP (e.g., 'RESET_PASSWORD')
            db_session: Async DB session (required)
            
        Returns:
            tuple: (raw_code, error_message)
        """
        try:
            # 1. Rate Limiting Check
            stmt = select(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose
            ).order_by(OTP.created_at.desc())
            
            result = await db_session.execute(stmt)
            last_otp = result.scalars().first()
            
            if last_otp:
                # Ensure last_otp.created_at is timezone-aware for comparison
                last_created = last_otp.created_at
                if last_created.tzinfo is None:
                    last_created = last_created.replace(tzinfo=UTC)
                    
                time_since = datetime.now(UTC) - last_created
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
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(minutes=cls.OTP_EXPIRY_MINUTES),
                is_used=False,
                attempts=0,
                is_locked=False
            )
            db_session.add(new_otp)
            await db_session.commit()
            
            logger.info(f"Generated OTP for user {user_id} (Type: {purpose})")
            return code, None
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Failed to generate OTP: {e}")
            return None, "Internal error generating code."

    @classmethod
    async def is_otp_locked(cls, user_id: int, purpose: str, db_session: AsyncSession) -> tuple[bool, str]:
        """
        Check if the OTP is locked due to too many failed attempts.
        """
        try:
            stmt = select(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.now(UTC)
            ).order_by(OTP.created_at.desc())
            
            result = await db_session.execute(stmt)
            otp = result.scalars().first()
            
            if not otp:
                return False, "No active OTP found."
            
            if otp.is_locked:
                return True, "Too many failed attempts. Please request a new code."
            
            if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                otp.is_locked = True
                await db_session.commit()
                return True, "Too many failed attempts. Please request a new code."
            
            return False, f"{cls.MAX_VERIFY_ATTEMPTS - otp.attempts} attempts remaining."
            
        except Exception as e:
            logger.error(f"Error checking OTP lock status: {e}")
            return False, "Error checking OTP status."

    @classmethod
    async def get_cooldown_remaining(cls, user_id: int, purpose: str, db_session: AsyncSession) -> int:
        """
        Return remaining cooldown seconds before a new OTP can be requested.
        """
        try:
            stmt = select(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose
            ).order_by(OTP.created_at.desc())

            result = await db_session.execute(stmt)
            last_otp = result.scalars().first()

            if last_otp:
                time_since = datetime.now(UTC) - last_otp.created_at.replace(tzinfo=UTC) if last_otp.created_at.tzinfo is None else datetime.now(UTC) - last_otp.created_at
                remaining = cls.RATE_LIMIT_SECONDS - int(time_since.total_seconds())
                return max(0, remaining)
            return 0
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return 0

    @classmethod
    async def get_remaining_attempts(cls, user_id: int, purpose: str, db_session: AsyncSession) -> int:
        """
        Return remaining verification attempts for the current OTP.
        """
        try:
            stmt = select(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose,
                OTP.is_used == False,
                OTP.is_locked == False,
                OTP.expires_at > datetime.now(UTC)
            ).order_by(OTP.created_at.desc())
            
            result = await db_session.execute(stmt)
            otp = result.scalars().first()
            
            if not otp:
                return 0
            
            remaining = max(0, cls.MAX_VERIFY_ATTEMPTS - otp.attempts)
            return remaining
            
        except Exception as e:
            logger.error(f"Error getting remaining attempts: {e}")
            return 0

    @classmethod
    async def verify_otp(cls, user_id: int, code: str, purpose: str, db_session: AsyncSession) -> tuple[bool, str]:
        """
        Verify an OTP code.
        """
        try:
            input_hash = cls._hash_code(code)
            
            # Find the valid OTP
            stmt = select(OTP).filter(
                OTP.user_id == user_id,
                OTP.type == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.now(UTC)
            ).order_by(OTP.created_at.desc())
            
            result = await db_session.execute(stmt)
            otp = result.scalars().first()
            
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
                await db_session.commit()
                logger.warning(f"OTP verification blocked: Max attempts exceeded for user {user_id}")
                return False, "Too many failed attempts. Please request a new code."
                
            # Verify Hash
            if otp.code_hash == input_hash:
                otp.is_used = True
                await db_session.commit()
                logger.info(f"OTP Verified successfully for user {user_id}")
                return True, "Verification successful."
            else:
                otp.attempts += 1
                # Lock if this was the last attempt
                if otp.attempts >= cls.MAX_VERIFY_ATTEMPTS:
                    otp.is_locked = True
                    await db_session.commit()
                    logger.warning(f"OTP locked after max attempts for user {user_id}")
                    return False, "Too many failed attempts. This code is now locked. Please request a new code."
                else:
                    remaining = cls.MAX_VERIFY_ATTEMPTS - otp.attempts
                    await db_session.commit()
                    logger.info(f"OTP verification failed: Invalid code for user {user_id} ({remaining} attempts remaining)")
                    return False, f"Invalid code. {remaining} attempt(s) remaining."
                
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Error validating OTP: {e}")
            return False, "Verification failed due to an error."
