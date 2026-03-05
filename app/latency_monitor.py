"""
Latency Monitoring and Statistics System

Tracks execution times, calculates statistics, and detects budget breaches.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetric:
    """Single latency measurement."""
    operation_name: str
    execution_time_ms: float
    budget_ms: float
    operation_type: str
    alert_threshold_percent: float
    breached: bool = field(init=False)
    alert_triggered: bool = field(init=False)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Calculate breach and alert status on initialization."""
        self.breached = self.execution_time_ms > self.budget_ms
        alert_threshold_ms = (self.budget_ms * self.alert_threshold_percent) / 100
        self.alert_triggered = self.execution_time_ms >= alert_threshold_ms


class LatencyMonitor:
    """Monitors and tracks operation latencies."""
    
    _instance: Optional['LatencyMonitor'] = None
    
    def __new__(cls) -> 'LatencyMonitor':
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the monitor."""
        if self._initialized:
            return
        
        self._initialized = True
        self.metrics: List[LatencyMetric] = []
        self.operation_metrics: Dict[str, List[LatencyMetric]] = defaultdict(list)
    
    def record_latency(
        self,
        operation_name: str,
        execution_time_ms: float,
        budget_ms: float,
        operation_type: str,
        alert_threshold_percent: float
    ) -> LatencyMetric:
        """Record a latency measurement."""
        metric = LatencyMetric(
            operation_name=operation_name,
            execution_time_ms=execution_time_ms,
            budget_ms=budget_ms,
            operation_type=operation_type,
            alert_threshold_percent=alert_threshold_percent
        )
        
        self.metrics.append(metric)
        self.operation_metrics[operation_name].append(metric)
        
        # Log if breach or alert triggered
        if metric.alert_triggered:
            logger.warning(
                f"Latency alert for '{operation_name}': "
                f"{execution_time_ms:.1f}ms (budget: {budget_ms}ms)"
            )
        
        if metric.breached:
            logger.error(
                f"Latency breach for '{operation_name}': "
                f"{execution_time_ms:.1f}ms exceeds budget of {budget_ms}ms"
            )
        
        return metric
    
    def get_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        ops = self.operation_metrics.get(operation_name, [])
        
        if not ops:
            return {
                "operation_name": operation_name,
                "count": 0,
                "data": None
            }
        
        times = [m.execution_time_ms for m in ops]
        breaches = sum(1 for m in ops if m.breached)
        alerts = sum(1 for m in ops if m.alert_triggered)
        
        return {
            "operation_name": operation_name,
            "count": len(ops),
            "min_ms": min(times),
            "max_ms": max(times),
            "avg_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "budget_ms": ops[0].budget_ms,
            "breaches": breaches,
            "breach_rate": (breaches / len(ops)) * 100,
            "alerts_triggered": alerts,
            "alert_rate": (alerts / len(ops)) * 100
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all operations."""
        return {
            op_name: self.get_stats(op_name)
            for op_name in self.operation_metrics.keys()
        }
    
    def get_breached_operations(self) -> List[LatencyMetric]:
        """Get all operations that exceeded their budgets."""
        return [m for m in self.metrics if m.breached]
    
    def get_alerted_operations(self) -> List[LatencyMetric]:
        """Get all operations that triggered alerts."""
        return [m for m in self.metrics if m.alert_triggered]
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics (useful for testing)."""
        self.metrics.clear()
        self.operation_metrics.clear()
