"""
Latency Alert System

Generates and manages alerts for latency budget breaches.
"""

from enum import Enum
from typing import List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class LatencyAlert:
    """Represents a latency budget alert."""
    operation_name: str
    actual_time_ms: float
    budget_ms: float
    alert_level: AlertLevel
    message: str
    timestamp: datetime
    
    def __str__(self) -> str:
        return (
            f"[{self.alert_level.value}] {self.operation_name}: "
            f"{self.actual_time_ms:.1f}ms (budget: {self.budget_ms}ms) - "
            f"{self.message}"
        )


class AlertManager:
    """Manages latency alerts."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize alert manager."""
        if self._initialized:
            return
        
        self._initialized = True
        self.alerts: List[LatencyAlert] = []
    
    def create_alert(
        self,
        operation_name: str,
        actual_time_ms: float,
        budget_ms: float,
        alert_threshold_percent: float
    ) -> LatencyAlert:
        """Create and record an alert."""
        # Determine alert level
        if actual_time_ms > budget_ms:
            excess_percent = ((actual_time_ms - budget_ms) / budget_ms) * 100
            if excess_percent > 50:
                alert_level = AlertLevel.CRITICAL
                message = f"CRITICAL: {excess_percent:.1f}% over budget"
            else:
                alert_level = AlertLevel.WARNING
                message = f"WARNING: {excess_percent:.1f}% over budget"
        else:
            alert_level = AlertLevel.WARNING
            message = f"Approaching budget ({alert_threshold_percent}% threshold)"
        
        alert = LatencyAlert(
            operation_name=operation_name,
            actual_time_ms=actual_time_ms,
            budget_ms=budget_ms,
            alert_level=alert_level,
            message=message,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        logger.log(
            logging.CRITICAL if alert_level == AlertLevel.CRITICAL else logging.WARNING,
            str(alert)
        )
        
        return alert
    
    def get_recent_alerts(self, limit: int = 10) -> List[LatencyAlert]:
        """Get recent alerts."""
        return self.alerts[-limit:]
    
    def get_alerts_by_operation(self, operation_name: str) -> List[LatencyAlert]:
        """Get alerts for a specific operation."""
        return [a for a in self.alerts if a.operation_name == operation_name]
    
    def get_critical_alerts(self) -> List[LatencyAlert]:
        """Get all critical alerts."""
        return [a for a in self.alerts if a.alert_level == AlertLevel.CRITICAL]
    
    def clear_alerts(self) -> None:
        """Clear all alerts (useful for testing)."""
        self.alerts.clear()
