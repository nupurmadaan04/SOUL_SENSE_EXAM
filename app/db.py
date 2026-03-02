# app/db.py - SIMPLIFIED VERSION
import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Iterator, Dict, Any, Optional, Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from app.config import (
    DATABASE_URL, DB_PATH, BASE_DIR, 
    DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_TIMEOUT, 
    DB_POOL_RECYCLE, DB_POOL_PRE_PING, DB_STATEMENT_TIMEOUT
)
from app.exceptions import DatabaseError

# Configure logger
logger = logging.getLogger(__name__)

# Secure database connection with connection pooling
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = DB_POOL_TIMEOUT
elif "postgresql" in DATABASE_URL:
    connect_args["options"] = f"-c statement_timeout={DB_STATEMENT_TIMEOUT}"

engine_args = {
    "connect_args": connect_args,
    "pool_pre_ping": DB_POOL_PRE_PING,
    "echo": False
}

if DATABASE_URL.startswith("sqlite"):
    # For SQLite, use StaticPool for consistency and thread-safety
    engine_args["poolclass"] = StaticPool
else:
    # Production pooling for other DB types
    engine_args.update({
        "pool_size": DB_POOL_SIZE,
        "max_overflow": DB_MAX_OVERFLOW,
        "pool_timeout": DB_POOL_TIMEOUT,
        "pool_recycle": DB_POOL_RECYCLE,
    })

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_engine() -> Engine:
    return engine

def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()

@contextmanager
def safe_db_context() -> Generator[Session, None, None]:
    """Context manager for safe database operations"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise DatabaseError("A database error occurred.", original_exception=e)
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error in DB context: {str(e)}", exc_info=True)
        raise DatabaseError("An unexpected database error occurred.", original_exception=e)
    finally:
        session.close()

def check_db_state() -> bool:
    """Check database connectivity and verify schema via inspector"""
    logger.info("Checking unified database connectivity...")
    
    try:
        # Check connectivity
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection established.")
        
        # Check for existing table (e.g., scores) as a health check
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "scores" in tables:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM scores"))
                count = result.scalar()
                logger.debug(f"Connectivity check passed: Found {count} scores")
        else:
            logger.warning("Database connected but expected tables (like 'scores') not found. Migration may be required.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking database state: {e}")
        return False

# Removed create_tables_directly to prevent shadow schema drift

# Initialize database
# check_db_state()  # DISABLED to prevent side-effects on import

# Backward compatibility - Only works if using SQLite
def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if not DATABASE_URL.startswith("sqlite"):
        logger.error(f"Raw sqlite3 connection requested but unified DATABASE_URL is {DATABASE_URL}")
        raise DatabaseError("Raw sqlite3 connection not supported for current non-SQLite database type.")
    try:
        # Extract path from DATABASE_URL if db_path not provided
        target_path = db_path
        if not target_path and DATABASE_URL.startswith("sqlite:///"):
            target_path = DATABASE_URL.replace("sqlite:///", "")
            
        return sqlite3.connect(target_path or DB_PATH)
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to raw database: {e}", exc_info=True)
        raise DatabaseError("Failed to connect to raw database.", original_exception=e)

def get_user_settings(user_id: int) -> Dict[str, Any]:
    """
    Fetch settings for a user.
    Returns a dictionary of settings. Creates defaults if not found.
    """
    from app.models import UserSettings
    from datetime import datetime
    
    with safe_db_context() as session:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()
        
        if not settings:
            # Create default settings for this user
            try:
                settings = UserSettings(user_id=user_id)
                session.add(settings)
                session.commit()
                # Refresh to get defaults
                session.refresh(settings)
            except Exception as e:
                logger.error(f"Failed to create default settings for user {user_id}: {e}")
                # Return generic defaults on failure (fallback)
                return {
                    "theme": "light", 
                    "question_count": 10, 
                    "sound_enabled": True,
                    "notifications_enabled": True,
                    "language": "en"
                }

        return {
            "theme": settings.theme,
            "question_count": settings.question_count,
            "sound_enabled": settings.sound_enabled,
            "notifications_enabled": settings.notifications_enabled,
            "language": settings.language
        }

def update_user_settings(user_id: int, **kwargs: Any) -> bool:
    """
    Update settings for a user.
    Args:
        user_id: ID of the user
        **kwargs: Key-value pairs of settings to update
    """
    from app.models import UserSettings
    from datetime import datetime, UTC

    with safe_db_context() as session:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()

        if not settings:
            settings = UserSettings(user_id=user_id)
            session.add(settings)

        # dynamic update
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value) # type: ignore

        settings.updated_at = datetime.now(UTC).isoformat() # type: ignore
        session.commit()
        return True

def delete_user_data(user_id: int) -> bool:
    """
    Permanently delete all user data from the database and local storage.
    This includes the user record and all related data due to cascade delete relationships,
    as well as local files like avatar images and exported data.

    Args:
        user_id: ID of the user to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    import os
    import shutil
    from app.models import User

    try:
        with safe_db_context() as session:
            user = session.query(User).filter_by(id=user_id).first()

            if not user:
                logger.warning(f"User with ID {user_id} not found for deletion")
                return False

            username = user.username

            # Delete local files before DB deletion
            # 1. Delete avatar file
            avatar_path = None
            if user.personal_profile and user.personal_profile.avatar_path:
                avatar_path = user.personal_profile.avatar_path
                if os.path.exists(avatar_path):
                    try:
                        os.remove(avatar_path)
                        logger.info(f"Deleted avatar file: {avatar_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete avatar file {avatar_path}: {e}")

            # 2. Delete exported files
            exports_dir = os.path.join(BASE_DIR, "exports")
            if os.path.exists(exports_dir):
                for filename in os.listdir(exports_dir):
                    if filename.startswith(f"{username}_"):
                        file_path = os.path.join(exports_dir, filename)
                        try:
                            os.remove(file_path)
                            logger.info(f"Deleted exported file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete exported file {file_path}: {e}")

            # Delete the user - cascade delete will handle all related records
            session.delete(user)
            session.commit()

            logger.info(f"Successfully deleted all data for user ID {user_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to delete user data for user ID {user_id}: {e}")
        return False

