import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MemoryPressure:
    """Memory pressure metrics from cgroup."""
    usage_bytes: int
    limit_bytes: int
    usage_percent: float
    pressure_level: str  # "none", "low", "medium", "high", "critical"
    is_containerized: bool

class CGroupMemoryMonitor:
    """Monitor cgroup memory pressure for containerized environments."""
    
    CGROUP_V1_PATH = "/sys/fs/cgroup/memory"
    CGROUP_V2_PATH = "/sys/fs/cgroup"
    
    def __init__(self):
        self.cgroup_version = self._detect_cgroup_version()
        self.is_available = self.cgroup_version is not None
        
    def _detect_cgroup_version(self) -> Optional[int]:
        """Detect cgroup version (v1 or v2)."""
        if Path(f"{self.CGROUP_V2_PATH}/cgroup.controllers").exists():
            return 2
        elif Path(f"{self.CGROUP_V1_PATH}/memory.limit_in_bytes").exists():
            return 1
        return None
    
    def get_memory_pressure(self) -> MemoryPressure:
        """Get current memory pressure metrics."""
        if not self.is_available:
            return self._get_fallback_metrics()
        
        if self.cgroup_version == 2:
            return self._read_cgroup_v2()
        return self._read_cgroup_v1()
    
    def _read_cgroup_v1(self) -> MemoryPressure:
        """Read memory metrics from cgroup v1."""
        try:
            usage = int(Path(f"{self.CGROUP_V1_PATH}/memory.usage_in_bytes").read_text().strip())
            limit = int(Path(f"{self.CGROUP_V1_PATH}/memory.limit_in_bytes").read_text().strip())
            
            # Handle unlimited cgroup (very large number)
            if limit > 9223372036854771712:  # 8 EiB
                limit = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            
            percent = (usage / limit) * 100
            return MemoryPressure(
                usage_bytes=usage,
                limit_bytes=limit,
                usage_percent=percent,
                pressure_level=self._calculate_pressure_level(percent),
                is_containerized=True
            )
        except Exception as e:
            logger.warning(f"Failed to read cgroup v1 metrics: {e}")
            return self._get_fallback_metrics()
    
    def _read_cgroup_v2(self) -> MemoryPressure:
        """Read memory metrics from cgroup v2."""
        try:
            mem_current = int(Path(f"{self.CGROUP_V2_PATH}/memory.current").read_text().strip())
            mem_max = Path(f"{self.CGROUP_V2_PATH}/memory.max").read_text().strip()
            
            if mem_max == "max":
                mem_max = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            else:
                mem_max = int(mem_max)
            
            percent = (mem_current / mem_max) * 100
            return MemoryPressure(
                usage_bytes=mem_current,
                limit_bytes=mem_max,
                usage_percent=percent,
                pressure_level=self._calculate_pressure_level(percent),
                is_containerized=True
            )
        except Exception as e:
            logger.warning(f"Failed to read cgroup v2 metrics: {e}")
            return self._get_fallback_metrics()
    
    def _get_fallback_metrics(self) -> MemoryPressure:
        """Fallback to psutil for non-containerized environments."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return MemoryPressure(
                usage_bytes=mem.used,
                limit_bytes=mem.total,
                usage_percent=mem.percent,
                pressure_level=self._calculate_pressure_level(mem.percent),
                is_containerized=False
            )
        except ImportError:
            logger.error("psutil not available for memory monitoring")
            return MemoryPressure(0, 0, 0.0, "unknown", False)
    
    @staticmethod
    def _calculate_pressure_level(percent: float) -> str:
        """Calculate pressure level from usage percentage."""
        if percent < 60:
            return "none"
        elif percent < 75:
            return "low"
        elif percent < 85:
            return "medium"
        elif percent < 95:
            return "high"
        return "critical"
    
    def should_throttle(self) -> bool:
        """Check if application should throttle operations."""
        pressure = self.get_memory_pressure()
        return pressure.pressure_level in ("high", "critical")
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for logging/monitoring."""
        pressure = self.get_memory_pressure()
        return {
            "usage_mb": pressure.usage_bytes / (1024 * 1024),
            "limit_mb": pressure.limit_bytes / (1024 * 1024),
            "usage_percent": round(pressure.usage_percent, 2),
            "pressure_level": pressure.pressure_level,
            "is_containerized": pressure.is_containerized,
            "cgroup_version": self.cgroup_version
        }

# Global singleton
_monitor = None

def get_memory_monitor() -> CGroupMemoryMonitor:
    """Get global memory monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = CGroupMemoryMonitor()
    return _monitor
