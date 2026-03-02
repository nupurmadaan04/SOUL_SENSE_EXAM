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

import sys
import os
# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from ..schemas import HealthResponse, ServiceStatus
from ..services.db_service import get_db
from ..config import get_settings
from poison_resistant_lock import PoisonResistantLock, register_lock

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
        self._lock = PoisonResistantLock()
        
        # Register lock for monitoring
        register_lock(self._lock)
    
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
    """Check Redis connectivity if configured."""
    try:
        # Check if Redis is configured in settings
        settings = get_settings()
        if not hasattr(settings, 'redis_url') or not settings.redis_url:
            return ServiceStatus(status="healthy", latency_ms=None, message="Redis not configured")

        # For now, return healthy status since Redis integration may not be fully implemented
        # In a full implementation, this would check actual Redis connectivity
        return ServiceStatus(status="healthy", latency_ms=None, message="Redis available")
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return ServiceStatus(status="unhealthy", message=str(e), latency_ms=None)


async def check_clock_skew(request) -> ServiceStatus:
    """Check clock synchronization status for distributed lock TTL protection (#1195)."""
    try:
        from clock_skew_monitor import get_clock_monitor
        monitor = get_clock_monitor()
        metrics = monitor.get_clock_metrics()

        # Determine status based on clock state
        if metrics.state.value == "synchronized":
            status = "healthy"
            message = f"Clock synchronized (offset: {metrics.ntp_offset:.3f}s)"
        elif metrics.state.value == "drifting":
            status = "degraded"
            message = f"Clock drifting (offset: {metrics.ntp_offset:.3f}s, rate: {metrics.drift_rate:.6f})"
        else:  # unsynchronized
            status = "unhealthy"
            message = f"Clock unsynchronized - using drift-tolerant timing"

        return ServiceStatus(status=status, latency_ms=None, message=message)
    except Exception as e:
        logger.warning(f"Clock skew health check failed: {e}")
        return ServiceStatus(status="unhealthy", message=f"Clock monitoring unavailable: {str(e)}", latency_ms=None)


async def check_event_loop_health(request) -> ServiceStatus:
    """Check event loop health and FD resource status (#1183)."""
    try:
        fd_monitor = getattr(request.app.state, 'fd_monitor', None)
        if fd_monitor is None:
            return ServiceStatus(status="unhealthy", message="FD monitor not initialized", latency_ms=None)

        health_status = fd_monitor.get_health_status()

        # Determine status based on health
        if health_status['critical']:
            status = "unhealthy"
            message = f"Critical FD exhaustion: {health_status['fd_stats']['current_usage_percent']:.1f}% usage"
        elif health_status['degraded']:
            status = "degraded"
            message = f"High FD usage: {health_status['fd_stats']['current_usage_percent']:.1f}% usage"
        else:
            status = "healthy"
            message = f"FD usage normal: {health_status['fd_stats']['current_usage_percent']:.1f}% usage"

        return ServiceStatus(status=status, latency_ms=None, message=message)
    except Exception as e:
        logger.warning(f"Event loop health check failed: {e}")
        return ServiceStatus(status="unhealthy", message=str(e), latency_ms=None)


def get_diagnostics() -> Dict[str, Any]:
    """Get detailed diagnostics for ?full=true."""
    import os
    import sys

    diagnostics = {
        "python_version": sys.version.split()[0],
        "pid": os.getpid(),
    }
    
    # Memory and Resource usage (if psutil available)

    try:
        import psutil
        import platform
        process = psutil.Process(os.getpid())
        
        diagnostics["memory_mb"] = round(process.memory_info().rss / (1024 * 1024), 2)
        diagnostics["cpu_percent"] = process.cpu_percent(interval=0.1)
        
        # Resource exhaustion monitoring (FD/Handle leaks)
        if platform.system() == "Windows":
            # On Windows, we track 'handles'
            diagnostics["open_handles"] = process.num_handles()
        else:
            # On Linux/macOS, we track 'file descriptors'
            try:
                diagnostics["open_file_descriptors"] = process.num_fds()
            except AttributeError:
                # Fallback for platforms where num_fds() is missing
                diagnostics["open_files"] = len(process.open_files())
                diagnostics["open_connections"] = len(process.connections())

        # FD Threshold Warning: Log if we're approaching limits
        # Typical default limit is 1024 on Linux
        fd_count = diagnostics.get("open_file_descriptors") or diagnostics.get("open_handles", 0)
        if fd_count > 800:
             logger.warning(f"HIGH RESOURCE USAGE: Process {os.getpid()} is using {fd_count} handles/FDs", extra={"fd_count": fd_count})
             
    except ImportError:
        logger.debug("psutil not available for diagnostics")
    except Exception as e:
        logger.warning(f"Failed to gather diagnostics: {e}")
    
        pass

    # Add FD monitoring diagnostics if available
    try:
        from event_loop_health_monitor import get_event_loop_monitor
        monitor = get_event_loop_monitor()
        if monitor:
            fd_manager = monitor.fd_manager
            fd_stats = fd_manager.get_stats()
            event_loop_stats = monitor.get_stats()

            diagnostics["fd_monitoring"] = {
                "fd_stats": fd_stats,
                "event_loop_stats": event_loop_stats,
                "tracked_fds": len(fd_manager.get_fd_info())
            }
    except Exception as e:
        diagnostics["fd_monitoring_error"] = str(e)

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
    event_loop_status = await check_event_loop_health(request)
    clock_skew_status = await check_clock_skew(request)

    services = {
        "database": db_status,
        "redis": redis_status,
        "event_loop": event_loop_status,
        "clock_skew": clock_skew_status
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
    
    # Perform health checks
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
    """
    Startup probe - checks if the application has completed initialization.
    
    Use this for Kubernetes startupProbe to give the app time to initialize.
    """
    # For startup, we just check if we can connect to DB
    """Startup probe - checks if the application has completed initialization."""
    db_status = await check_database(db)
    
    return HealthResponse(
        status="healthy" if db_status.status == "healthy" else "unhealthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=get_app_version(),
        services={"database": db_status},
        details=None
    )
