import logging
import json
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.db import get_session
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
    def log_event(cls, user_id: int, action: str, 
                 ip_address: Optional[str] = "SYSTEM", 
                 user_agent: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None,
                 db_session: Optional[Session] = None) -> bool:
        """
        Log a security-critical event.
        
        Args:
            user_id: ID of the user performing the action
            action: Action name (e.g., 'LOGIN', 'PASSWORD_CHANGE')
            ip_address: IP address of the requester
            user_agent: User agent string
            details: Dictionary of additional context (will be filtered)
            db_session: Optional shared session to use
            
        Returns:
            bool: True if logged successfully, False otherwise path
        """
        session = db_session if db_session else get_session()
        should_close = db_session is None
        
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
            
            session.add(log_entry)
            session.commit()
            
            logger.info(f"AUDIT LOG: User {user_id} performed {action} from {ip_address}")
            return True
            
        except Exception as e:
            # Fallback logging if DB fails
            logger.critical(f"AUDIT LOG FAILURE: User {user_id} performed {action}. Error: {e}")
            session.rollback()
            return False
        finally:
            if should_close:
                session.close()

    @staticmethod
    def get_user_logs(user_id: int, page: int = 1, per_page: int = 20, db_session: Optional[Session] = None) -> List[AuditLog]:
        """
        Retrieve audit logs for a specific user with pagination.
        """
        session = db_session if db_session else get_session()
        should_close = db_session is None
        
        try:
            offset = (page - 1) * per_page
            logs = session.query(AuditLog).filter(
                AuditLog.user_id == user_id
            ).order_by(
                AuditLog.timestamp.desc()
            ).limit(per_page).offset(offset).all()
            
            return logs
        except Exception as e:
            logger.error(f"Failed to fetch audit logs for user {user_id}: {e}")
            return []
        finally:
            if should_close:
                session.close()

    @staticmethod
    def cleanup_old_logs(days: int = 90) -> int:
        """
        Delete logs older than retention period.
        Returns: Number of records deleted.
        """
        session = get_session()
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            deleted_count = session.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).delete()
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old audit logs.")
            return deleted_count
        except Exception as e:
            session.rollback()
            logger.error(f"Audit cleanup failed: {e}")
            return 0
        finally:
            session.close()
