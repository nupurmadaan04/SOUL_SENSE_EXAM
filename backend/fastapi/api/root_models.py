"""
Root app models loader.

This module provides a consistent way to import models from the root app/models.py
file, avoiding namespace collisions and import hangs.
"""
from pathlib import Path
import sys
import os

# Get possible project roots
CUR_DIR = Path(__file__).resolve().parent
ROOT_DIR = CUR_DIR.parent.parent.parent
BACKEND_DIR = CUR_DIR.parent

# Ensure root & backend directories are in sys.path
for p in [str(ROOT_DIR), str(BACKEND_DIR), str(CUR_DIR), "/app"]:
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

# Load models from app using standard import or file search
_models_module = None
try:
    import app.models as _models_module
except Exception:
    pass

if _models_module is None:
    candidate_paths = [
        ROOT_DIR / "app" / "models.py",
        BACKEND_DIR / "app" / "models.py",
        CUR_DIR / "app" / "models.py",
        Path("/app/app/models.py"),
        Path("/app/models.py")
    ]
    import importlib.util
    for p in candidate_paths:
        if p.exists():
            _spec = importlib.util.spec_from_file_location("root_app_models_final", p)
            if _spec and _spec.loader:
                _models_module = importlib.util.module_from_spec(_spec)
                _spec.loader.exec_module(_models_module)
                break

if _models_module is None:
    raise RuntimeError("Could not locate models.py in any expected application path.")

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
AuditLog = _models_module.AuditLog
Goal = _models_module.Goal
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
    'AuditLog',
    'Goal',
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
