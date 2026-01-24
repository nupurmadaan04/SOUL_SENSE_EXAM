from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import health, assessments, auth, users, profiles, analytics, questions, journal, settings_sync

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SoulSense API",
        description="Comprehensive REST API for SoulSense EQ Test Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register all routers
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, prefix="/auth", tags=["authentication"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
    app.include_router(assessments.router, prefix="/api/assessments", tags=["assessments"])
    app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(journal.router, prefix="/api", tags=["journal"])
    app.include_router(settings_sync.router, prefix="/api/sync", tags=["settings-sync"])

    @app.on_event("startup")
    async def startup_event():
        app.state.settings = settings
        print("✅ SoulSense API started successfully")
        print(f"🌐 Environment: {settings.app_env}")
        print(f"🔧 Debug mode: {settings.debug}")
        print(f"💾 Database: {settings.database_url}")
        print(f"📋 Registered routers: health, auth, users, profiles, assessments, questions, analytics, settings-sync")

    return app


app = create_app()
