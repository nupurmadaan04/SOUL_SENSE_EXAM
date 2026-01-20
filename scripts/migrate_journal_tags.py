#!/usr/bin/env python3
"""
Migration script to add tags column to journal_entries table.
Run this script to update the database schema for enhanced journal features.
"""

import sqlite3
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path("soulsense.db")

def migrate_journal_tags():
    """Add tags column to journal_entries table"""
    if not DB_PATH.exists():
        logger.error(f"Database file not found at {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if tags column already exists
        cursor.execute("PRAGMA table_info(journal_entries)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'tags' in columns:
            logger.info("✅ Tags column already exists in journal_entries table")
            return True

        # Add tags column
        logger.info("Adding tags column to journal_entries table...")
        cursor.execute("ALTER TABLE journal_entries ADD COLUMN tags TEXT")

        conn.commit()
        logger.info("✅ Successfully added tags column to journal_entries table")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(journal_entries)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'tags' in columns:
            logger.info("✅ Migration completed successfully")
            return True
        else:
            logger.error("❌ Failed to add tags column")
            return False

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("Starting journal tags migration...")
    success = migrate_journal_tags()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        exit(1)
