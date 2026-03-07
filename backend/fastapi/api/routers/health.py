"""
Health and Readiness endpoints for orchestration support.
Migrated to Async SQLAlchemy 2.0.
"""
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Response, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from ..schemas import HealthResponse, ServiceStatus
from ..services.db_service import get_db
from ..services.replica_lag_monitor import get_lag_monitor
from ..config import get_settings
from scripts.utilities.poison_resistant_lock import PoisonResistantLock, register_lock

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


async def check_replica_lag(request) -> ServiceStatus:
    """Check read-replica lag status and health."""
    try:
        settings = get_settings()
        
        # Check if replica is configured
        if not settings.replica_database_url:
            return ServiceStatus(
                status="healthy", 
                latency_ms=None, 
                message="Replica not configured"
            )
        
        # Check if lag monitoring is disabled
        if not settings.enable_replica_lag_detection:
            return ServiceStatus(
                status="healthy",
                latency_ms=None,
                message="Replica lag monitoring disabled"
            )
        
        # Get lag monitor
        lag_monitor = get_lag_monitor()
        if not lag_monitor:
            return ServiceStatus(
                status="unhealthy",
                latency_ms=None,
                message="Replica lag monitor not initialized"
            )
        
        # Get lag metrics
        metrics = await lag_monitor.get_lag_metrics()
        last_lag_ms = metrics.get('last_lag_ms')
        
        # Determine status
        if last_lag_ms is None:
            status = "unhealthy"
            message = "Unable to determine replica lag"
        elif not metrics['replica_healthy']:
            status = "degraded"
            message = f"Replica lag high: {last_lag_ms:.2f}ms (threshold: {metrics['threshold_ms']}ms)"
        else:
            status = "healthy"
            message = f"Replica lag: {last_lag_ms:.2f}ms"
        
        return ServiceStatus(
            status=status,
            latency_ms=last_lag_ms,
            message=message
        )
        
    except Exception as e:
        logger.warning(f"Replica lag health check failed: {e}")
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
    replica_lag_status = await check_replica_lag(request)

    services = {
        "database": db_status,
        "redis": redis_status,
        "event_loop": event_loop_status,
        "clock_skew": clock_skew_status,
        "fd_guardrails": fd_guardrails_status,
        "replica_lag": replica_lagms where num_fds() is missing
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
    fd_guardrails_status = await check_fd_guardrails(request)

    services = {
        "database": db_status,
        "redis": redis_status,
        "event_loop": event_loop_status,
        "clock_skew": clock_skew_status,
        "fd_guardrails": fd_guardrails_status
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
    request: Request,
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
    fd_guardrails_status = await check_fd_guardrails(request)
    
    services = {"database": db_status, "fd_guardrails": fd_guardrails_status}
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


# --- FD Guardrail Endpoints (Issue #1316) ---

async def check_fd_guardrails(request) -> ServiceStatus:
    """Check Linux FD guardrail status."""
    try:
        from ..utils.linux_fd_guardrails import get_fd_guardrails
        guardrails = get_fd_guardrails()
        status = guardrails.get_status()
        
        state = status['state']
        usage_percent = status['usage_percent']
        
        if state == 'critical':
            return ServiceStatus(
                status="unhealthy",
                message=f"Critical FD usage: {usage_percent:.1f}% ({status['current_fds']}/{status['max_fds']})",
                latency_ms=None
            )
        elif state in ('degraded', 'warning'):
            return ServiceStatus(
                status="degraded",
                message=f"Elevated FD usage: {usage_percent:.1f}% ({status['current_fds']}/{status['max_fds']})",
                latency_ms=None
            )
        else:
            return ServiceStatus(
                status="healthy",
                message=f"FD usage normal: {usage_percent:.1f}% ({status['current_fds']}/{status['max_fds']})",
                latency_ms=None
            )
    except Exception as e:
        logger.warning(f"FD guardrails check failed: {e}")
        return ServiceStatus(
            status="unhealthy",
            message=f"FD guardrails unavailable: {str(e)}",
            latency_ms=None
        )


@router.get("/fd-status", tags=["Health", "FD Guardrails"])
async def fd_guardrail_status() -> Dict[str, Any]:
    """
    Get detailed FD guardrail status.
    
    Returns current FD usage, thresholds, and request handling statistics.
    """
    try:
        from ..utils.linux_fd_guardrails import get_fd_guardrails
        guardrails = get_fd_guardrails()
        return guardrails.get_status()
    except Exception as e:
        logger.error(f"Error getting FD guardrail status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve FD guardrail status: {str(e)}"
        )


@router.get("/fd-metrics", tags=["Health", "FD Guardrails"])
async def fd_guardrail_metrics(
    count: int = Query(100, ge=1, le=1000, description="Number of metrics samples to return")
) -> Dict[str, Any]:
    """
    Get FD guardrail metrics history.
    
    Returns historical metrics for trend analysis and monitoring.
    """
    try:
        from ..utils.linux_fd_guardrails import get_fd_guardrails
        guardrails = get_fd_guardrails()
        
        metrics = guardrails.get_metrics(count)
        trend = guardrails.get_fd_usage_trend()
        
        return {
            "metrics": [
                {
                    "timestamp": m.timestamp,
                    "current_fds": m.current_fds,
                    "max_fds": m.max_fds,
                    "usage_percent": m.usage_percent,
                    "state": m.state.value,
                    "requests_accepted": m.requests_accepted,
                    "requests_rejected": m.requests_rejected,
                    "cleanups_performed": m.cleanups_performed,
                    "fds_reclaimed": m.fds_reclaimed
                }
                for m in metrics
            ],
            "trend_fds_per_minute": trend,
            "current_status": guardrails.get_status()
        }
    except Exception as e:
        logger.error(f"Error getting FD guardrail metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve FD guardrail metrics: {str(e)}"
        )


@router.post("/fd-cleanup", tags=["Health", "FD Guardrails"])
async def trigger_fd_cleanup(
    request: Request,
    force: bool = Query(False, description="Force cleanup even if not in critical state")
) -> Dict[str, Any]:
    """
    Trigger manual FD cleanup.
    
    Requires admin privileges. Attempts to reclaim leaked file descriptors.
    """
    # Check for admin authorization
    # This is a simple check - in production, use proper RBAC
    api_key = request.headers.get("X-Admin-Key")
    settings = get_settings()
    admin_key = getattr(settings, 'admin_api_key', None)
    
    if admin_key and api_key != admin_key:
        raise HTTPException(
            status_code=403,
            detail="Admin authorization required"
        )
    
    try:
        from ..utils.linux_fd_guardrails import get_fd_guardrails
        guardrails = get_fd_guardrails()
        
        status = guardrails.get_status()
        
        # Only allow cleanup if in elevated state or force flag is set
        if not force and status['state'] not in ('warning', 'degraded', 'critical'):
            return {
                "success": False,
                "message": "Cleanup not needed - FD usage is normal. Use force=true to override.",
                "status": status
            }
        
        reclaimed = guardrails.force_cleanup()
        
        # Get updated status
        new_status = guardrails.get_status()
        
        return {
            "success": True,
            "fds_reclaimed": reclaimed,
            "previous_status": status,
            "current_status": new_status
        }
    except Exception as e:
        logger.error(f"Error during FD cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )


# --- Replica Lag Monitoring Endpoints (Read-Replica Lag Aware Routing) ---

@router.get("/replica-lag", tags=["Health", "Database"])
async def replica_lag_status() -> Dict[str, Any]:
    """
    Get current replica lag metrics.
    
    Returns lag measurements, health status, and configuration.
    Useful for monitoring database replication health.
    """
    try:
        settings = get_settings()
        
        # Check if replica is configured
        if not settings.replica_database_url:
            return {
                "enabled": False,
                "message": "Read replica not configured",
                "primary_only": True
            }
        
        # Check if lag monitoring is disabled
        if not settings.enable_replica_lag_detection:
            return {
                "enabled": False,
                "message": "Replica lag monitoring disabled",
                "replica_configured": True,
                "reads_routed_to_replica": True
            }
        
        # Get lag monitor
        lag_monitor = get_lag_monitor()
        if not lag_monitor:
            raise HTTPException(
                status_code=503,
                detail="Replica lag monitor not initialized"
            )
        
        # Get lag metrics
        metrics = await lag_monitor.get_lag_metrics()
        
        return {
            "enabled": True,
            "replica_configured": True,
            "metrics": metrics,
            "configuration": {
                "threshold_ms": settings.replica_lag_threshold_ms,
                "check_interval_seconds": settings.replica_lag_check_interval_seconds,
                "cache_ttl_seconds": settings.replica_lag_cache_ttl_seconds,
                "timeout_seconds": settings.replica_lag_timeout_seconds,
                "fallback_on_error": settings.replica_lag_fallback_on_error
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting replica lag status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve replica lag status: {str(e)}"
        )


@router.post("/replica-lag/check", tags=["Health", "Database"])
async def trigger_replica_lag_check() -> Dict[str, Any]:
    """
    Trigger manual replica lag check.
    
    Forces an immediate lag measurement, bypassing cache.
    Useful for testing and troubleshooting.
    """
    try:
        settings = get_settings()
        
        if not settings.replica_database_url:
            raise HTTPException(
                status_code=400,
                detail="Read replica not configured"
            )
        
        if not settings.enable_replica_lag_detection:
            raise HTTPException(
                status_code=400,
                detail="Replica lag monitoring is disabled"
            )
        
        lag_monitor = get_lag_monitor()
        if not lag_monitor:
            raise HTTPException(
                status_code=503,
                detail="Replica lag monitor not initialized"
            )
        
        # Force a lag check
        lag_ms = await lag_monitor.check_lag()
        
        if lag_ms is None:
            return {
                "success": False,
                "message": "Unable to determine replica lag",
                "metrics": await lag_monitor.get_lag_metrics()
            }
        
        return {
            "success": True,
            "lag_ms": lag_ms,
            "replica_healthy": lag_monitor.is_replica_healthy(),
            "threshold_ms": settings.replica_lag_threshold_ms,
            "within_threshold": lag_ms <= settings.replica_lag_threshold_ms,
            "metrics": await lag_monitor.get_lag_metrics()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking replica lag: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Replica lag check failed: {str(e)}"
        )

