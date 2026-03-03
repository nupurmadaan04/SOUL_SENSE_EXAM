from fastapi import APIRouter, Depends
from typing import Dict, Any
from ..utils.cgroup_memory_monitor import get_memory_monitor

router = APIRouter()

@router.get("/memory")
async def memory_health() -> Dict[str, Any]:
    """Get memory pressure metrics for monitoring."""
    monitor = get_memory_monitor()
    metrics = monitor.get_metrics_dict()
    pressure = monitor.get_memory_pressure()
    
    return {
        "status": "healthy" if pressure.pressure_level in ("none", "low") else "degraded",
        "metrics": metrics,
        "should_throttle": monitor.should_throttle()
    }
