"""
User Service Layer

Handles CRUD operations for users with proper authorization and validation.
"""

from typing import Optional, List, Tuple
from datetime import datetime, timedelta, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

# Import models from models module
from ..models import User, UserSettings, MedicalProfile, PersonalProfile, UserStrengths, UserEmotionalPatterns, Score, UserSession
from .db_error_handler import safe_db_query, DatabaseConnectionError
import bcrypt
import logging

logger = logging.getLogger(__name__)




class UserService:
    """Service for managing user CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by ID."""
        try:
            return safe_db_query(
                self.db,
                lambda: self.db.query(User).filter(User.id == user_id).filter(User.is_deleted == False if not include_deleted else True).first(),
                "get user by ID"
            )
        except DatabaseConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

    async def get_user_by_username(self, username: str, include_deleted: bool = False) -> Optional[User]:
        """Retrieve a user by username."""
        try:
            return safe_db_query(
                self.db,
                lambda: self.db.query(User).filter(User.username == username).filter(User.is_deleted == False if not include_deleted else True).first(),
                "get user by username"
            )
        except DatabaseConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

    async def get_all_users(self, skip: int = 0, limit: int = 100, include_deleted: bool = False) -> List[User]:
        """Retrieve all users with pagination."""
        try:
            return safe_db_query(
                self.db,
                lambda: self.db.query(User).filter(User.is_deleted == False if not include_deleted else True).offset(skip).limit(limit).all(),
                "get all users"
            )
        except DatabaseConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

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
            existing_user = self.get_user_by_username(username, include_deleted=True)
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

        # Hash password and create user
        password_hash = get_password_hash(password)
        
        new_user = User(
            username=username,
            password_hash=password_hash,
            created_at=datetime.now(UTC).isoformat()
        )

        try:
            self.db.add(new_user)
            await self.db.flush() # Ensure ID is generated

            # Record initial password in history
            self.db.add(PasswordHistory(user_id=new_user.id, password_hash=password_hash))
            
            await self.db.commit()
            await self.db.refresh(new_user)
            return new_user
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        except (OperationalError, DatabaseError) as e:
            self.db.rollback()
            logger.error(f"Database connection error during user creation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later."
            )

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

        # Update username if provided
        if username:
            username = username.strip().lower()
            if username != user.username:
                # Check if new username is already taken (including soft-deleted)
                existing_user = await self.get_user_by_username(username, include_deleted=True)
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
                user.username = username

        # Update password if provided
        if password:
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

        try:
            # Increment version for cache consistency (#1143)
            user.version = (getattr(user, 'version', 0) or 0) + 1
            
            await self.db.commit()
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
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user"
            )

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
            
        try:
            # Increment version for cache consistency (#1143)
            user.version = (getattr(user, 'version', 0) or 0) + 1
            
            await self.db.commit()
            await self.db.refresh(user)
            
            # Distribute Cache Invalidation and set authoritative version (#1143)
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            await cache_service.broadcast_invalidation(f"user_role:{user_id}", is_prefix=False)
            
            return user
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

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

        try:
            if permanent:
                await self.db.delete(user)
            else:
                user.is_deleted = True
                user.is_active = False
                user.deleted_at = datetime.now(UTC)
                # Bump version to clear cache for deleted account (#1143)
                user.version = (getattr(user, 'version', 0) or 0) + 1
                
            await self.db.commit()
            
            if not permanent:
                 from .cache_service import cache_service
                 await cache_service.update_version("user", user.id, user.version)
                 await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
                 
            return True
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}"
            )

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
        
        try:
            await self.db.commit()
            await self.db.refresh(user)
            
            from .cache_service import cache_service
            await cache_service.update_version("user", user.id, user.version)
            await cache_service.broadcast_invalidation(f"user_data:{user.id}", is_prefix=False)
            
            return user
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reactivate user: {str(e)}"
            )

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
            print(f"[CLEANUP] Purged {count} expired accounts")
            
        return count

    async def get_user_detail(self, user_id: int) -> dict:
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
        count_stmt = select(func.count(Score.id)).join(
            UserSession, Score.session_id == UserSession.session_id
        ).filter(UserSession.user_id == user_id)
        
        count_result = await self.db.execute(count_stmt)
        total_assessments = count_result.scalar() or 0

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
