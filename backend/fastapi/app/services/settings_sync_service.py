"""
Settings Synchronization Service

Provides key-value based settings storage with conflict-safe updates using optimistic locking.
Implements Issue #396: Create Settings Synchronization API
"""

from typing import List, Optional, Tuple, Any, Dict
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models import UserSyncSetting


class SettingsSyncService:
    """Service for managing user sync settings with conflict detection."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value to JSON string for storage."""
        return json.dumps(value)
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize JSON string to Python object."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def get_setting(self, user_id: int, key: str) -> Optional[UserSyncSetting]:
        """
        Get a single setting by key for a user.
        
        Args:
            user_id: User ID
            key: Setting key
            
        Returns:
            UserSyncSetting or None if not found
        """
        return self.db.query(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id,
            UserSyncSetting.key == key
        ).first()
    
    def get_all_settings(self, user_id: int) -> List[UserSyncSetting]:
        """
        Get all settings for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of UserSyncSetting objects
        """
        return self.db.query(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id
        ).order_by(UserSyncSetting.key).all()
    
    def upsert_setting(
        self, 
        user_id: int, 
        key: str, 
        value: Any,
        expected_version: Optional[int] = None
    ) -> Tuple[UserSyncSetting, bool, Optional[str]]:
        """
        Create or update a setting with optimistic locking.
        
        Args:
            user_id: User ID
            key: Setting key
            value: Setting value (will be JSON serialized)
            expected_version: If provided, update only if current version matches
            
        Returns:
            Tuple of (setting, success, error_message)
            - success is False if there's a version conflict
        """
        existing = self.get_setting(user_id, key)
        serialized_value = self._serialize_value(value)
        
        if existing:
            # Check for version conflict
            if expected_version is not None and existing.version != expected_version:
                return existing, False, f"Version conflict: expected {expected_version}, found {existing.version}"
            
            # Update existing setting
            existing.value = serialized_value
            existing.version += 1
            existing.updated_at = datetime.utcnow().isoformat()
            self.db.commit()
            self.db.refresh(existing)
            return existing, True, None
        else:
            # Create new setting
            new_setting = UserSyncSetting(
                user_id=user_id,
                key=key,
                value=serialized_value,
                version=1,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            self.db.add(new_setting)
            self.db.commit()
            self.db.refresh(new_setting)
            return new_setting, True, None
    
    def delete_setting(self, user_id: int, key: str) -> bool:
        """
        Delete a setting by key.
        
        Args:
            user_id: User ID
            key: Setting key
            
        Returns:
            True if deleted, False if not found
        """
        existing = self.get_setting(user_id, key)
        if existing:
            self.db.delete(existing)
            self.db.commit()
            return True
        return False
    
    def batch_get_settings(self, user_id: int, keys: List[str]) -> List[UserSyncSetting]:
        """
        Get multiple settings by keys.
        
        Args:
            user_id: User ID
            keys: List of setting keys
            
        Returns:
            List of UserSyncSetting objects (may be fewer than keys if some don't exist)
        """
        return self.db.query(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id,
            UserSyncSetting.key.in_(keys)
        ).all()
    
    def batch_upsert_settings(
        self, 
        user_id: int, 
        settings: List[Dict[str, Any]]
    ) -> Tuple[List[UserSyncSetting], List[str]]:
        """
        Batch upsert settings. Continues on conflict, recording conflicting keys.
        
        Args:
            user_id: User ID
            settings: List of dicts with 'key' and 'value' fields
            
        Returns:
            Tuple of (successful settings, list of conflicting keys)
        """
        successful = []
        conflicts = []
        
        for setting_data in settings:
            key = setting_data.get('key')
            value = setting_data.get('value')
            expected_version = setting_data.get('expected_version')
            
            if not key:
                continue
            
            setting, success, error = self.upsert_setting(
                user_id=user_id,
                key=key,
                value=value,
                expected_version=expected_version
            )
            
            if success:
                successful.append(setting)
            else:
                conflicts.append(key)
        
        return successful, conflicts
    
    def delete_all_settings(self, user_id: int) -> int:
        """
        Delete all settings for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of settings deleted
        """
        count = self.db.query(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id
        ).delete()
        self.db.commit()
        return count
