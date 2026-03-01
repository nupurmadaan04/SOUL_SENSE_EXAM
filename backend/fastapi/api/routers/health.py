"""
Health and Readiness endpoints for orchestration support.
Migrated to Async SQLAlchemy 2.0.
"""
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import HealthResponse, ServiceStatus
from ..services.db_service import get_db
from ..config import get_settings

router = APIRouter()
logger = logging.getLogger("api.health")


# --- Version Detection ---
def get_app_version() -> str:
    """Get application version from environment or fallback."""
    import os
    return os.environ.get("APP_VERSION", "1.0.0")


# --- Caching Layer ---
class HealthCache:
    """Thread-safe cache for readiness check results."""
    
    def __init__(self, ttl_seconds: float = 5.0):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._timestamp: float = 0
        self._lock = threading.Lock()
    
    def get(self) -> Optional[Dict[str, Any]]:
        """Get cached result if still valid."""
        with self._lock:
            if time.time() - self._timestamp < self.ttl:
                return self._cache.copy()
        return None
    
    def set(self, data: Dict[str, Any]) -> None:
        """Update cache with new data."""
        with self._lock:
            self._cache = data.copy()
            self._timestamp = time.time()


_readiness_cache = HealthCache(ttl_seconds=5.0)


# --- Health Check Helpers ---
async def check_database(db: AsyncSession) -> ServiceStatus:
    """Check database connectivity and measure latency."""
    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000  # ms
        return ServiceStatus(status="healthy", latency_ms=round(latency, 2), message=None)
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return ServiceStatus(status="unhealthy", message=str(e), latency_ms=None)


async def check_redis(request) -> ServiceStatus:
    """Check Redis connectivity and measure latency."""
    start = time.perf_counter()
    try:
        redis_client = getattr(request.app.state, 'redis_client', None)
        if redis_client is None:
            return ServiceStatus(status="unhealthy", message="Redis client not initialized", latency_ms=None)
        
        await redis_client.ping()
        latency = (time.perf_counter() - start) * 1000  # ms
        return ServiceStatus(status="healthy", latency_ms=round(latency, 2), message=None)
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return ServiceStatus(status="unhealthy", message=str(e), latency_ms=None)


def get_diagnostics() -> Dict[str, Any]:
    """Get detailed diagnostics for ?full=true."""
    import os
    import sys
    
    diagnostics = {
        "python_version": sys.version.split()[0],
        "pid": os.getpid(),
    }
    
    try:
        import psutil
        process = psutil.Process(os.getpid())
        diagnostics["memory_mb"] = round(process.memory_info().rss / (1024 * 1024), 2)
        diagnostics["cpu_percent"] = process.cpu_percent(interval=0.1)
    except ImportError:
        pass
    
    return diagnostics


# --- Endpoints ---
@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> HealthResponse:
    """System health check - verifies critical dependencies are operational."""
    db_status = await check_database(db)
    redis_status = await check_redis(request)
    
    services = {
        "database": db_status,
        "redis": redis_status
    }
    
    # Determine overall health - all critical services must be healthy
    is_healthy = all(s.status == "healthy" for s in services.values())
    
    if not is_healthy:
        response.status_code = 503  # Service Unavailable
        logger.warning(f"Health check failed: {services}")
    
    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=get_app_version(),
        services=services,
        details=None
    )


@router.get("/ready", response_model=HealthResponse, tags=["Health"])
async def readiness_check(
    response: Response,
    full: bool = Query(False, description="Include detailed diagnostics"),
    db: AsyncSession = Depends(get_db)
) -> HealthResponse:
    """Readiness probe - checks if the application can serve traffic."""
    cached = _readiness_cache.get()
    if cached and not full:
        return HealthResponse(**cached)
    
    db_status = await check_database(db)
    
    services = {"database": db_status}
    is_healthy = all(s.status == "healthy" for s in services.values())
    
    result = {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": get_app_version(),
        "services": services
    }
    
    if full:
        result["details"] = get_diagnostics()
    
    cache_data = {k: v for k, v in result.items() if k != "details"}
    _readiness_cache.set(cache_data)
    
    if not is_healthy:
        response.status_code = 503
        logger.warning(f"Readiness check failed: {services}")
    
    return HealthResponse(**result)


@router.get("/startup", response_model=HealthResponse, tags=["Health"])
async def startup_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Startup probe - checks if the application has completed initialization."""
    db_status = await check_database(db)
    
    return HealthResponse(
        status="healthy" if db_status.status == "healthy" else "unhealthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=get_app_version(),
        services={"database": db_status},
        details=None
    )
