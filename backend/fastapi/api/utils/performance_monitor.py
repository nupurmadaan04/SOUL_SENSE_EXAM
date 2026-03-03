"""
Performance monitoring and optimization utilities.

Tracks:
- API response times
- Database query performance
- Cache hit rates
- Memory usage
"""

import time
import logging
from functools import wraps
from typing import Callable, Dict, List
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_timing(self, operation: str, duration: float):
        """Record operation timing."""
        self.metrics[operation].append(duration)
        
        if duration > 1.0:  # Log slow operations
            logger.warning(f"Slow operation: {operation} took {duration:.2f}s")
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses += 1
    
    def get_stats(self) -> dict:
        """Get performance statistics."""
        stats = {}
        
        for operation, timings in self.metrics.items():
            if timings:
                stats[operation] = {
                    'count': len(timings),
                    'avg': sum(timings) / len(timings),
                    'min': min(timings),
                    'max': max(timings),
                    'p95': sorted(timings)[int(len(timings) * 0.95)] if len(timings) > 1 else timings[0],
                }
        
        total_cache = self.cache_hits + self.cache_misses
        stats['cache'] = {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': self.cache_hits / total_cache if total_cache > 0 else 0,
        }
        
        return stats
    
    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.cache_hits = 0
        self.cache_misses = 0


# Global monitor instance
monitor = PerformanceMonitor()


def track_performance(operation_name: str):
    """Decorator to track function performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                monitor.record_timing(operation_name, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                monitor.record_timing(operation_name, duration)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def get_performance_report() -> dict:
    """Get comprehensive performance report."""
    return monitor.get_stats()
