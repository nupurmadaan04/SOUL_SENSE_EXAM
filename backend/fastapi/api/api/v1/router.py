from fastapi import APIRouter

from ...routers import (
    auth, users, profiles, assessments, 
    settings_sync, community, contact, exams, export, deep_dive,
    goals
)

api_router = APIRouter()

# Health check at API root level
api_router.include_router(health.router, tags=["Health"])

# Domain routers with explicit prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(exams.router, prefix="/exams", tags=["Exams"])
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(journal.router, prefix="/journal", tags=["Journal"])
api_router.include_router(settings_sync.router, prefix="/sync", tags=["Settings Sync"])
api_router.include_router(community.router, prefix="/community", tags=["Community"])
api_router.include_router(contact.router, prefix="/contact", tags=["Contact"])
api_router.include_router(export.router, prefix="/export", tags=["Exports"])
api_router.include_router(deep_dive.router, prefix="/deep-dive", tags=["Deep Dive"])
api_router.include_router(goals.router, prefix="/goals", tags=["Goals"])

