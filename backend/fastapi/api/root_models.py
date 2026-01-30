"""
Root app models loader.

This module loads models from the root app/models.py file.
Because we added the project root to sys.path in config.py,
we can directly import from 'app.models' without dynamic loading hacks.

All backend services and routers should import models from this module
to maintain a Clean Architecture boundary, although direct import is now possible.

Usage:
    from api.root_models import User, Score, Question, etc.
"""
from app.models import (
    Base,
    User,
    Score,
    Response,
    Question,
    QuestionCategory,
    JournalEntry,
    UserSettings,
    MedicalProfile,
    PersonalProfile,
    UserStrengths,
    UserEmotionalPatterns,
    UserSyncSetting
)

# Export all for easy discovery
__all__ = [
    'Base',
    'User', 
    'Score',
    'Response',
    'Question',
    'QuestionCategory',
    'JournalEntry',
    'UserSettings',
    'MedicalProfile',
    'PersonalProfile',
    'UserStrengths',
    'UserEmotionalPatterns',
    'UserSyncSetting',
]
