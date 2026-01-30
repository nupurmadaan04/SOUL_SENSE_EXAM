"""
User Service Layer

Handles CRUD operations for users with proper authorization and validation.
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

# Import models from root_models module (handles namespace collision)
from api.root_models import User, UserSettings, MedicalProfile, PersonalProfile, UserStrengths, UserEmotionalPatterns, Score
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class UserService:
    """Service for managing user CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieve a user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieve all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, username: str, password: str) -> User:
        """
        Create a new user with hashed password.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            
        Returns:
            Created User object
            
        Raises:
            HTTPException: If username already exists
        """
        # Check if username already exists
        if self.get_user_by_username(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Hash password and create user
        password_hash = hash_password(password)
        
        new_user = User(
            username=username,
            password_hash=password_hash,
            created_at=datetime.utcnow().isoformat()
        )

        try:
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            return new_user
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )

    def update_user(self, user_id: int, username: Optional[str] = None, password: Optional[str] = None) -> User:
        """
        Update user information.
        
        Args:
            user_id: ID of user to update
            username: New username (optional)
            password: New password (optional, will be hashed)
            
        Returns:
            Updated User object
            
        Raises:
            HTTPException: If user not found or username conflict
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update username if provided
        if username and username != user.username:
            # Check if new username is already taken
            if self.get_user_by_username(username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            user.username = username

        # Update password if provided
        if password:
            user.password_hash = hash_password(password)

        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update user"
            )

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user and all related data (cascaded).
        
        Args:
            user_id: ID of user to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            HTTPException: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        try:
            self.db.delete(user)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}"
            )

    def get_user_detail(self, user_id: int) -> dict:
        """
        Get detailed user information including relationship status.
        
        Args:
            user_id: ID of user
            
        Returns:
            Dictionary with user details and relationship flags
            
        Raises:
            HTTPException: If user not found
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Count total assessments
        total_assessments = self.db.query(Score).filter(Score.user_id == user_id).count()

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

    def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow().isoformat()
            self.db.commit()
