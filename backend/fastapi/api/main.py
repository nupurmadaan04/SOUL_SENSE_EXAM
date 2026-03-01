from fastapi import FastAPI, Request
import asyncio
import logging
import uuid
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
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
from .services.websocket_manager import manager as ws_manager

# Initialize centralized logging
setup_logging()
logger = logging.getLogger("api.main")

# Load and validate settings on import
settings = get_settings_instance()
STATIC_DIR = Path(__file__).resolve().parent / "static"
FAVICON_PATH = STATIC_DIR / "favicon.svg"

# Initialize FastAPI Cache early (before router imports)
try:
    import redis.asyncio as redis
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.redis import RedisBackend
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    print("[OK] FastAPI Cache initialized with Redis backend")
except Exception as e:
    print(f"[WARNING] FastAPI Cache initialization failed: {e}")
    # Initialize with in-memory backend as fallback
    try:
        from fastapi_cache import FastAPICache
        from fastapi_cache.backends.memory import MemoryBackend
        FastAPICache.init(MemoryBackend(), prefix="fastapi-cache")
        print("[OK] FastAPI Cache initialized with in-memory backend")
    except Exception as e2:
        print(f"[ERROR] FastAPI Cache fallback initialization failed: {e2}")


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
        from .models import Base
        from .services.db_service import engine, AsyncSessionLocal
        # Note: In a production app, we would use migrations, but for this exercise we can auto-create
        # Base.metadata.create_all(bind=engine) # Synchronous metadata create requires synchronous engine
        print("[OK] Initializing/verifying database")
        
        # Verify database connectivity before starting background tasks
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            print("[OK] Database connectivity verified")
        
        # Initialize Redis for rate limiting
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test Redis connectivity
            await redis_client.ping()
            app.state.redis_client = redis_client
            
            # Configure slowapi limiter with Redis storage
            limiter._storage_uri = settings.redis_url
            print(f"[OK] Redis connected for rate limiting: {settings.redis_host}:{settings.redis_port}")
            
            # Initialize JWT blacklist
            from .utils.jwt_blacklist import init_jwt_blacklist
            init_jwt_blacklist(redis_client)
            print("[OK] JWT blacklist initialized")
            
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
            print(f"[WARNING] Redis not available, rate limiting will use in-memory fallback: {e}")
            # SlowAPI will automatically fall back to in-memory storage if Redis is unavailable
            
        # Initialize analytics scheduler
        try:
            from app.ml.scheduler_service import get_scheduler
            scheduler = get_scheduler()
            scheduler.start()
            app.state.analytics_scheduler = scheduler
            print("[OK] Analytics scheduler initialized and started")
        except Exception as e:
            logger.warning(f"Analytics scheduler initialization failed: {e}")
            print(f"[WARNING] Analytics scheduler not available: {e}")
            
        # Initialize WebSocket Manager
        app.state.ws_manager = ws_manager
        try:
            await ws_manager.connect_redis()
            print("[OK] WebSocket Manager initialized with Redis Pub/Sub")
        except Exception as e:
            logger.warning(f"[WARNING] WebSocket Manager failing Redis connection: {e}. Falling back to local.")
            print(f"[WARNING] WebSocket Manager Redis connect failed: {e}")

        
        # Start background task for soft-delete cleanup
        async def purge_task_loop():
            while True:
                try:
                    print("[CLEANUP] Starting scheduled purge of expired accounts...")
                    from .services.db_service import AsyncSessionLocal
                    async with AsyncSessionLocal() as db:
                        from .services.user_service import UserService
                        user_service = UserService(db)
                        await user_service.purge_deleted_users(settings.deletion_grace_period_days)
                    print("[CLEANUP] Scheduled purge completed successfully")
                except Exception as e:
                    logger = logging.getLogger("api.purge_task")
                    logger.error(f"Soft-delete cleanup task failed: {e}", exc_info=True)
                    # Continue the loop instead of crashing - the task will retry in 24 hours
                
                # Run once every 24 hours
                await asyncio.sleep(24 * 3600)
        
        purge_task = asyncio.create_task(purge_task_loop())
        app.state.purge_task = purge_task  # Store reference for cleanup
        print("[OK] Soft-delete cleanup task scheduled (runs every 24h)")

        # Kafka producer and Audit Consumer initialization (#1085)
        try:
            from .services.kafka_producer import get_kafka_producer
            from .services.audit_consumer import start_audit_loop
            from .services.cqrs_worker import start_cqrs_worker
            producer = get_kafka_producer()
            await producer.start()
            start_audit_loop()
            start_cqrs_worker()
            app.state.kafka_producer = producer
            print("[OK] Kafka Producer, Audit Consumer, and CQRS Worker initialized")
            
            # ES Search initialization (#1087)
            from .services.es_sync import register_es_listeners
            from .services.es_service import get_es_service
            register_es_listeners()
            es = get_es_service()
            await es.create_index()
            print("[OK] Elasticsearch Sync Listeners and Index ready")
        except Exception as e:
            logger.warning(f"Kafka/Audit initialization failed: {e}")
            print(f"[WARNING] Event-sourced audit trail falling back to mock mode: {e}")
        
        # Initialize Cache Invalidation Listener (#1123)
        try:
            from .services.cache_service import cache_service
            invalidation_task = asyncio.create_task(cache_service.start_invalidation_listener())
            app.state.invalidation_task = invalidation_task
            print("[OK] Distributed Cache Invalidation listener started via Redis Pub/Sub")
        except Exception as e:
            logger.warning(f"Failed to start cache invalidation listener: {e}")
            print(f"[WARNING] Distributed cache invalidation unavailable: {e}")
        
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
            
    if hasattr(app.state, 'invalidation_task'):
        logger.info("Cancelling distributed cache invalidation listener...")
        app.state.invalidation_task.cancel()
        try:
            await app.state.invalidation_task
        except asyncio.CancelledError:
            logger.info("Cache invalidation listener cancelled successfully")
    
    # Stop analytics scheduler
    if hasattr(app.state, 'analytics_scheduler'):
        logger.info("Stopping analytics scheduler...")
        app.state.analytics_scheduler.stop()
        logger.info("Analytics scheduler stopped successfully")
        
    # Close WebSocket Manager
    if hasattr(app.state, 'ws_manager'):
        logger.info("Shutting down WebSocket Manager...")
        await app.state.ws_manager.shutdown()
        logger.info("WebSocket Manager shutdown successfully")
    
    # Close Redis connection
    if hasattr(app.state, 'redis_client'):
        logger.info("Closing Redis connection...")
        try:
            await app.state.redis_client.close()
            logger.info("Redis connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

    # Stop Kafka Producer (#1085)
    if hasattr(app.state, 'kafka_producer'):
        logger.info("Stopping Kafka Producer...")
        await app.state.kafka_producer.stop()
        logger.info("Kafka Producer stopped successfully")
    
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
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(FAVICON_PATH, media_type="image/svg+xml")

    # Attach slowapi limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Request Logging Middleware (inner-most for full request lifecycle tracking)
    # Provides: Request IDs, JSON logging, PII protection, X-Request-ID headers
    from .middleware.logging_middleware import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)

    # GZip compression middleware for response optimization
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

    # Security Headers Middleware
    from .middleware.security import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Consent Validation Middleware for privacy compliance
    # Blocks analytics data collection without user consent
    from .middleware.consent_middleware import ConsentValidationMiddleware
    app.add_middleware(ConsentValidationMiddleware)

    # ETag Middleware for HTTP caching optimization
    # Adds ETag headers to static resources (questions, prompts, translations)
    # Returns 304 Not Modified when content hasn't changed, saving bandwidth
    from .middleware.etag_middleware import ETagMiddleware
    app.add_middleware(ETagMiddleware)

    # Server-side RBAC enforcement middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from .middleware.rbac_middleware import rbac_middleware
    from .middleware.feature_flags import feature_flag_middleware
    # from .middleware.rate_limiter_sliding import sliding_rate_limit_middleware
    from .middleware.redaction_middleware import redaction_middleware
    
    # app.add_middleware(BaseHTTPMiddleware, dispatch=sliding_rate_limit_middleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=rbac_middleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=feature_flag_middleware)

    # CORS middleware
    # In debug mode, allow all origins for easier development
    if settings.debug:
        origins = ["*"]
        allow_credentials = False  # Must be False when using wildcard origins
    else:
        origins = settings.BACKEND_CORS_ORIGINS
        allow_credentials = True
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        expose_headers=["X-API-Version", "X-Request-ID", "X-Process-Time", "ETag"],  # Expose request ID for frontend tracing
        max_age=3600,  # Cache preflight requests for 1 hour
    )
    
    # Version header middleware
    # app.add_middleware(VersionHeaderMiddleware)
    
    # Global Maintenance Mode Middleware (#1112)
    # Blocks or restricts access during critical updates
    from .middleware.maintenance import MaintenanceMiddleware
    app.add_middleware(MaintenanceMiddleware)
    
    # Mount static files for avatars
    from fastapi.staticfiles import StaticFiles
    import os
    avatars_path = os.path.join(os.getcwd(), "app_data", "avatars")
    os.makedirs(avatars_path, exist_ok=True)
    app.mount("/api/v1/avatars", StaticFiles(directory=avatars_path), name="avatars")

    # Register V1 API Router
    app.include_router(api_v1_router, prefix="/api/v1")
    
    # Register WebSocket Router
    from .routers.websockets import router as ws_router
    app.include_router(ws_router, prefix="/api/v1/stream", tags=["WebSockets"])

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
        # Register standardized exception handlers
    # import removed: register_exception_handlers not needed for current setup
    # register_exception_handlers(app)


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
