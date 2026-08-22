"""
Latency Budget Annotation System

Provides decorators to monitor command/query execution times against defined budgets.
Automatically triggers alerts when thresholds are exceeded.

GitHub Issue: #1368
"""

import time
import functools
import logging
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BudgetConfig:
    """Configuration for a latency budget."""
    operation_name: str
    budget_ms: float
    operation_type: str  # "query" or "command"
    alert_threshold_percent: float = 80.0  # Alert at 80% of budget
    enabled: bool = True


class LatencyBudget:
    """Manages latency budgets for operations."""
    
    _budgets: Dict[str, BudgetConfig] = {}
    
    @classmethod
    def register(cls, config: BudgetConfig) -> None:
        """Register a latency budget."""
        cls._budgets[config.operation_name] = config
    
    @classmethod
    def get(cls, operation_name: str) -> Optional[BudgetConfig]:
        """Get budget configuration for an operation."""
        return cls._budgets.get(operation_name)
    
    @classmethod
    def get_all(cls) -> Dict[str, BudgetConfig]:
        """Get all registered budgets."""
        return cls._budgets.copy()


def monitor_latency(
    operation_name: str,
    budget_ms: float,
    operation_type: str = "query",
    alert_threshold_percent: float = 80.0
) -> Callable:
    """
    Decorator to monitor method execution time against a latency budget.
    
    Args:
        operation_name: Unique identifier (e.g., "exam_service.get_results")
        budget_ms: Threshold in milliseconds
        operation_type: "query" for reads, "command" for writes
        alert_threshold_percent: Alert when execution reaches this % of budget
    
    Example:
        @monitor_latency("exam_service.get_results", budget_ms=500, operation_type="query")
        def get_results(self, user_id: int):
            return db.query(...)
    """
    def decorator(func: Callable) -> Callable:
        # Register the budget
        config = BudgetConfig(
            operation_name=operation_name,
            budget_ms=budget_ms,
            operation_type=operation_type,
            alert_threshold_percent=alert_threshold_percent
        )
        LatencyBudget.register(config)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                
                # Record metric
                from app.latency_monitor import LatencyMonitor
                from app.latency_alerts import AlertManager
                
                monitor = LatencyMonitor()
                metric = monitor.record_latency(
                    operation_name=operation_name,
                    execution_time_ms=elapsed_ms,
                    budget_ms=budget_ms,
                    operation_type=operation_type,
                    alert_threshold_percent=alert_threshold_percent
                )
                
                # Trigger alert if threshold exceeded
                if metric.alert_triggered:
                    alert_mgr = AlertManager()
                    alert_mgr.create_alert(
                        operation_name=operation_name,
                        actual_time_ms=elapsed_ms,
                        budget_ms=budget_ms,
                        alert_threshold_percent=alert_threshold_percent
                    )
        
        return wrapper
    return decorator
