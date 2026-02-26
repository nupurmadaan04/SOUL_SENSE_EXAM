from typing import List, Optional, Tuple, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, UTC
import json

# Import models from root_models module (handles namespace collision)
from ..root_models import UserSyncSetting


class SettingsSyncService:
    """Service for managing user sync settings with conflict detection (Async)."""
    
    def __init__(self, db: AsyncSession):
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
    
    async def get_setting(self, user_id: int, key: str) -> Optional[UserSyncSetting]:
        """
        Get a single setting by key for a user.
        """
        stmt = select(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id,
            UserSyncSetting.key == key
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_settings(self, user_id: int) -> List[UserSyncSetting]:
        """
        Get all settings for a user.
        """
        stmt = select(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id
        ).order_by(UserSyncSetting.key)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def upsert_setting(
        self, 
        user_id: int, 
        key: str, 
        value: Any,
        expected_version: Optional[int] = None
    ) -> Tuple[UserSyncSetting, bool, Optional[str]]:
        """
        Create or update a setting with optimistic locking.
        """
        existing = await self.get_setting(user_id, key)
        serialized_value = self._serialize_value(value)
        
        now_iso = datetime.now(UTC).isoformat()
        
        if existing:
            # Check for version conflict
            if expected_version is not None and existing.version != expected_version:
                return existing, False, f"Version conflict: expected {expected_version}, found {existing.version}"
            
            # Update existing setting
            existing.value = serialized_value
            existing.version += 1
            existing.updated_at = now_iso
            await self.db.commit()
            await self.db.refresh(existing)
            return existing, True, None
        else:
            # Create new setting
            new_setting = UserSyncSetting(
                user_id=user_id,
                key=key,
                value=serialized_value,
                version=1,
                created_at=now_iso,
                updated_at=now_iso
            )
            self.db.add(new_setting)
            await self.db.commit()
            await self.db.refresh(new_setting)
            return new_setting, True, None
    
    async def delete_setting(self, user_id: int, key: str) -> bool:
        """
        Delete a setting by key.
        """
        existing = await self.get_setting(user_id, key)
        if existing:
            await self.db.delete(existing)
            await self.db.commit()
            return True
        return False
    
    async def batch_get_settings(self, user_id: int, keys: List[str]) -> List[UserSyncSetting]:
        """
        Get multiple settings by keys.
        """
        stmt = select(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id,
            UserSyncSetting.key.in_(keys)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def batch_upsert_settings(
        self, 
        user_id: int, 
        settings: List[Dict[str, Any]]
    ) -> Tuple[List[UserSyncSetting], List[str]]:
        """
        Batch upsert settings. Continues on conflict, recording conflicting keys.
        """
        successful = []
        conflicts = []
        
        for setting_data in settings:
            key = setting_data.get('key')
            value = setting_data.get('value')
            expected_version = setting_data.get('expected_version')
            
            if not key:
                continue
            
            setting, success, error = await self.upsert_setting(
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
    
    async def delete_all_settings(self, user_id: int) -> int:
        """
        Delete all settings for a user.
        """
        stmt = delete(UserSyncSetting).filter(
            UserSyncSetting.user_id == user_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
