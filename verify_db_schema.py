from app.db import get_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_schema():
    session = get_session()
    try:
        # distinct sqlite command
        result = session.execute(text("PRAGMA table_info(users)")).fetchall()
        columns = [row[1] for row in result]
        
        if "is_2fa_enabled" in columns:
            logger.info("✅ Column 'is_2fa_enabled' EXISTS in 'users' table.")
            return True
        else:
            logger.warning("❌ Column 'is_2fa_enabled' MISSING from 'users' table.")
            return False
            
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    check_schema()
