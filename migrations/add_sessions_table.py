"""
Database Migration: Add Sessions Table
---------------------------------------
This migration adds the sessions table to track user login sessions with unique session IDs.

Run this script to upgrade an existing database with the sessions table.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.db import get_engine, get_session
from app.models import Base, Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate_add_sessions_table():
    """Add sessions table to the database"""
    engine = get_engine()
    
    try:
        # Check if sessions table already exists
        if check_table_exists(engine, 'sessions'):
            logger.info("Sessions table already exists. No migration needed.")
            return True
        
        logger.info("Creating sessions table...")
        
        # Create only the sessions table
        Session.__table__.create(engine, checkfirst=True)
        
        logger.info("✓ Sessions table created successfully")
        
        # Verify the table was created
        if check_table_exists(engine, 'sessions'):
            logger.info("✓ Migration completed successfully")
            
            # Show table structure
            inspector = inspect(engine)
            columns = inspector.get_columns('sessions')
            logger.info(f"Sessions table has {len(columns)} columns:")
            for col in columns:
                logger.info(f"  - {col['name']} ({col['type']})")
            
            return True
        else:
            logger.error("✗ Failed to create sessions table")
            return False
    
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def rollback_sessions_table():
    """Remove sessions table (rollback migration)"""
    engine = get_engine()
    
    try:
        if not check_table_exists(engine, 'sessions'):
            logger.info("Sessions table doesn't exist. Nothing to rollback.")
            return True
        
        logger.info("Rolling back: Dropping sessions table...")
        
        with engine.connect() as conn:
            conn.execute(text('DROP TABLE IF EXISTS sessions'))
            conn.commit()
        
        logger.info("✓ Sessions table removed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        return False


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate database to add sessions table')
    parser.add_argument(
        '--rollback', 
        action='store_true', 
        help='Rollback the migration (remove sessions table)'
    )
    
    args = parser.parse_args()
    
    if args.rollback:
        logger.info("Starting rollback...")
        success = rollback_sessions_table()
    else:
        logger.info("Starting migration...")
        success = migrate_add_sessions_table()
    
    if success:
        logger.info("Operation completed successfully!")
        return 0
    else:
        logger.error("Operation failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
