from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from ..utils.cgroup_memory_monitor import get_memory_monitor

logger = logging.getLogger(__name__)

class MemoryPressureMiddleware(BaseHTTPMiddleware):
    """Throttle requests under high memory pressure."""
    
    async def dispatch(self, request: Request, call_next):
        monitor = get_memory_monitor()
        
        if monitor.should_throttle():
            pressure = monitor.get_memory_pressure()
            logger.warning(
                f"Memory pressure detected: {pressure.pressure_level} "
                f"({pressure.usage_percent:.1f}% used)",
                extra=monitor.get_metrics_dict()
            )
            
            # Return 503 for critical pressure
            if pressure.pressure_level == "critical":
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "service_unavailable",
                        "message": "Server under high memory pressure",
                        "retry_after": 30
                    },
                    headers={"Retry-After": "30"}
                )
        
        return await call_next(request)
