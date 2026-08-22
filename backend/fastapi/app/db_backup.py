"""
Database Backup & Restore Module (Issue #345)
Provides functionality to create and restore local backups of the SQLite database.
"""

import os
import shutil
import sqlite3
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from contextlib import contextmanager

from app.config import DATABASE_URL, DB_PATH, DATA_DIR
from app.exceptions import DatabaseError
from app.db import get_engine, safe_db_context
from sqlalchemy import text
logger = logging.getLogger(__name__)

def is_sqlite() -> bool:
    """Check if the current unified database is SQLite."""
    return DATABASE_URL.startswith("sqlite")

# Backup directory location
BACKUP_DIR: str = os.path.join(DATA_DIR, "backups")

# Ensure backup directory exists
if not os.path.exists(BACKUP_DIR):
    try:
        os.makedirs(BACKUP_DIR)
    except OSError as e:
        logger.warning(f"Could not create backup directory: {e}")


@dataclass
class BackupInfo:
    """Information about a database backup."""
    path: str
    filename: str
    timestamp: datetime
    size_bytes: int
    description: str = ""
    
    @property
    def size_display(self) -> str:
        """Return human-readable size string."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        else:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
    
    @property
    def timestamp_display(self) -> str:
        """Return formatted timestamp string."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")


def _validate_sqlite_file(filepath: str) -> bool:
    """
    Validate that a file is a valid SQLite database.
    
    Args:
        filepath: Path to the file to validate
        
    Returns:
        True if valid SQLite database, False otherwise
    """
    try:
        # Check file exists
        if not os.path.exists(filepath):
            return False
        
        # Try to open as SQLite database
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        # Execute a simple query to verify it's a valid database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        conn.close()
        return True
    except sqlite3.Error:
        return False
    except Exception:
        return False


def create_backup(description: str = "") -> BackupInfo:
    """
    Create a backup of the current database.
    
    Args:
        description: Optional description for the backup
        
    Returns:
        BackupInfo object with details about the created backup
        
    Raises:
        DatabaseError: If backup creation fails
    """
    if not is_sqlite():
        raise DatabaseError("Local database backup is only supported for SQLite databases. Please use external tools for PostgreSQL backups.")
    
    if not os.path.exists(DB_PATH):
        raise DatabaseError("Database file not found. Cannot create backup.")
    
    # Ensure backup directory exists
    if not os.path.exists(BACKUP_DIR):
        try:
            os.makedirs(BACKUP_DIR)
        except OSError as e:
            raise DatabaseError(f"Failed to create backup directory: {e}", original_exception=e)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    # Sanitize description for filename (remove special chars)
    safe_desc = ""
    if description:
        safe_desc = "_" + "".join(c for c in description[:30] if c.isalnum() or c in "- _").strip().replace(" ", "_")
    
    backup_filename = f"soulsense_backup_{timestamp_str}{safe_desc}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        # Use SQLite's backup API for safe copy
        engine = get_engine()
        source_conn = engine.raw_connection()
        
        # We need to handle potential wrappers in some versions of SQLAlchemy
        raw_source = getattr(source_conn, "connection", source_conn)
        
        # Open destination connection
        dest_conn = sqlite3.connect(backup_path)
        
        try:
            with dest_conn:
                raw_source.backup(dest_conn)
            
            # Get file size
            size_bytes = os.path.getsize(backup_path)
            
            # Create metadata file for description
            if description:
                meta_path = backup_path + ".meta"
                try:
                    with open(meta_path, "w", encoding="utf-8") as f:
                        f.write(description)
                except Exception as e:
                    logger.warning(f"Failed to write backup metadata: {e}")
            
            logger.info(f"Created backup: {backup_path} ({size_bytes} bytes)")
            
            return BackupInfo(
                path=backup_path,
                filename=backup_filename,
                timestamp=timestamp,
                size_bytes=size_bytes,
                description=description
            )
        finally:
            dest_conn.close()
            # Return source connection to pool
            source_conn.close()
        
    except sqlite3.Error as e:
        # Clean up partial backup if it exists
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass
        raise DatabaseError(f"Failed to create backup: {e}", original_exception=e)
    except Exception as e:
        raise DatabaseError(f"Unexpected error creating backup: {e}", original_exception=e)


