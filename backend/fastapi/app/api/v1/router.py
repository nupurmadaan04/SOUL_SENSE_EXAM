from fastapi import APIRouter

from app.routers import (
    auth, users, profiles, assessments, 
    questions, analytics, journal, health,
    settings_sync, community
)

api_router = APIRouter()

# Health check at API root level
api_router.include_router(health.router, tags=["Health"])

# Domain routers with explicit prefixes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(journal.router, prefix="/journal", tags=["Journal"])
api_router.include_router(settings_sync.router, prefix="/sync", tags=["Settings Sync"])
api_router.include_router(community.router, prefix="/community", tags=["Community"])
