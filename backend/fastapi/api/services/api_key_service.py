# api_key_service.py
"""
API Key Service for Fine-Grained Access Control (#1264)

Provides functionality for:
- API key creation and management
- Scope validation
- Key hashing and verification
- Migration support for existing keys
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
import logging

from ..models import ApiKey, User, ApiKeyScope
from ..utils.timestamps import utc_now

logger = logging.getLogger(__name__)


class ApiKeyService:
    """Service for managing API keys with fine-grained scopes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random API key."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def create_api_key(
        self,
        user_id: int,
        name: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[str, ApiKey]:
        """
        Create a new API key with specified scopes.

        Args:
            user_id: ID of the user owning the key
            name: Human-readable name for the key
            scopes: List of scope strings (e.g., ['read', 'users:read'])
            expires_at: Optional expiration date

        Returns:
            Tuple of (plain_api_key, api_key_model)

        Raises:
            ValueError: If scopes are invalid or user doesn't exist
        """
        # Validate user exists
        user_stmt = select(User).where(User.id == user_id)
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Validate scopes
        valid_scopes = {scope.value for scope in ApiKeyScope}
        invalid_scopes = [scope for scope in scopes if scope not in valid_scopes]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        # Generate and hash the key
        plain_key = self.generate_api_key()
        key_hash = self.hash_api_key(plain_key)

        # Create the API key record
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
            is_active=True
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        logger.info(f"Created API key '{name}' for user {user_id} with scopes: {scopes}")
        return plain_key, api_key

    async def verify_api_key(self, api_key: str) -> Optional[ApiKey]:
        """
        Verify an API key and return the key record if valid.

        Args:
            api_key: The plain API key to verify

        Returns:
            ApiKey instance if valid and active, None otherwise
        """
        key_hash = self.hash_api_key(api_key)

        stmt = select(ApiKey).where(
            and_(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,
                or_(
                    ApiKey.expires_at.is_(None),
                    ApiKey.expires_at > utc_now()
                )
            )
        )

        result = await self.db.execute(stmt)
        key_record = result.scalar_one_or_none()

        if key_record:
            # Update last used timestamp
            key_record.last_used_at = utc_now()
            await self.db.commit()

        return key_record

    async def validate_scopes(self, api_key_record: ApiKey, required_scopes: List[str]) -> bool:
        """
        Validate that an API key has the required scopes.

        Args:
            api_key_record: The ApiKey instance
            required_scopes: List of required scope strings

        Returns:
            True if the key has all required scopes, False otherwise
        """
        if not required_scopes:
            return True  # No scopes required

        key_scopes = set(api_key_record.scopes)
        required_scopes_set = set(required_scopes)

        return required_scopes_set.issubset(key_scopes)

    async def get_user_api_keys(self, user_id: int) -> List[ApiKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            List of ApiKey instances
        """
        stmt = select(ApiKey).where(ApiKey.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def revoke_api_key(self, key_id: int, user_id: int) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: API key ID
            user_id: User ID (for ownership validation)

        Returns:
            True if key was revoked, False if not found or not owned by user
        """
        stmt = (
            update(ApiKey)
            .where(
                and_(
                    ApiKey.id == key_id,
                    ApiKey.user_id == user_id,
                    ApiKey.is_active == True
                )
            )
            .values(is_active=False, updated_at=utc_now())
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        success = result.rowcount > 0
        if success:
            logger.info(f"Revoked API key {key_id} for user {user_id}")

        return success

    async def update_api_key_scopes(
        self,
        key_id: int,
        user_id: int,
        new_scopes: List[str]
    ) -> bool:
        """
        Update the scopes of an API key.

        Args:
            key_id: API key ID
            user_id: User ID (for ownership validation)
            new_scopes: New list of scopes

        Returns:
            True if updated successfully, False otherwise

        Raises:
            ValueError: If scopes are invalid
        """
        # Validate scopes
        valid_scopes = {scope.value for scope in ApiKeyScope}
        invalid_scopes = [scope for scope in new_scopes if scope not in valid_scopes]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")

        stmt = (
            update(ApiKey)
            .where(
                and_(
                    ApiKey.id == key_id,
                    ApiKey.user_id == user_id,
                    ApiKey.is_active == True
                )
            )
            .values(scopes=new_scopes, updated_at=utc_now())
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        success = result.rowcount > 0
        if success:
            logger.info(f"Updated scopes for API key {key_id}: {new_scopes}")

        return success

    async def migrate_legacy_keys(self, user_id: int) -> List[ApiKey]:
        """
        Migrate legacy API keys to the new scoped system.

        This method can be called during deployment to give existing keys
        full access temporarily, allowing gradual migration.

        Args:
            user_id: User ID

        Returns:
            List of migrated ApiKey instances
        """
        # This is a placeholder for migration logic
        # In a real implementation, you might:
        # 1. Find existing keys from a legacy table
        # 2. Create new scoped keys with appropriate permissions
        # 3. Mark legacy keys as migrated

        logger.info(f"Migration placeholder called for user {user_id}")
        return []

    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired API keys.

        Returns:
            Number of keys deactivated
        """
        stmt = (
            update(ApiKey)
            .where(
                and_(
                    ApiKey.is_active == True,
                    ApiKey.expires_at.isnot(None),
                    ApiKey.expires_at <= utc_now()
                )
            )
            .values(is_active=False, updated_at=utc_now())
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Cleaned up {count} expired API keys")

        return count

    async def get_api_key_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get statistics about a user's API keys.

        Args:
            user_id: User ID

        Returns:
            Dictionary with key statistics
        """
        stmt = select(ApiKey).where(ApiKey.user_id == user_id)
        result = await self.db.execute(stmt)
        keys = result.scalars().all()

        active_keys = [k for k in keys if k.is_active]
        expired_keys = [k for k in keys if not k.is_active and k.expires_at and k.expires_at <= utc_now()]

        # Count scopes usage
        scope_counts = {}
        for key in active_keys:
            for scope in key.scopes:
                scope_counts[scope] = scope_counts.get(scope, 0) + 1

        return {
            "total_keys": len(keys),
            "active_keys": len(active_keys),
            "expired_keys": len(expired_keys),
            "scope_usage": scope_counts
        }