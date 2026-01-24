from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings_instance
from .routers import health, assessments, auth, users, profiles, analytics, questions, journal

# Load and validate settings on import
settings = get_settings_instance()


class VersionHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = "1.0"
        return response


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
    
    # Version header middleware
    app.add_middleware(VersionHeaderMiddleware)
    
    # Register V1 API Router
    app.include_router(api_v1_router, prefix="/api/v1")
    
    # Register Health endpoints at root level for orchestration
    app.include_router(health_router, tags=["Health"])

    # Root endpoint - version discovery
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "SoulSense API",
            "versions": [
                {"version": "v1", "status": "current", "path": "/api/v1"}
            ],
            "documentation": "/docs"
        }

    @app.on_event("startup")
    async def startup_event():
        app.state.settings = settings
        print("✅ SoulSense API started successfully")
        print(f"🌐 Environment: {settings.app_env}")
        print(f"🔧 Debug mode: {settings.debug}")
        print(f"💾 Database: {settings.database_url}")
        print(f"📋 API available at /api/v1")

    return app


app = create_app()
