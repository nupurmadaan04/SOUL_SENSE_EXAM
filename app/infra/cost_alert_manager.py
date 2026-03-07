"""
Cost Anomaly Alert Manager

Manages the lifecycle of cost anomaly alerts (create, retrieve, clear).
Follows the same pattern as latency_alerts.AlertManager
"""

from typing import List, Optional
from datetime import datetime
import logging

from app.infra.cost_anomaly_detector import CostAnomalyAlert, AlertLevel

logger = logging.getLogger(__name__)


class CostAnomalyAlertManager:
    """Manages cost anomaly alerts (Singleton pattern)."""
    
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
        self.alerts: List[CostAnomalyAlert] = []
    
    def add_alert(self, alert: CostAnomalyAlert) -> None:
        """Add an alert to the manager.
        
        Args:
            alert: CostAnomalyAlert to track
        """
        self.alerts.append(alert)
        logger.log(
            level=logging.WARNING if alert.alert_level == AlertLevel.WARNING else logging.CRITICAL,
            msg=str(alert)
        )
    
    def add_alerts(self, alerts: List[CostAnomalyAlert]) -> None:
        """Add multiple alerts at once.
        
        Args:
            alerts: List of CostAnomalyAlert objects
        """
        for alert in alerts:
            self.add_alert(alert)
    
    def get_alerts(self, service_name: Optional[str] = None,
                   alert_level: Optional[AlertLevel] = None) -> List[CostAnomalyAlert]:
        """Get alerts with optional filtering.
        
        Args:
            service_name: Filter by service (optional)
            alert_level: Filter by severity level (optional)
            
        Returns:
            List of matching alerts
        """
        filtered = self.alerts
        
        if service_name is not None:
            filtered = [a for a in filtered if a.service_name == service_name]
        
        if alert_level is not None:
            filtered = [a for a in filtered if a.alert_level == alert_level]
        
        return filtered
    
    def clear_alerts_before(self, timestamp: datetime) -> int:
        """Remove alerts older than specified timestamp.
        
        Args:
            timestamp: Cutoff datetime
            
        Returns:
            Number of alerts cleared
        """
        original_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.timestamp >= timestamp]
        cleared = original_count - len(self.alerts)
        
        if cleared > 0:
            logger.info(f"Cleared {cleared} old alerts")
        
        return cleared
    
    def clear(self) -> None:
        """Clear all alerts (useful for testing)."""
        self.alerts.clear()
    
    def get_summary(self) -> dict:
        """Get summary statistics of current alerts.
        
        Returns:
            Dict with total count, counts by level, and services with alerts
        """
        summary = {
            "total": len(self.alerts),
            "critical": len([a for a in self.alerts if a.alert_level == AlertLevel.CRITICAL]),
            "warning": len([a for a in self.alerts if a.alert_level == AlertLevel.WARNING]),
            "info": len([a for a in self.alerts if a.alert_level == AlertLevel.INFO]),
            "services": list(set(a.service_name for a in self.alerts))
        }
        return summary


__all__ = ["CostAnomalyAlertManager"]
