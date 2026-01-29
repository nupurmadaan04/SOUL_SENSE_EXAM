from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_settings_instance
from .api.v1.router import api_router as api_v1_router
from .routers.health import router as health_router

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

    # Security Headers Middleware
    from .middleware.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS middleware
    # If in production, ensure we are not allowing all origins blindly unless intended
    origins = settings.cors_origins
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-API-Version"],
        max_age=3600, # Cache preflight requests for 1 hour
    )
    
    # Version header middleware
    app.add_middleware(VersionHeaderMiddleware)
    
    # Register V1 API Router
    app.include_router(api_v1_router, prefix="/api/v1")
    
    # Register Health endpoints at root level for orchestration
    app.include_router(health_router, tags=["Health"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        print(f"[ERROR] GLOBAL EXCEPTION: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(exc)}
        )

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
        
        # Initialize database tables
        try:
            from .services.db_service import Base, engine
            Base.metadata.create_all(bind=engine)
            print("[OK] Database tables initialized/verified")
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            
        print("[OK] SoulSense API started successfully")
        print(f"[ENV] Environment: {settings.app_env}")
        print(f"[CONFIG] Debug mode: {settings.debug}")
        print(f"[DB] Database: {settings.database_url}")
        print(f"[API] API available at /api/v1")

    return app


app = create_app()
