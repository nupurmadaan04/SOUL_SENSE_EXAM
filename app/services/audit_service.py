import logging
import json
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    """
    Service for securely logging user actions and retrieving audit history.
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
                 db_session: Optional[AsyncSession] = None) -> bool:
        """
        Log a security-critical event.
        
        Args:
            user_id: ID of the user performing the action
            action: Action name (e.g., 'LOGIN', 'PASSWORD_CHANGE')
            ip_address: IP address of the requester
            user_agent: User agent string
            details: Dictionary of additional context (will be filtered)
            db_session: AsyncSession to use (REQUIRED now for async)
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        if not db_session:
            logger.error("AuditService.log_event requires a db_session")
            return False
        
        try:
            # 1. Sanitize Inputs
            # Truncate User Agent
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
            # We don't commit here if shared session, but log_event was doing it.
            # Usually audit logs should be committed immediately or along with the transaction.
            # If we want it to be separate, it needs its own session.
            # For now, let's keep it in the same transaction but caller must commit.
            # Actually, the previous implementation did session.commit().
            # await db_session.commit()
            
            logger.info(f"AUDIT LOG: User {user_id} performed {action} from {ip_address}")
            return True
            
        except Exception as e:
            # Fallback logging if DB fails
            logger.critical(f"AUDIT LOG FAILURE: User {user_id} performed {action}. Error: {e}")
            # session.rollback() # Let caller handle rollback
            return False

    @staticmethod
    async def get_user_logs(user_id: int, page: int = 1, per_page: int = 20, db_session: Optional[AsyncSession] = None) -> List[AuditLog]:
        """
        Retrieve audit logs for a specific user with pagination.
        """
        if not db_session:
            return []
        
        try:
            offset = (page - 1) * per_page
            stmt = select(AuditLog).where(
                AuditLog.user_id == user_id
            ).order_by(
                AuditLog.timestamp.desc()
            ).limit(per_page).offset(offset)
            
            result = await db_session.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to fetch audit logs for user {user_id}: {e}")
            return []

    @staticmethod
    async def cleanup_old_logs(db_session: AsyncSession, days: int = 90) -> int:
        """
        Delete logs older than retention period.
        Returns: Number of records deleted.
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            stmt = delete(AuditLog).where(
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
