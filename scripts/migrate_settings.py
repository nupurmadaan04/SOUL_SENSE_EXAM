#!/usr/bin/env python3
"""
Migration Script: User Settings
-------------------------------
Migrates global settings from data/settings.json to the database for all users.
"""
import sys
import os
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_session, update_user_settings
from app.models import User
from app.config import DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_settings():
    settings_path = os.path.join(DATA_DIR, "settings.json")
    
    if not os.path.exists(settings_path):
        logger.info("No settings.json found. Skipping migration.")
        return

    logger.info(f"Loading settings from {settings_path}...")
    try:
        with open(settings_path, 'r') as f:
            global_settings = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read settings.json: {e}")
        return

    logger.info(f"Global Settings to Migrate: {global_settings}")

    session = get_session()
    try:
        users = session.query(User).all()
        logger.info(f"Found {len(users)} users to migrate.")
        
        migrated_count = 0
        for user in users:
            logger.info(f"Migrating settings for user: {user.username} (ID: {user.id})")
            
            # Map JSON keys to DB columns
            # JSON: { "question_count": 10, "theme": "light", "sound_effects": true }
            # DB: question_count, theme, sound_enabled
            
            update_data = {
                "question_count": global_settings.get("question_count", 10),
                "theme": global_settings.get("theme", "light"),
                "sound_enabled": global_settings.get("sound_effects", True),
                # Defaults for new fields
                "notifications_enabled": True,
                "language": "en"
            }
            
            update_user_settings(user.id, **update_data)
            migrated_count += 1
            
        logger.info(f"Successfully migrated settings for {migrated_count} users.")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate_settings()
