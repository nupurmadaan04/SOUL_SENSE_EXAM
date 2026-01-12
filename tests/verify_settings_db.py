
import sys
import os
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_session, update_user_settings, get_user_settings
from app.models import User, UserSettings
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_settings_persistence():
    session = get_session()
    try:
        # 1. Create Test User
        username = f"test_settings_{int(datetime.utcnow().timestamp())}"
        user = User(username=username, password_hash="test", created_at=datetime.utcnow().isoformat())
        session.add(user)
        session.commit()
        user_id = user.id
        logger.info(f"Created test user: {username} (ID: {user_id})")
        
        # 2. Verify Defaults
        settings = get_user_settings(user_id)
        logger.info(f"Initial Defaults: {settings}")
        assert settings["theme"] == "light"
        assert settings["question_count"] == 10
        
        # 3. Update Settings
        update_user_settings(user_id, theme="dark", question_count=20, sound_enabled=False)
        logger.info("Updated settings to: Dark, 20 questions, Sound Off")
        
        # 4. Verify Persistence
        new_settings = get_user_settings(user_id)
        logger.info(f"Retrieved Settings: {new_settings}")
        assert new_settings["theme"] == "dark"
        assert new_settings["question_count"] == 20
        assert new_settings["sound_enabled"] == False
        
        logger.info("✅ Settings Persistence Verified!")
        
    except Exception as e:
        logger.error(f"Test Failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    test_settings_persistence()
