import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..root_models import AuditLog

logger = logging.getLogger("api.audit")

class AuditService:
    """Async Audit Service for FastAPI backend."""
    
    ALLOWED_DETAIL_FIELDS = {
        "status", "reason", "method", "device", "location", "changed_field", "old_value"
    }

    @classmethod
    async def log_event(cls, user_id: int, action: str, 
                        ip_address: Optional[str] = "SYSTEM", 
                        user_agent: Optional[str] = None, 
                        details: Optional[Dict[str, Any]] = None,
                        db_session: Optional[AsyncSession] = None) -> bool:
        """
        Log a security-critical event (Async).
        """
        if not db_session:
            logger.warning(f"Audit log skipped for user {user_id} - no db_session provided")
            return False
            
        try:
            # 1. Sanitize Inputs
            safe_ua = (user_agent[:250] + "...") if user_agent and len(user_agent) > 250 else user_agent
            
            # Filter Details
            safe_details = "{}"
            if details:
                filtered = {k: v for k, v in details.items() if k in cls.ALLOWED_DETAIL_FIELDS}
                try:
                    safe_details = json.dumps(filtered)
                except Exception as e:
                    logger.warning(f"Failed to serialize audit details: {e}")
            
            # 2. Create Record
            log_entry = AuditLog(
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=safe_ua,
                details=safe_details,
                timestamp=datetime.now(timezone.utc)
            )
            
            db_session.add(log_entry)
            # We don't commit here if it's part of a larger transaction, 
            # but auth_service awaits it directly. 
            # Better to commit if we want it to be persistent.
            await db_session.commit()
            
            logger.info(f"AUDIT LOG: User {user_id} performed {action} from {ip_address}")
            return True
            
        except Exception as e:
            logger.error(f"AUDIT LOG FAILURE: User {user_id} performed {action}. Error: {e}")
            await db_session.rollback()
            return False
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from ..models import AuditLog, User
from .tamper_evident_audit_service import TamperEvidentAuditService

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for securely logging user actions and retrieving audit history (Async).

    Now integrated with tamper-evident logging (#1265) for cryptographic integrity.
    """

    # Allowed fields in details JSON to prevent PII leakage
    ALLOWED_DETAIL_FIELDS = {
        "status", "reason", "method", "device", "location", "changed_field", "old_value", "outcome",
        "session_id", "ip_address", "user_agent", "risk_score", "anomaly_type"
    }

    @classmethod
    async def log_event(cls, user_id: int, action: str,
                 ip_address: Optional[str] = "SYSTEM",
                 user_agent: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 db_session: AsyncSession = None) -> bool:
        """
        Log a security-critical event with tamper-evident hash chaining (#1265).

        Now uses TamperEvidentAuditService for cryptographic integrity.
        """
        if db_session is None:
            logger.error("Async db_session must be provided to log_event")
            return False

        # Add ip_address and user_agent to details for tamper-evident logging
        enhanced_details = details.copy() if details else {}
        if ip_address and ip_address != "SYSTEM":
            enhanced_details["ip_address"] = ip_address
        if user_agent:
            enhanced_details["user_agent"] = user_agent

        # Use tamper-evident logging service
        return await TamperEvidentAuditService.log_event_with_hash_chain(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=enhanced_details,
            db_session=db_session
        )

    @classmethod
    async def log_auth_event(cls, action: str, username: str,
                      ip_address: Optional[str] = "SYSTEM",
                      user_agent: Optional[str] = None,
                      details: Optional[Dict[str, Any]] = None,
                      db_session: Optional[AsyncSession] = None) -> bool:
        """
        Log an auth event by username (finds user_id first).
        """
        if not db_session:
             return False

        stmt = select(User.id).filter(User.username == username)
        result = await db_session.execute(stmt)
        user_id = result.scalar()

        if not user_id:
            logger.warning(f"AuditLog: Could not find user_id for username {username}")
            return False

        return await cls.log_event(
            user_id=user_id,
            action=action.upper(),
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            db_session=db_session
        )

    @staticmethod
    async def get_user_logs(user_id: int, page: int = 1, per_page: int = 20, db_session: Optional[AsyncSession] = None) -> List[AuditLog]:
        """
        Retrieve audit logs for a specific user with pagination (Async).
        """
        if not db_session:
            return []

        try:
            offset = (page - 1) * per_page
            stmt = select(AuditLog).filter(
                AuditLog.user_id == user_id
            ).order_by(
                desc(AuditLog.timestamp)
            ).limit(per_page).offset(offset)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to fetch audit logs for user {user_id}: {e}")
            return []

    @staticmethod
    async def cleanup_old_logs(db_session: AsyncSession, days: int = 90) -> int:
        """
        Delete logs older than retention period (Async).

        WARNING: This operation breaks the hash chain. Use with caution and
        consider archiving logs instead of deleting them to preserve integrity.
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            stmt = delete(AuditLog).filter(AuditLog.timestamp < cutoff_date)
            result = await db_session.execute(stmt)
            await db_session.commit()
            deleted_count = result.rowcount
            logger.warning(f"Cleaned up {deleted_count} old audit logs. HASH CHAIN BROKEN - integrity compromised!")
            return deleted_count
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Audit cleanup failed: {e}")
            return 0

    @classmethod
    async def validate_chain_integrity(cls, db_session: AsyncSession, max_entries: int = 1000) -> Tuple[bool, List[str]]:
        """
        Validate the integrity of the audit log chain (#1265).

        Returns (is_valid, error_messages) tuple.
        """
        return await TamperEvidentAuditService.validate_chain_integrity(db_session, max_entries)

    @classmethod
    async def get_chain_status(cls, db_session: AsyncSession) -> Dict[str, Any]:
        """
        Get comprehensive status of the audit log chain (#1265).
        """
        return await TamperEvidentAuditService.get_chain_status(db_session)

    @classmethod
    async def detect_tampering(cls, db_session: AsyncSession) -> List[Dict[str, Any]]:
        """
        Detect potential tampering in the audit log chain (#1265).
        """
        return await TamperEvidentAuditService.detect_tampering(db_session)
