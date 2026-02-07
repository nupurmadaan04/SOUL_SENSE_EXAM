import logging
from datetime import datetime, timedelta, UTC
from app.db import get_session
from app.models import User

logger = logging.getLogger(__name__)

def deactivate_dormant_accounts(days: int = 90) -> int:
    """
    Deactivate accounts that have been inactive for a specified number of days.
    
    Logic:
        1. Checks last_activity, then last_login, then created_at.
        2. If all are older than threshold, marks as inactive.
        3. EXEMPTS User ID 1 (Admin/Superuser).
    
    Args:
        days: Threshold in days for dormancy (default 90)
        
    Returns:
        int: Number of accounts deactivated
    """
    session = get_session()
    deactivated_count = 0
    
    try:
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        
        # Fetch active users only
        # Note: We fetch all and filter in python to handle complex 'OR' logic 
        # with nullable fields properly across different DB backends (SQLite/Postgres) 
        # without complex Coalesce queries, though Coalesce is standard, explicit logic is safer for this critical task.
        active_users = session.query(User).filter(User.is_active == True).all()
        
        for user in active_users:
            # 1. Protection: Skip Admin (ID 1 OR username 'admin' for robustness)
            if user.id == 1 or user.username.lower() == "admin":
                continue
                
            # 2. Determine Last Seen
            last_seen_str = user.last_activity or user.last_login or user.created_at
            
            if not last_seen_str:
                # Should not happen given created_at default, but safegaurd
                logger.warning(f"User {user.username} has no timestamps. Skipping deactivation.")
                continue
                
            try:
                # Handle potential format differences if any legacy data exists
                last_seen = datetime.fromisoformat(last_seen_str)
            except ValueError:
                # Fallback purely for safety if ISO format is broken (unlikely)
                continue
                
            # 3. Check Dormancy
            if last_seen < cutoff_date:
                logger.info(f"Deactivating dormant user: {user.username} (Last active: {last_seen_str})")
                user.is_active = False
                deactivated_count += 1
                
        if deactivated_count > 0:
            session.commit()
            logger.info(f"Maintenance: Deactivated {deactivated_count} dormant accounts.")
        else:
            logger.info("Maintenance: No dormant accounts found.")
            
    except Exception as e:
        logger.error(f"Error during account deactivation task: {e}")
        session.rollback()
    finally:
        session.close()
        
    return deactivated_count
