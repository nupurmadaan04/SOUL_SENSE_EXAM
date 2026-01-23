"""Performance monitoring utility"""
import time
import psutil
import threading
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def measure_time(self, func_name: str = None):
        """Decorator to measure function execution time"""
        def decorator(func):
            name = func_name or func.__name__
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    self._record_metric(name, duration)
            return wrapper
        return decorator
    
    def _record_metric(self, name: str, value: float):
        """Record performance metric"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(value)
        
        # Keep only last 100 measurements
        if len(self.metrics[name]) > 100:
            self.metrics[name] = self.metrics[name][-100:]
    
    def get_memory_usage(self):
        """Get current memory usage"""
        process = psutil.Process()
        return {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent()
        }
    
    def get_performance_report(self):
        """Get performance report"""
        report = {
            "uptime": time.time() - self.start_time,
            "memory": self.get_memory_usage(),
            "function_times": {}
        }
        
        for func_name, times in self.metrics.items():
            if times:
                report["function_times"][func_name] = {
                    "avg": sum(times) / len(times),
                    "max": max(times),
                    "min": min(times),
                    "count": len(times)
                }
        
        return report
    
    def log_performance(self):
        """Log performance metrics"""
        report = self.get_performance_report()
        logger.info(f"Performance Report: Memory={report['memory']['memory_mb']:.1f}MB, "
                   f"CPU={report['memory']['cpu_percent']:.1f}%, "
                   f"Uptime={report['uptime']:.1f}s")

# Global performance monitor
perf_monitor = PerformanceMonitor()

def monitor_performance(func_name: str = None):
    """Performance monitoring decorator"""
    return perf_monitor.measure_time(func_name)

def log_performance():
    """Log current performance"""
    perf_monitor.log_performance()