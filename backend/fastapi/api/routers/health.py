"""
Health and Readiness endpoints for orchestration support.
Provides liveness (/health) and readiness (/ready) probes for Kubernetes, Docker, and load balancers.
"""
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import HealthResponse, ServiceStatus
from ..services.db_service import get_db
from ..config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Version Detection ---
def get_app_version() -> str:
    """Get application version from environment, pyproject.toml, or fallback."""
    import os
    
    # Priority 1: Environment variable
    env_version = os.environ.get("APP_VERSION")
    if env_version:
        return env_version
    
    # Priority 2: pyproject.toml
    try:
        import tomllib
        pyproject_path = os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml")
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", "unknown")
    except Exception:
        pass
    
    # Priority 3: Fallback
    return "1.0.0"


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


def get_diagnostics() -> Dict[str, Any]:
    """Get detailed diagnostics for ?full=true."""
    import os
    import sys
    
    # Basic diagnostics (no sensitive data)
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
    
    return diagnostics


# --- Endpoints ---
@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Liveness probe - checks if the application process is running.
    
    Returns 200 OK immediately. Use this for Kubernetes livenessProbe.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=get_app_version(),
        services=None,
        details=None
    )


@router.get("/ready", response_model=HealthResponse, tags=["Health"])
async def readiness_check(
    response: Response,
    full: bool = Query(False, description="Include detailed diagnostics"),
    db: AsyncSession = Depends(get_db)
) -> HealthResponse:
    """
    Readiness probe - checks if the application can serve traffic.
    
    Verifies database connectivity. Returns 503 if unhealthy.
    Use this for Kubernetes readinessProbe and load balancer health checks.
    """
    # Check cache first
    cached = _readiness_cache.get()
    if cached and not full:
        return HealthResponse(**cached)
    
    # Perform health checks
    db_status = await check_database(db)
    
    # Determine overall status
    services = {"database": db_status}
    is_healthy = all(s.status == "healthy" for s in services.values())
    
    result = {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": get_app_version(),
        "services": services
    }
    
    # Add diagnostics if requested
    if full:
        result["details"] = get_diagnostics()
    
    # Cache the result (without details)
    cache_data = {k: v for k, v in result.items() if k != "details"}
    _readiness_cache.set(cache_data)
    
    # Set HTTP status code
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
    db_status = await check_database(db)
    
    return HealthResponse(
        status="healthy" if db_status.status == "healthy" else "unhealthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=get_app_version(),
        services={"database": db_status},
        details=None
    )
