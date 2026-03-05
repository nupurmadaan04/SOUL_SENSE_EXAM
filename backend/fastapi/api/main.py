from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Request
import asyncio
import logging
import traceback
import uuid
import time
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
# Triggering reload for new community routes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .config import get_settings_instance
from .api.v1.router import api_router as api_v1_router
from .routers.health import router as health_router
from .utils.limiter import limiter
from .utils.logging_config import setup_logging
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Initialize centralized logging
setup_logging()
logger = logging.getLogger("api.main")

# Load and validate settings on import
settings = get_settings_instance()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    logger = logging.getLogger("api.lifespan")
    
    # STARTUP LOGIC
    logger.info("LIFESPAN BOOT STARTED")
    
    app.state.settings = settings
    
    # Generate a unique instance ID for this server session
    # All JWTs will include this ID; tokens from previous instances are rejected
    app.state.server_instance_id = str(uuid.uuid4())
    logger.info(f"Server instance ID: {app.state.server_instance_id}")
    
    # Initialize database tables
    try:
        from .services.db_service import Base, engine, AsyncSessionLocal
        # Note: metadata.create_all is typically sync, for async we use run_sync
        async def init_models():
            async with engine.begin() as conn:
                # await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
        
        await init_models()
        logger.info("Database tables initialized/verified (Async)")
        
        # Verify database connectivity
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            logger.info("Database connectivity verified (Async)")
        
        # Start background task for soft-delete cleanup
        async def purge_task_loop():
            while True:
                try:
                    logger.info("Starting scheduled purge of expired accounts...", extra={"task": "cleanup"})
                    async with AsyncSessionLocal() as db:
                        from .services.user_service import UserService
                        user_service = UserService(db)
                        await user_service.purge_deleted_users(settings.deletion_grace_period_days)
                    logger.info("Scheduled purge completed successfully", extra={"task": "cleanup"})
                except Exception as e:
                    logger = logging.getLogger("api.purge_task")
                    logger.error(f"Soft-delete cleanup task failed: {e}", exc_info=True)
                    # Continue the loop instead of crashing - the task will retry in 24 hours
                
                # Run once every 24 hours
                await asyncio.sleep(24 * 3600)
        
        purge_task = asyncio.create_task(purge_task_loop())
        app.state.purge_task = purge_task  # Store reference for cleanup
        logger.info("Soft-delete cleanup task scheduled (runs every 24h)")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        # Re-raise to crash the application - don't start with broken DB
        raise
    
    logger.info("Application startup completed successfully")
    
    yield  # API processes requests here
    
    # SHUTDOWN LOGIC
    logger.info("LIFESPAN TEARDOWN STARTED")
    
    # Cancel background tasks
    if hasattr(app.state, 'purge_task'):
        logger.info("Cancelling background purge task...")
        app.state.purge_task.cancel()
        try:
            await app.state.purge_task
        except asyncio.CancelledError:
            logger.info("Background purge task cancelled successfully")
    
    # Dispose database engine if needed
    try:
        from .services.db_service import engine
        logger.info("Disposing database engine...")
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")
    
    logger.info("Application shutdown completed")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class VersionHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
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
                f"Slow request: {request.method} {request.url.path} took {process_time:.2f}ms",
                extra={"request_id": getattr(request.state, 'request_id', 'unknown'), "method": request.method, "path": request.url.path, "duration_ms": process_time}
            )

        # Log all requests in debug mode
        settings = get_settings_instance()
        if settings.debug:
            logger = logging.getLogger("api.requests")
            logger.info(
                f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms",
                extra={"request_id": getattr(request.state, 'request_id', 'unknown'), "status_code": response.status_code}
            )

        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="SoulSense API",
        description="Comprehensive REST API for SoulSense EQ Test Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Correlation ID middleware (outermost for logging reference)
    app.add_middleware(CorrelationIDMiddleware)

    # Attach slowapi limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        if settings.debug:
            # Safe for local dev: print full traceback to stdout and log error details
            traceback.print_exc()
            logger.error(f"Unhandled Exception: {exc}", extra={
                "request_id": request_id,
                "error": str(exc),
                "type": type(exc).__name__
            })
            error_details = {"error": str(exc), "type": type(exc).__name__, "request_id": request_id}
            message = f"Internal Server Error: {exc}"
        else:
            # Production: Log the error safely without stdout pollution, 
            # preserving traceback in structured logs via exc_info=True
            logger.error("Internal Server Error occurred", extra={"request_id": request_id}, exc_info=True)
            # strictly zero code artifacts or tracebacks in production response
            error_details = {"request_id": request_id}
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

    logger.info("SoulSense API started successfully", extra={
        "environment": settings.app_env,
        "debug": settings.debug,
        "database": settings.database_url,
        "api_v1_path": "/api/v1"
    })

    # OUTSIDE MIDDLEWARES (added last to run first)
    
    # Host Header Validation
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    logger.info(f"Loading TrustedHostMiddleware with allowed_hosts: {settings.ALLOWED_HOSTS}")
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS
    )

    return app


app = create_app()

