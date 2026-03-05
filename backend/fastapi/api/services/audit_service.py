import logging
import json
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from ..models import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for securely logging user actions and retrieving audit history (Async).
    """

    # Allowed fields in details JSON to prevent PII leakage
    ALLOWED_DETAIL_FIELDS = {
        "status", "reason", "method", "device", "location", "changed_field", "old_value"
    }

    @classmethod
    async def log_event(cls, user_id: int, action: str,
                 ip_address: Optional[str] = "SYSTEM",
                 user_agent: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 db_session: AsyncSession = None) -> bool:
        """
        Log a security-critical event (Async).
        """
        if db_session is None:
            logger.error("Async db_session must be provided to log_event")
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
                timestamp=datetime.now(UTC)
            )

            db_session.add(log_entry)
            await db_session.commit()

            logger.info(f"AUDIT LOG: User {user_id} performed {action} from {ip_address}")
            return True

        except Exception as e:
            await db_session.rollback()
            logger.critical(f"AUDIT LOG FAILURE: User {user_id} performed {action}. Error: {e}")
            return False

    @staticmethod
    async def get_user_logs(user_id: int, page: int = 1, per_page: int = 20, db_session: AsyncSession = None) -> List[AuditLog]:
        """
        Retrieve audit logs for a specific user with pagination (Async).
        """
        if db_session is None:
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
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            stmt = delete(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            )
            result = await db_session.execute(stmt)
            await db_session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Cleaned up {deleted_count} old audit logs.")
            return deleted_count
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Audit cleanup failed: {e}")
            return 0
