from fastapi import FastAPI, Request
import asyncio
import logging
import traceback
import uuid
import time
from fastapi.responses import JSONResponse
# Triggering reload for new community routes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_settings_instance
from .api.v1.router import api_router as api_v1_router
from .routers.health import router as health_router

# Load and validate settings on import
settings = get_settings_instance()


class VersionHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if "X-API-Version" not in response.headers:
            response.headers["X-API-Version"] = "1.0"
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API response times and performance metrics.
    Logs slow requests and adds performance headers.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Add performance header
        response.headers["X-Process-Time"] = f"{process_time:.2f}"

        # Log slow requests (> 500ms)
        if process_time > 500:
            logger = logging.getLogger("api.performance")
            logger.warning(
                f"Slow request: {request.method} {request.url.path} took {process_time:.2f}ms"
            )

        # Log all requests in debug mode
        settings = get_settings_instance()
        if settings.debug:
            logger = logging.getLogger("api.requests")
            logger.info(
                f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms"
            )

        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="SoulSense API",
        description="Comprehensive REST API for SoulSense EQ Test Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Performance Monitoring Middleware (inner-most for accurate timing)
    app.add_middleware(PerformanceMonitoringMiddleware)

    # GZip compression middleware for response optimization
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

    # Security Headers Middleware
    from .middleware.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS middleware
    origins = settings.BACKEND_CORS_ORIGINS
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        expose_headers=["X-API-Version"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )
    
    # Version header middleware
    app.add_middleware(VersionHeaderMiddleware)
    
    # Register V1 API Router
    app.include_router(api_v1_router, prefix="/api/v1")

    # Register Health endpoints at root level for orchestration
    app.include_router(health_router, tags=["Health"])

    from .exceptions import APIException
    from .constants.errors import ErrorCode

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger = logging.getLogger("api.main")
        
        if settings.debug:
            # Safe for local dev: print full traceback to stdout and log error details
            traceback.print_exc()
            logger.error(f"Unhandled Exception: {exc}")
            error_details = {"error": str(exc), "type": type(exc).__name__}
            message = f"Internal Server Error: {exc}"
        else:
            # Production: Log the error safely without stdout pollution, 
            # preserving traceback in structured logs via exc_info=True
            logger.error("Internal Server Error occurred", exc_info=True)
            # strictly zero code artifacts or tracebacks in production response
            error_details = None
            message = "Internal Server Error"
        
        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": message,
                "details": error_details
            }
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
        
        # Generate a unique instance ID for this server session
        # All JWTs will include this ID; tokens from previous instances are rejected
        app.state.server_instance_id = str(uuid.uuid4())
        print(f"[OK] Server instance ID: {app.state.server_instance_id}")
        
        # Initialize database tables
        try:
            from .services.db_service import Base, engine, AsyncSessionLocal
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("[OK] Database tables initialized/verified")
            
            # Start background task for soft-delete cleanup
            async def purge_task_loop():
                while True:
                    try:
                        print("[CLEANUP] Starting scheduled purge of expired accounts...")
                        async with AsyncSessionLocal() as db:
                            from .services.user_service import UserService
                            user_service = UserService(db)
                            await user_service.purge_deleted_users(settings.deletion_grace_period_days)
                    except Exception as e:
                        print(f"[ERROR] Soft-delete cleanup task failed: {e}")
                    
                    # Run once every 24 hours
                    await asyncio.sleep(24 * 3600)
            
            asyncio.create_task(purge_task_loop())
            print("[OK] Soft-delete cleanup task scheduled (runs every 24h)")
            
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            
        print("[OK] SoulSense API started successfully")
        print(f"[ENV] Environment: {settings.app_env}")
        print(f"[CONFIG] Debug mode: {settings.debug}")
        print(f"[DB] Database: {settings.database_url}")
        print(f"[API] API available at /api/v1")

    return app


app = create_app()
