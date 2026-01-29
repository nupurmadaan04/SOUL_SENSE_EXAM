# Backup and Restore Guide

This guide explains how to create and restore backups of your SoulSense database and application data.

## Overview

SoulSense provides a comprehensive backup system that allows you to:

- Create point-in-time snapshots of your database
- Restore from any previous backup
- Manage backup files through a user-friendly interface
- Ensure data safety with automatic safety backups during restoration

## Backup Storage

### Location
Backups are stored in the `data/backups/` directory within your SoulSense installation.

### File Format
- **Filename**: `soulsense_backup_YYYYMMDD_HHMMSS_description.db`
- **Example**: `soulsense_backup_20240129_143052_weekly_backup.db`
- **Metadata**: Description stored in `.meta` file alongside backup

### Backup Contents
- Complete SQLite database containing all user data
- User profiles, journal entries, exam results, analytics data
- Configuration and preferences (stored in database)

## Creating Backups

### Method 1: Using the GUI (Recommended)

1. **Open SoulSense** and navigate to your profile or settings
2. **Click "💾 Manage Backups"** button
3. **In the backup dialog**:
   - Enter an optional description (e.g., "Before major changes")
   - Click **"📦 Create Backup"**
4. **Wait for confirmation** that the backup was created successfully

### Method 2: Programmatic Access

```python
from app.db_backup import create_backup

# Create a backup with description
backup_info = create_backup("Weekly backup")

# Create a backup without description
backup_info = create_backup()

# Access backup details
print(f"Backup created: {backup_info.filename}")
print(f"Size: {backup_info.size_display}")
print(f"Location: {backup_info.path}")
```

## Restoring from Backups

### Method 1: Using the GUI (Recommended)

1. **Open SoulSense** and navigate to your profile or settings
2. **Click "💾 Manage Backups"** button
3. **In the restore section**:
   - Select a backup from the list
   - Click **"🔄 Restore"**
4. **Confirm the restoration** when prompted
5. **Restart SoulSense** for changes to take effect

### Method 2: Programmatic Access

```python
from app.db_backup import restore_backup, list_backups

# List all available backups
backups = list_backups()
for backup in backups:
    print(f"{backup.timestamp_display} - {backup.size_display}")

# Restore from a specific backup
success = restore_backup("/path/to/soulsense_backup_20240129_143052.db")
if success:
    print("Restore completed successfully")
```

## Managing Backups

### Viewing Available Backups

```python
from app.db_backup import list_backups

backups = list_backups()
print(f"Found {len(backups)} backups:")

for backup in backups:
    print(f"- {backup.timestamp_display}: {backup.size_display}")
    if backup.description:
        print(f"  Description: {backup.description}")
```

### Deleting Old Backups

```python
from app.db_backup import delete_backup, list_backups

# List backups and delete old ones
backups = list_backups()

# Keep only the 5 most recent backups
if len(backups) > 5:
    for backup in backups[5:]:
        print(f"Deleting backup: {backup.filename}")
        delete_backup(backup.path)
```

## Safety Features

### Automatic Safety Backups

When restoring from a backup, SoulSense automatically:

1. **Creates a safety backup** of your current database
2. **Names it** `soulsense.db.safety_backup`
3. **Restores from safety backup** if the restore operation fails

### Validation

- **File validation**: Ensures backup files are valid SQLite databases
- **Permission checks**: Verifies read/write permissions on backup files
- **Directory security**: Prevents operations outside the backup directory

## Best Practices

### Backup Frequency

- **Daily**: For active users with frequent data changes
- **Weekly**: For regular users
- **Before major changes**: Updates, configuration changes, or data imports
- **Before upgrades**: Always backup before updating SoulSense

### Backup Naming

- Use descriptive names: `"Before_v2_upgrade"`, `"Monthly_backup_Jan2024"`
- Include dates in descriptions for easy identification
- Keep descriptions under 30 characters (automatically truncated)

### Storage and Retention

- **Keep multiple backups**: Maintain at least 3-5 recent backups
- **External storage**: Copy important backups to external drives or cloud storage
- **Regular cleanup**: Delete old backups to save disk space
- **Test restores**: Periodically test restoring from backups

### Security Considerations

- **Backup file permissions**: Ensure backup files have appropriate permissions
- **Encryption**: Consider encrypting backups if storing sensitive data
- **Access control**: Limit access to backup files
- **Network storage**: Use secure connections for remote backup storage

## Troubleshooting

### Common Issues

#### "Database file not found" Error

**Cause**: The main database file is missing or corrupted.

**Solutions**:
1. Check if `data/soulsense.db` exists
2. Run SoulSense to recreate the database structure
3. Restore from a working backup

#### "Invalid backup file" Error

**Cause**: The backup file is corrupted or not a valid SQLite database.

**Solutions**:
1. Verify the backup file exists and is readable
2. Check file size (should not be 0 bytes)
3. Try a different backup file
4. Contact support if all backups are invalid

