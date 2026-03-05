"""
Root app models loader.

This module provides a consistent way to import models from the root app/models.py
file, avoiding namespace collisions and import hangs.
"""
from pathlib import Path
import sys
import os

# Get project root (SOUL_SENSE_EXAM directory)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Ensure the root directory is in sys.path so 'import app' works correctly
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load models from root app using standard import
# This is much safer than importlib for SQLAlchemy models in test environments
try:
    import app.models as _models_module
except ImportError:
    # Very fallback: try to find it via absolute path if standard import fails
    import importlib.util
    _models_path = ROOT_DIR / "app" / "models.py"
    _spec = importlib.util.spec_from_file_location("root_app_models_final", _models_path)
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
AnalyticsEvent = _models_module.AnalyticsEvent
OTP = _models_module.OTP
PasswordHistory = _models_module.PasswordHistory
UserSession = _models_module.UserSession
SatisfactionRecord = _models_module.SatisfactionRecord
SatisfactionHistory = _models_module.SatisfactionHistory
AssessmentResult = _models_module.AssessmentResult
AuditLog = _models_module.AuditLog
ExportRecord = _models_module.ExportRecord
Achievement = _models_module.Achievement
UserAchievement = _models_module.UserAchievement
UserStreak = _models_module.UserStreak
UserXP = _models_module.UserXP
Challenge = _models_module.Challenge
UserChallenge = _models_module.UserChallenge
TokenRevocation = _models_module.TokenRevocation

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
    'AnalyticsEvent',
    'OTP',
    'PasswordHistory',
    'UserSession',
    'SatisfactionRecord',
    'SatisfactionHistory',
    'AssessmentResult',
    'AuditLog',
    'ExportRecord',
    'Achievement',
    'UserAchievement',
    'UserStreak',
    'UserXP',
    'Challenge',
    'UserChallenge',
    'TokenRevocation',
]
