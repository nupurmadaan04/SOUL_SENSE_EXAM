"""
User Service Layer (Async Version)

Handles CRUD operations for users with proper authorization and validation.
"""

from typing import Optional, List, Tuple, Any
from datetime import datetime, timedelta, UTC
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError
from fastapi import HTTPException, status

# Import models from models module
from ..models import User, UserSettings, MedicalProfile, PersonalProfile, UserStrengths, UserEmotionalPatterns, Score, UserSession
from ..utils.timestamps import utc_now_iso
from .db_service import transaction_scope, deadlock_retry
import bcrypt
import logging

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password for storing (Blocking call - should be run in thread)."""
    # Note: bcrypt is CPU bound and synchronous. In a high-concurrency app,
    # this should ideally be offloaded to a thread pool.
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class UserService:
    """Service for managing user CRUD operations (Async)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by ID (Async)."""
        stmt = select(User).filter(User.id == user_id)
        if not include_deleted:
            stmt = stmt.filter(User.is_deleted == False)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by username (Async)."""
        stmt = select(User).filter(User.username == username)
        if not include_deleted:
            stmt = stmt.filter(User.is_deleted == False)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_users(self, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[User]:
        """Retrieve all users with pagination (Async)."""
        stmt = select(User)
        if not include_deleted:
            stmt = stmt.filter(User.is_deleted == False)
        
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_user(self, username: str, password: str) -> User:
        """Create a new user with hashed password (Async)."""
        username = username.strip().lower()

        if await self.get_user_by_username(username, include_deleted=True):
        """Retrieve a user by ID."""
        try:
            stmt = select(User).filter(User.id == user_id)
            if not include_deleted:
                stmt = stmt.filter(User.is_deleted == False)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except (OperationalError, DatabaseError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

    async def get_user_by_username(self, username: str, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by username."""
        try:
            stmt = select(User).filter(User.username == username)
            if not include_deleted:
                stmt = stmt.filter(User.is_deleted == False)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except (OperationalError, DatabaseError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

    async def get_all_users(self, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[User]:
        """Retrieve all users with pagination."""
        try:
            stmt = select(User)
            if not include_deleted:
                stmt = stmt.filter(User.is_deleted == False)
            stmt = stmt.offset(skip).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except (OperationalError, DatabaseError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

    @deadlock_retry()
    async def create_user(self, username: str, password: str) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            
        Returns:
            Created User object
            
        Raises:
            HTTPException: If username already exists or database error
        """
        # Normalize username
        username = username.strip().lower()

        # Check if username already exists (including soft-deleted for collision prevention)
        try:
            existing_user = await self.get_user_by_username(username, include_deleted=True)
        except HTTPException as e:
            if e.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                raise  # Re-raise database connection errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            ) from e

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Offload CPU-bound hashing to thread pool to avoid blocking event loop
        password_hash = await asyncio.to_thread(hash_password, password)
        # Hash password and create user
        password_hash = get_password_hash(password)
        
        new_user = User(
            username=username,
            password_hash=password_hash,
            created_at=datetime.now(UTC).isoformat()
            created_at=utc_now_iso()
        )

        async with transaction_scope(self.db):
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            return new_user
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )

    async def update_user(self, user_id: int, username: Optional[str] = None, password: Optional[str] = None) -> User:
        """Update user information (Async)."""
            await self.db.flush() # Ensure ID is generated

            # Record initial password in history
            self.db.add(PasswordHistory(user_id=new_user.id, password_hash=password_hash))
            
            await self.db.refresh(new_user)
            return new_user

    @deadlock_retry()
    async def update_user(self, user_id: int, username: Optional[str] = None, password: Optional[str] = None) -> User:
        """
        Update user information.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if username:
            username = username.strip().lower()
            if username != user.username:
                if await self.get_user_by_username(username, include_deleted=True):
                # Check if new username is already taken (including soft-deleted)
                existing_user = await self.get_user_by_username(username, include_deleted=True)
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
                user.username = username

        if password:
            user.password_hash = await asyncio.to_thread(hash_password, password)

        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            await self.db.rollback()
            # Check password history
            from sqlalchemy import desc
            stmt = select(PasswordHistory.password_hash).filter(
                PasswordHistory.user_id == user.id
            ).order_by(desc(PasswordHistory.created_at)).limit(PASSWORD_HISTORY_LIMIT)
            result = await self.db.execute(stmt)
            history = result.scalars().all()
            
            if check_password_history(password, history):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reuse any of your last 5 passwords"
                )

            hashed_pw = get_password_hash(password)
            user.password_hash = hashed_pw
            # Record the new password in history
            self.db.add(PasswordHistory(user_id=user.id, password_hash=hashed_pw))

        # Check if role is provided (assuming user has role or is_admin attribute)
        # Note: Added for Cache Invalidation pattern (#1123)

        async with transaction_scope(self.db):
            # Increment version for cache consistency (#1143)
            user.version = (getattr(user, 'version', 0) or 0) + 1
            
            await self.db.refresh(user)
            
            # Broadcast cache invalidation and set authoritative version (#1143)
            try:
                from .cache_service import cache_service
                # Set latest version in Redis as the 'source of truth'
                await cache_service.update_version("user", user.id, user.version)
                # Still broadcast invalidation for nodes that *can* hear it
                await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
                await cache_service.broadcast_invalidation(f"user_role:{user.id}", is_prefix=False)
            except ImportError:
                pass
                
            return user

    @deadlock_retry()
    async def update_user_role(self, user_id: int, is_admin: bool, pii_viewer: bool = False) -> User:
        """
        Update user roles and explicitly broadcast cache invalidation.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Safely set attributes if they exist
        if hasattr(user, 'is_admin'):
            user.is_admin = is_admin
        if hasattr(user, 'role'):
            user.role = "pii_viewer" if pii_viewer else ("admin" if is_admin else "user")
            
        async with transaction_scope(self.db):
            # Increment version for cache consistency (#1143)
            user.version = (getattr(user, 'version', 0) or 0) + 1
            
            await self.db.refresh(user)
            
            # Distribute Cache Invalidation and set authoritative version (#1143)
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            await cache_service.broadcast_invalidation(f"user_role:{user_id}", is_prefix=False)
            
            return user

    async def delete_user(self, user_id: int, permanent: bool = False) -> bool:
        """Delete a user (Async)."""
    @deadlock_retry()
    async def delete_user(self, user_id: int, permanent: bool = False) -> bool:
        """
        Delete a user. Supports soft delete by default.
        """
        user = await self.get_user_by_id(user_id, include_deleted=permanent)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        async with transaction_scope(self.db):
            if permanent:
                await self.db.delete(user)
            else:
                user.is_deleted = True
                user.is_active = False
                user.deleted_at = datetime.now(UTC)
                # Bump version to clear cache for deleted account (#1143)
                user.version = (getattr(user, 'version', 0) or 0) + 1
                
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}"
            )

    async def purge_deleted_users(self, grace_period_days: int) -> int:
        """Permanently delete expired users (Async)."""
            if not permanent:
                 from .cache_service import cache_service
                 await cache_service.update_version("user", user.id, user.version)
                 await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
                 
            return True

    @deadlock_retry()
    async def reactivate_user(self, user_id: int) -> User:
        """
        Restore a soft-deleted user.
        """
        user = await self.get_user_by_id(user_id, include_deleted=True)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_deleted = False
        user.is_active = True
        user.deleted_at = None
        user.version = (getattr(user, 'version', 0) or 0) + 1
        
        async with transaction_scope(self.db):
            await self.db.refresh(user)
            
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
            
            return user

    @deadlock_retry()
    async def purge_deleted_users(self, grace_period_days: int) -> int:
        """
        Permanently delete users whose grace period has expired.
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=grace_period_days)
        
        stmt = select(User).filter(
            User.is_deleted == True,
            User.deleted_at <= cutoff_date
        )
        result = await self.db.execute(stmt)
        expired_users = result.scalars().all()
        
        count = 0
        for user in expired_users:
            try:
                await self.db.delete(user)
                count += 1
            except Exception as e:
                print(f"[ERROR] Failed to purge user {user.id}: {e}")
        
        if count > 0:
            await self.db.commit()
        async with transaction_scope(self.db):
            for user in expired_users:
                try:
                    await self.db.delete(user)
                    count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to purge user {user.id}: {e}")
        
        if count > 0:
            print(f"[CLEANUP] Purged {count} expired accounts")
            
        return count

    async def get_user_detail(self, user_id: int) -> dict:
        """Get detailed user information (Async)."""
        user = await self.get_user_by_id(user_id)
        """
        Get detailed user information including relationship status.
        """
        # Load user with related profiles to avoid lazy-loading issues in async
        stmt = select(User).options(
            selectinload(User.settings),
            selectinload(User.medical_profile),
            selectinload(User.personal_profile),
            selectinload(User.strengths),
            selectinload(User.emotional_patterns)
        ).filter(User.id == user_id)
        
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Count total assessments
        stmt = select(func.count(Score.id)).filter(Score.user_id == user_id)
        result = await self.db.execute(stmt)
        total_assessments = result.scalar() or 0
        count_stmt = select(func.count(Score.id)).join(
            UserSession, Score.session_id == UserSession.session_id
        ).filter(UserSession.user_id == user_id)
        
        count_result = await self.db.execute(count_stmt)
        total_assessments = count_result.scalar() or 0

        # Load relationships explicitly if needed or rely on lazy loading (which is tricky in async)
        # For this example, we assume they are either eager loaded or we check them individually
        
        return {
            "id": user.id,
            "username": user.username,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "has_settings": user.settings is not None,
            "has_medical_profile": user.medical_profile is not None,
            "has_personal_profile": user.personal_profile is not None,
            "has_strengths": user.strengths is not None,
            "has_emotional_patterns": user.emotional_patterns is not None,
            "total_assessments": total_assessments,
            "onboarding_completed": getattr(user, 'onboarding_completed', False)
        }

    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp (Async)."""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.now(UTC).isoformat()
            await self.db.commit()
        """Update user's last login timestamp and bump version for consistency."""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.now(UTC).isoformat()
            user.version = (getattr(user, 'version', 0) or 1) + 1
            await self.db.commit()
            
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            # We don't necessarily broadcast invalidation for every login pulse
            # unless we cache the 'last_login' value heavily.
