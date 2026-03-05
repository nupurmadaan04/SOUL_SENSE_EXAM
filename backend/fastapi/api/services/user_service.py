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
from fastapi import HTTPException, status

# Import models from models module
from ..models import User, UserSettings, MedicalProfile, PersonalProfile, UserStrengths, UserEmotionalPatterns, Score
import bcrypt


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Offload CPU-bound hashing to thread pool to avoid blocking event loop
        password_hash = await asyncio.to_thread(hash_password, password)
        
        new_user = User(
            username=username,
            password_hash=password_hash,
            created_at=datetime.now(UTC).isoformat()
        )

        try:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user"
            )

    async def delete_user(self, user_id: int, permanent: bool = False) -> bool:
        """Delete a user (Async)."""
        user = await self.get_user_by_id(user_id, include_deleted=permanent)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        try:
            if permanent:
                await self.db.delete(user)
            else:
                user.is_deleted = True
                user.is_active = False
                user.deleted_at = datetime.now(UTC)
                
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
            print(f"[CLEANUP] Purged {count} expired accounts")
            
        return count

    async def get_user_detail(self, user_id: int) -> dict:
        """Get detailed user information (Async)."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Count total assessments
        stmt = select(func.count(Score.id)).filter(Score.user_id == user_id)
        result = await self.db.execute(stmt)
        total_assessments = result.scalar() or 0

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
            "total_assessments": total_assessments
        }

    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp (Async)."""
        user = await self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.now(UTC).isoformat()
            await self.db.commit()
