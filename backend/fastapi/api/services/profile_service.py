"""
Profile Service Layer

Handles CRUD operations for all user profile types:
- UserSettings
- MedicalProfile
- PersonalProfile
- UserStrengths
- UserEmotionalPatterns
"""

from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

# Import models from root_models module (handles namespace collision)
from api.root_models import (
    User,
    MedicalProfile,
    PersonalProfile,
    UserStrengths,
    UserEmotionalPatterns
)


class ProfileService:
    """Service for managing all user profile CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def _verify_user_exists(self, user_id: int) -> User:
        """Verify user exists and return user object."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    # ========================================================================
    # User Settings CRUD
    # ========================================================================

    def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """Get user settings."""
        self._verify_user_exists(user_id)
        return self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    def create_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """Create user settings."""
        self._verify_user_exists(user_id)

        # Check if settings already exist
        existing = self.get_user_settings(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User settings already exist. Use update instead."
            )

        settings = UserSettings(
            user_id=user_id,
            **settings_data,
            updated_at=datetime.utcnow().isoformat()
        )

        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def update_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> UserSettings:
        """Update user settings."""
        settings = self.get_user_settings(user_id)
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found. Create them first."
            )

        # Update only provided fields
        for key, value in settings_data.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def delete_user_settings(self, user_id: int) -> bool:
        """Delete user settings."""
        settings = self.get_user_settings(user_id)
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )

        self.db.delete(settings)
        self.db.commit()
        return True

    # ========================================================================
    # Medical Profile CRUD
    # ========================================================================

    def get_medical_profile(self, user_id: int) -> Optional[MedicalProfile]:
        """Get medical profile."""
        self._verify_user_exists(user_id)
        return self.db.query(MedicalProfile).filter(MedicalProfile.user_id == user_id).first()

    def create_medical_profile(self, user_id: int, profile_data: Dict[str, Any]) -> MedicalProfile:
        """Create medical profile."""
        self._verify_user_exists(user_id)

        # Check if profile already exists
        existing = self.get_medical_profile(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical profile already exists. Use update instead."
            )

        profile = MedicalProfile(
            user_id=user_id,
            **profile_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_medical_profile(self, user_id: int, profile_data: Dict[str, Any]) -> MedicalProfile:
        """Update medical profile."""
        profile = self.get_medical_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical profile not found. Create it first."
            )

        # Update only provided fields
        for key, value in profile_data.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_medical_profile(self, user_id: int) -> bool:
        """Delete medical profile."""
        profile = self.get_medical_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical profile not found"
            )

        self.db.delete(profile)
        self.db.commit()
        return True

    # ========================================================================
    # Personal Profile CRUD
    # ========================================================================

    def get_personal_profile(self, user_id: int) -> Optional[PersonalProfile]:
        """Get personal profile."""
        self._verify_user_exists(user_id)
        return self.db.query(PersonalProfile).filter(PersonalProfile.user_id == user_id).first()

    def create_personal_profile(self, user_id: int, profile_data: Dict[str, Any]) -> PersonalProfile:
        """Create personal profile."""
        self._verify_user_exists(user_id)

        # Check if profile already exists
        existing = self.get_personal_profile(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Personal profile already exists. Use update instead."
            )

        profile = PersonalProfile(
            user_id=user_id,
            **profile_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_personal_profile(self, user_id: int, profile_data: Dict[str, Any]) -> PersonalProfile:
        """Update personal profile."""
        profile = self.get_personal_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal profile not found. Create it first."
            )

        # Update only provided fields
        for key, value in profile_data.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_updated = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_personal_profile(self, user_id: int) -> bool:
        """Delete personal profile."""
        profile = self.get_personal_profile(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal profile not found"
            )

        self.db.delete(profile)
        self.db.commit()
        return True

    # ========================================================================
    # User Strengths CRUD
    # ========================================================================

    def get_user_strengths(self, user_id: int) -> Optional[UserStrengths]:
        """Get user strengths."""
        self._verify_user_exists(user_id)
        return self.db.query(UserStrengths).filter(UserStrengths.user_id == user_id).first()

    def create_user_strengths(self, user_id: int, strengths_data: Dict[str, Any]) -> UserStrengths:
        """Create user strengths."""
        self._verify_user_exists(user_id)

        # Check if strengths already exist
        existing = self.get_user_strengths(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User strengths already exist. Use update instead."
            )

        strengths = UserStrengths(
            user_id=user_id,
            **strengths_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(strengths)
        self.db.commit()
        self.db.refresh(strengths)
        return strengths

    def update_user_strengths(self, user_id: int, strengths_data: Dict[str, Any]) -> UserStrengths:
        """Update user strengths."""
        strengths = self.get_user_strengths(user_id)
        if not strengths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User strengths not found. Create them first."
            )

        # Update only provided fields
        for key, value in strengths_data.items():
            if value is not None and hasattr(strengths, key):
                setattr(strengths, key, value)

        strengths.last_updated = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(strengths)
        return strengths

    def delete_user_strengths(self, user_id: int) -> bool:
        """Delete user strengths."""
        strengths = self.get_user_strengths(user_id)
        if not strengths:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User strengths not found"
            )

        self.db.delete(strengths)
        self.db.commit()
        return True

    # ========================================================================
    # Emotional Patterns CRUD
    # ========================================================================

    def get_emotional_patterns(self, user_id: int) -> Optional[UserEmotionalPatterns]:
        """Get emotional patterns."""
        self._verify_user_exists(user_id)
        return self.db.query(UserEmotionalPatterns).filter(UserEmotionalPatterns.user_id == user_id).first()

    def create_emotional_patterns(self, user_id: int, patterns_data: Dict[str, Any]) -> UserEmotionalPatterns:
        """Create emotional patterns."""
        self._verify_user_exists(user_id)

        # Check if patterns already exist
        existing = self.get_emotional_patterns(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Emotional patterns already exist. Use update instead."
            )

        patterns = UserEmotionalPatterns(
            user_id=user_id,
            **patterns_data,
            last_updated=datetime.utcnow().isoformat()
        )

        self.db.add(patterns)
        self.db.commit()
        self.db.refresh(patterns)
        return patterns

    def update_emotional_patterns(self, user_id: int, patterns_data: Dict[str, Any]) -> UserEmotionalPatterns:
        """Update emotional patterns."""
        patterns = self.get_emotional_patterns(user_id)
        if not patterns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emotional patterns not found. Create them first."
            )

        # Update only provided fields
        for key, value in patterns_data.items():
            if value is not None and hasattr(patterns, key):
                setattr(patterns, key, value)

        patterns.last_updated = datetime.utcnow().isoformat()
        self.db.commit()
        self.db.refresh(patterns)
        return patterns

    def delete_emotional_patterns(self, user_id: int) -> bool:
        """Delete emotional patterns."""
        patterns = self.get_emotional_patterns(user_id)
        if not patterns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emotional patterns not found"
            )

        self.db.delete(patterns)
        self.db.commit()
        return True

    # ========================================================================
    # Complete Profile Operations
    # ========================================================================

    def get_complete_profile(self, user_id: int) -> Dict[str, Any]:
        """Get complete user profile with all sub-profiles."""
        user = self._verify_user_exists(user_id)

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "created_at": user.created_at,
                "last_login": user.last_login
            },
            "settings": self.get_user_settings(user_id),
            "medical_profile": self.get_medical_profile(user_id),
            "personal_profile": self.get_personal_profile(user_id),
            "strengths": self.get_user_strengths(user_id),
            "emotional_patterns": self.get_emotional_patterns(user_id)
        }
