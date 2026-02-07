import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from app.db import safe_db_context
from app.models import (
    User, UserProfile, PersonalProfile, MedicalProfile, 
    UserStrengths, UserEmotionalPatterns
)
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class ProfileService:
    """
    Service layer for User Profile operations.
    Handles aggregation and persistence of user profile data.
    """

    @staticmethod
    def get_user_profile(username: str) -> Optional[User]:
        """
        Fetches the complete user object with all relationships loaded.
        Uses joinedload to ensure data is available after session close.
        """
        try:
            from sqlalchemy.orm import joinedload
            with safe_db_context() as session:
                session.expire_on_commit = False
                user = session.query(User)\
                    .options(
                        joinedload(User.personal_profile),
                        joinedload(User.medical_profile),
                        joinedload(User.strengths),
                        joinedload(User.emotional_patterns)
                    )\
                    .filter_by(username=username)\
                    .first()
                
                if user:
                    # Touch attributes to ensure they are loaded if joinedload fails for some reason
                    # (though joinedload should suffice)
                    _ = user.personal_profile
                    _ = user.medical_profile
                    _ = user.strengths
                    _ = user.emotional_patterns
                    
                return user 
        except Exception as e:
            logger.error(f"Failed to get profile for {username}: {e}")
            return None

    @staticmethod
    def update_personal_profile(username: str, data: Dict[str, Any]) -> bool:
        """
        Updates PersonalProfile for a user.
        Data dict keys should match PersonalProfile attributes.
        """
        try:
            with safe_db_context() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False
                
                profile = user.personal_profile
                if not profile:
                    profile = PersonalProfile(user_id=user.id)
                    user.personal_profile = profile
                
                # Generic set attr
                for key, value in data.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
                
                profile.last_updated = datetime.now(UTC).isoformat()
                return True
        except Exception as e:
            logger.error(f"Failed to update personal profile: {e}")
            raise DatabaseError("Failed to update personal profile", original_exception=e)

    @staticmethod
    def update_medical_profile(username: str, data: Dict[str, Any]) -> bool:
        """Updates MedicalProfile for a user."""
        try:
            with safe_db_context() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False
                
                profile = user.medical_profile
                if not profile:
                    profile = MedicalProfile(user_id=user.id)
                    user.medical_profile = profile
                
                for key, value in data.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
                
                profile.last_updated = datetime.now(UTC).isoformat()
                return True
        except Exception as e:
            logger.error(f"Failed to update medical profile: {e}")
            raise DatabaseError("Failed to update medical profile", original_exception=e)

    @staticmethod
    def update_strengths(username: str, data: Dict[str, Any]) -> bool:
        """Updates UserStrengths and EmotionalPatterns."""
        try:
            with safe_db_context() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False
                
                # 1. Strengths
                strengths = user.strengths
                if not strengths:
                    strengths = UserStrengths(user_id=user.id)
                    user.strengths = strengths
                
                # Map specific fields if needed or generic loop
                # The UI passes specific keys usually.
                for key, value in data.items():
                    if hasattr(strengths, key):
                        setattr(strengths, key, value)
                    # Special check: Emotional Patterns might be mixed in `data` or separate?
                    # The UI separated them. We can have a separate method or shared.
                
                strengths.last_updated = datetime.now(UTC).isoformat()
                return True
        except Exception as e:
            logger.error(f"Failed to update strengths: {e}")
            raise DatabaseError("Failed to update strengths", original_exception=e)

    @staticmethod
    def update_emotional_patterns(username: str, data: Dict[str, Any]) -> bool:
        """Updates UserEmotionalPatterns."""
        try:
            with safe_db_context() as session:
                user = session.query(User).filter_by(username=username).first()
                if not user:
                    return False
                
                ep = user.emotional_patterns
                if not ep:
                    ep = UserEmotionalPatterns(user_id=user.id)
                    user.emotional_patterns = ep
                
                for key, value in data.items():
                    if hasattr(ep, key):
                        setattr(ep, key, value)
                
                ep.last_updated = datetime.now(UTC).isoformat()
                return True
        except Exception as e:
            logger.error(f"Failed to update emotional patterns: {e}")
            raise DatabaseError("Failed to update emotional patterns", original_exception=e)
