
import os
import sqlite3
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///app.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_engine():
    return engine


def get_session() -> Session:
    """Get a new database session"""
    return SessionLocal()


@contextmanager
def safe_db_context():
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


def check_db_state():
    """
    Check and create database tables if needed.
    IMPORTANT:
    - Import Base ONLY inside the function
    - NEVER call this automatically at import time
    """
    logger.info("Checking database state...")

    try:
        from app.models import Base  # SAFE: runtime import only

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully.")

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "scores" in tables:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM scores"))
                count = result.scalar()
                logger.info(f"Found {count} scores in database")

        return True

    except Exception as e:
        logger.error(f"Error checking database state: {e}", exc_info=True)
        logger.warning("Falling back to direct SQLite table creation")
        create_tables_directly()
        return True


# -------------------------
# SQLite fallback (legacy)
# -------------------------

def create_tables_directly():
    """Create tables using direct SQLite (fallback only)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                age INTEGER,
                total_score INTEGER,
                sentiment_score REAL DEFAULT 0.0,
                reflection_text TEXT,
                is_rushed BOOLEAN DEFAULT 0,
                is_inconsistent BOOLEAN DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                detailed_age_group TEXT,
                user_id INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                entry_date TEXT DEFAULT CURRENT_TIMESTAMP,
                content TEXT,
                sentiment_score REAL,
                emotional_patterns TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT,
                last_login TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Tables created using direct SQLite")

    except sqlite3.Error as e:
        logger.error(f"Failed to create tables: {e}", exc_info=True)
        raise DatabaseError("Failed to initialize database", original_exception=e)


# -------------------------
# Raw SQLite compatibility
# -------------------------

def get_connection(db_path=None):
    try:
        return sqlite3.connect(db_path or DB_PATH)
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to raw database: {e}", exc_info=True)
        raise DatabaseError("Failed to connect to raw database.", original_exception=e)


# -------------------------
# User settings helpers
# -------------------------

def get_user_settings(user_id):
    """
    Fetch settings for a user.
    Returns a dictionary of settings. Creates defaults if not found.
    """
    from app.models import UserSettings

    with safe_db_context() as session:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()

        if not settings:
            try:
                settings = UserSettings(user_id=user_id)
                session.add(settings)
                session.commit()
                session.refresh(settings)
            except Exception as e:
                logger.error(f"Failed to create default settings: {e}", exc_info=True)
                return {
                    "theme": "light",
                    "question_count": 10,
                    "sound_enabled": True,
                    "notifications_enabled": True,
                    "language": "en",
                }

        return {
            "theme": settings.theme,
            "question_count": settings.question_count,
            "sound_enabled": settings.sound_enabled,
            "notifications_enabled": settings.notifications_enabled,
            "language": settings.language,
        }


def update_user_settings(user_id, **kwargs):
    """
    Update settings for a user.
    """
    from app.models import UserSettings
    from datetime import datetime

    with safe_db_context() as session:
        settings = session.query(UserSettings).filter_by(user_id=user_id).first()

        if not settings:
            settings = UserSettings(user_id=user_id)
            session.add(settings)

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow().isoformat()
        session.commit()
        return True