def restore_backup(backup_path: str) -> bool:
    """
    Restore database from a backup file.
    
    Creates a safety backup before restoration in case the restore fails.
    
    Args:
        backup_path: Path to the backup file to restore
        
    Returns:
        True if restoration was successful
        
    Raises:
        DatabaseError: If restoration fails
    """
    if not os.path.exists(backup_path):
        raise DatabaseError(f"Backup file not found: {backup_path}")
    
    # Validate backup is a valid SQLite database
    if not _validate_sqlite_file(backup_path):
        raise DatabaseError("Invalid backup file. The file is not a valid SQLite database.")
    
    # Create safety backup of current database
    safety_path = DB_PATH + ".safety_backup"
    try:
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, safety_path)
            logger.info(f"Created safety backup: {safety_path}")
    except Exception as e:
        logger.warning(f"Could not create safety backup: {e}")
        # Continue anyway - user explicitly requested restore
    
    try:
        # Use SQLite's backup API for safe restoration
        source_conn = sqlite3.connect(backup_path)
        
        engine = get_engine()
        dest_conn_wrapper = engine.raw_connection()
        raw_dest = getattr(dest_conn_wrapper, "connection", dest_conn_wrapper)
        
        try:
            # Note: During restoration, we backup FROM the file TO the current DB
            source_conn.backup(raw_dest)
            logger.info(f"Successfully restored database from: {backup_path}")
        finally:
            source_conn.close()
            dest_conn_wrapper.close()
        
        # Remove safety backup after successful restore
        if os.path.exists(safety_path):
            try:
                os.remove(safety_path)
            except Exception:
                pass
        
        return True
        
    except sqlite3.Error as e:
        # Try to restore from safety backup
        if os.path.exists(safety_path):
            try:
                shutil.copy2(safety_path, DB_PATH)
                logger.info("Restored from safety backup after failed restore")
            except Exception:
                pass
        raise DatabaseError(f"Failed to restore backup: {e}", original_exception=e)
    except Exception as e:
        raise DatabaseError(f"Unexpected error restoring backup: {e}", original_exception=e)


def list_backups() -> List[BackupInfo]:
    """
    Get a list of all available backups, sorted by date (newest first).
    
    Returns:
        List of BackupInfo objects
    """
    backups: List[BackupInfo] = []
    
    if not os.path.exists(BACKUP_DIR):
        return backups
    
    try:
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith("soulsense_backup_") and filename.endswith(".db"):
                filepath = os.path.join(BACKUP_DIR, filename)
                
                try:
                    # Parse timestamp from filename
                    # Format: soulsense_backup_YYYYMMDD_HHMMSS_description.db
                    parts = filename.replace("soulsense_backup_", "").replace(".db", "")
                    timestamp_str = parts[:15]  # YYYYMMDD_HHMMSS
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    # Get file size
                    size_bytes = os.path.getsize(filepath)
                    
                    # Read description from metadata file if exists
                    description = ""
                    meta_path = filepath + ".meta"
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                description = f.read().strip()
                        except Exception:
                            pass
                    
                    backups.append(BackupInfo(
                        path=filepath,
                        filename=filename,
                        timestamp=timestamp,
                        size_bytes=size_bytes,
                        description=description
                    ))
                    
                except (ValueError, OSError) as e:
                    logger.warning(f"Skipping invalid backup file {filename}: {e}")
                    continue
                    
    except OSError as e:
        logger.error(f"Error listing backups: {e}")
    
    # Sort by timestamp, newest first
    backups.sort(key=lambda b: b.timestamp, reverse=True)
    
    return backups


def delete_backup(backup_path: str) -> bool:
    """
    Delete a backup file.
    
    Args:
        backup_path: Path to the backup file to delete
        
    Returns:
        True if deletion was successful
        
    Raises:
        DatabaseError: If deletion fails
    """
    if not os.path.exists(backup_path):
        raise DatabaseError(f"Backup file not found: {backup_path}")
    
    # Verify this is actually in the backup directory (security check)
    if not os.path.dirname(os.path.abspath(backup_path)) == os.path.abspath(BACKUP_DIR):
        raise DatabaseError("Cannot delete files outside backup directory")
    
    try:
        os.remove(backup_path)
        
        # Also remove metadata file if exists
        meta_path = backup_path + ".meta"
        if os.path.exists(meta_path):
            try:
                os.remove(meta_path)
            except Exception:
                pass
        
        logger.info(f"Deleted backup: {backup_path}")
        return True
        
    except OSError as e:
        raise DatabaseError(f"Failed to delete backup: {e}", original_exception=e)


def get_backup_dir() -> str:
    """Return the backup directory path."""
    return BACKUP_DIR
