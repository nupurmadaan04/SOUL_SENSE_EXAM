"""
Root app models loader.

This module dynamically loads models from the root app/models.py file
to avoid namespace collision with the local backend app package.

All backend services and routers should import models from this module
instead of trying to import from 'app.models' directly.

Usage:
    from api.root_models import User, Score, Question, etc.
"""
from pathlib import Path
import importlib.util

# Get project root (SOUL_SENSE_EXAM directory)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Load models from root app using importlib to avoid namespace collision
_models_path = ROOT_DIR / "app" / "models.py"
_spec = importlib.util.spec_from_file_location("root_app_models", _models_path)
_models_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_models_module)

# Re-export all model classes
Base = _models_module.Base
User = _models_module.User
Score = _models_module.Score
Response = _models_module.Response
Question = _models_module.Question
QuestionCategory = _models_module.QuestionCategory
JournalEntry = _models_module.JournalEntry
UserSettings = _models_module.UserSettings
MedicalProfile = _models_module.MedicalProfile
PersonalProfile = _models_module.PersonalProfile
UserStrengths = _models_module.UserStrengths
UserEmotionalPatterns = _models_module.UserEmotionalPatterns
UserSyncSetting = _models_module.UserSyncSetting
LoginAttempt = _models_module.LoginAttempt
RefreshToken = _models_module.RefreshToken

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
    'LoginAttempt',
    'RefreshToken',
]