#### "Permission denied" Error

**Cause**: Insufficient permissions to read/write backup files.

**Solutions**:
1. Check file permissions on the `data/backups/` directory
2. Ensure SoulSense has write access to the data directory
3. Run SoulSense as administrator (Windows) or with appropriate permissions

#### Restore Fails with "Database locked" Error

**Cause**: The database is currently in use by another process.

**Solutions**:
1. Close all instances of SoulSense
2. Wait a few minutes and try again
3. Check for any background processes using the database
4. Restart your computer if necessary

### Recovery Procedures

#### If Current Database is Corrupted

1. **Don't panic** - your data is likely safe in backups
2. **Identify a good backup** - use the backup manager to see available options
3. **Create a safety backup** of the corrupted database (if possible)
4. **Restore from backup** using the GUI or programmatic methods
5. **Verify the restore** by checking your data in SoulSense
6. **Restart SoulSense** to ensure all changes take effect

#### If All Backups are Missing

1. **Check backup directory**: `data/backups/`
2. **Search for backups** in other locations (external drives, cloud storage)
3. **Contact support** if you have cloud backups enabled
4. **Recreate data** from memory or external records if necessary

#### If Restore Partially Fails

1. **Check the safety backup**: `data/soulsense.db.safety_backup`
2. **Restore from safety backup** if the main restore failed
3. **Try a different backup** file
4. **Check application logs** for detailed error information

### Performance Considerations

- **Large databases**: Backup operations may take longer for large databases
- **Disk space**: Ensure sufficient space for backups (typically 2-3x database size)
- **Network storage**: Use fast, reliable connections for remote backups
- **Compression**: Consider compressing backups for storage efficiency

## Advanced Usage

### Automated Backups

Create a script for automated backups:

```python
#!/usr/bin/env python3
"""
Automated backup script for SoulSense
Run this daily/weekly via cron, Task Scheduler, etc.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db_backup import create_backup, list_backups, delete_backup
from datetime import datetime, timedelta

def automated_backup():
    """Create automated backup and clean up old ones."""
    try:
        # Create backup with timestamp
        description = f"Automated_{datetime.now().strftime('%Y%m%d')}"
        backup = create_backup(description)
        print(f"Backup created: {backup.filename}")

        # Clean up backups older than 30 days
        backups = list_backups()
        cutoff_date = datetime.now() - timedelta(days=30)

        deleted_count = 0
        for backup in backups:
            if backup.timestamp < cutoff_date:
                delete_backup(backup.path)
                deleted_count += 1

        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} old backups")

    except Exception as e:
        print(f"Backup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    automated_backup()
```

### Backup Verification

Verify backup integrity:

```python
from app.db_backup import list_backups, _validate_sqlite_file

def verify_backups():
    """Verify all backup files are valid."""
    backups = list_backups()
    valid_count = 0

    for backup in backups:
        if _validate_sqlite_file(backup.path):
            print(f"✓ {backup.filename}: Valid")
            valid_count += 1
        else:
            print(f"✗ {backup.filename}: Invalid")

    print(f"\nSummary: {valid_count}/{len(backups)} backups are valid")

verify_backups()
```

## API Reference

### Core Functions

#### `create_backup(description="") -> BackupInfo`
Creates a new backup of the current database.

**Parameters:**
- `description` (str): Optional description for the backup

**Returns:** `BackupInfo` object with backup details

**Raises:** `DatabaseError` if backup creation fails

#### `restore_backup(backup_path) -> bool`
Restores database from a backup file.

**Parameters:**
- `backup_path` (str): Path to the backup file

**Returns:** `True` if restoration was successful

**Raises:** `DatabaseError` if restoration fails

#### `list_backups() -> List[BackupInfo]`
Lists all available backups, sorted by date (newest first).

**Returns:** List of `BackupInfo` objects

#### `delete_backup(backup_path) -> bool`
Deletes a backup file.

**Parameters:**
- `backup_path` (str): Path to the backup file to delete

**Returns:** `True` if deletion was successful

**Raises:** `DatabaseError` if deletion fails

### Data Classes

#### `BackupInfo`
Represents information about a database backup.

**Attributes:**
- `path` (str): Full path to the backup file
- `filename` (str): Name of the backup file
- `timestamp` (datetime): When the backup was created
- `size_bytes` (int): Size of the backup file in bytes
- `description` (str): Optional description of the backup

**Properties:**
- `size_display` (str): Human-readable size string (e.g., "1.2 MB")
- `timestamp_display` (str): Formatted timestamp string

## Support

If you encounter issues with backups or restores:

1. **Check this guide** for common solutions
2. **Review application logs** for detailed error messages
3. **Verify file permissions** and disk space
4. **Test with a small backup** to isolate issues
5. **Contact support** with backup file details and error messages

Remember: **Always create a backup before attempting any restore operation!**</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\docs\guides\backup_restore.md