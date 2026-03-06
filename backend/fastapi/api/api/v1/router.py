from fastapi import APIRouter

from ...routers import (
    auth, users, profiles, assessments, 
    settings_sync, community, contact, exams, export, deep_dive,
    goals, questions, analytics, journal, health,
    gamification, audit, tasks, consent, surveys, advanced_analytics, 
    archival, notifications, flags, search, team_vision,
    api_keys, tamper_evident_audit, dlq
)

api_router = APIRouter()

# Health check at API root level
api_router.include_router(health.router, tags=["Health"])

# Domain routers with explicit prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(team_vision.router, prefix="/team-vision", tags=["Team EI - Vision Documents"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(exams.router, prefix="/exams", tags=["Exams"])
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(advanced_analytics.router, prefix="/analytics/advanced", tags=["Advanced Analytics"])
api_router.include_router(archival.router, prefix="/archival", tags=["GDPR Archival & Purge"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(journal.router, prefix="/journal", tags=["Journal"])
api_router.include_router(settings_sync.router, prefix="/sync", tags=["Settings Sync"])
api_router.include_router(community.router, prefix="/community", tags=["Community"])
api_router.include_router(contact.router, prefix="/contact", tags=["Contact"])
api_router.include_router(export.router, prefix="/reports/export", tags=["Exports"])
api_router.include_router(deep_dive.router, prefix="/deep-dive", tags=["Deep Dive"])
api_router.include_router(goals.router, prefix="/goals", tags=["Goals"])
api_router.include_router(gamification.router, prefix="/gamification", tags=["Gamification"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Background Tasks"])
api_router.include_router(consent.router, prefix="/consent", tags=["Consent"])
api_router.include_router(surveys.router, prefix="/surveys", tags=["Surveys"])
api_router.include_router(flags.router, prefix="/admin/flags", tags=["Feature Flags"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(tamper_evident_audit.router, prefix="/tamper-evident-audit", tags=["Tamper-Evident Audit"])
api_router.include_router(dlq.router, prefix="/admin/dlq", tags=["Dead-Letter Queue (Admin)"])
