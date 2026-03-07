"""
Cost Anomaly Detector

Detects cost anomalies based on baseline comparisons, rate of change, and absolute limits.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from app.infra.cost_trend_analyzer import CostTrendAnalyzer

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels (matching latency_alerts pattern)."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class CostAnomalyAlert:
    """Represents a cost anomaly alert."""
    service_name: str
    current_cost: float
    baseline_cost: Optional[float]
    alert_level: AlertLevel
    reason: str
    timestamp: datetime
    deviation_percent: Optional[float] = None
    
    def __str__(self) -> str:
        baseline_str = f"${self.baseline_cost:.2f}" if self.baseline_cost else "N/A"
        dev_str = f" ({self.deviation_percent:+.1f}%)" if self.deviation_percent else ""
        return (
            f"[{self.alert_level.value}] {self.service_name}: "
            f"${self.current_cost:.2f} vs baseline {baseline_str}{dev_str} - "
            f"{self.reason}"
        )


class CostAnomalyDetector:
    """Detects cost anomalies using 3-tier strategy.
    
    Tier 1: Baseline Comparison - Current cost vs 7-day average
    Tier 2: Rate of Change - Cost acceleration detection
    Tier 3: Absolute Limits - Per-service budget caps
    """
    
    def __init__(self, analyzer: Optional[CostTrendAnalyzer] = None):
        """Initialize detector.
        
        Args:
            analyzer: CostTrendAnalyzer instance (defaults to singleton)
        """
        self.analyzer = analyzer or CostTrendAnalyzer()
    
    def detect_anomaly(self, service_name: str, current_cost: float,
                      config: Dict[str, Any]) -> List[CostAnomalyAlert]:
        """Detect cost anomalies for a service.
        
        Args:
            service_name: Name of the service
            current_cost: Current cost in USD
            config: Configuration dict with thresholds (see format below)
            
        Returns:
            List of CostAnomalyAlert objects (may be empty if no anomalies)
            
        Expected config structure:
            {
                "enabled": true,
                "baseline_days": 7,
                "services": {
                    "service_name": {
                        "daily_budget_usd": 50.0,
                        "spike_threshold_percent": 20,
                        "rate_of_change_multiplier": 2.0
                    }
                }
            }
        """
        alerts: List[CostAnomalyAlert] = []
        
        # Validate config
        if not config.get("enabled", True):
            return alerts
        
        if service_name not in config.get("services", {}):
            logger.debug(f"No config for service {service_name}")
            return alerts
        
        service_config = config["services"][service_name]
        baseline_days = config.get("baseline_days", 7)
        now = datetime.utcnow()
        
        # TIER 1: Baseline Comparison
        baseline_cost = self.analyzer.get_baseline(service_name, days=baseline_days)
        if baseline_cost is not None:
            alerts.extend(self._check_baseline(
                service_name, current_cost, baseline_cost, service_config, now
            ))
        
        # TIER 2: Rate of Change
        roc = self.analyzer.get_rate_of_change(service_name, window_hours=1)
        if roc is not None:
            alerts.extend(self._check_rate_of_change(
                service_name, roc, service_config, baseline_cost, now
            ))
        
        # TIER 3: Absolute Limits
        alerts.extend(self._check_absolute_limit(
            service_name, current_cost, service_config, baseline_cost, now
        ))
        
        return alerts
    
    def _check_baseline(self, service_name: str, current_cost: float,
                       baseline_cost: float, service_config: Dict,
                       timestamp: datetime) -> List[CostAnomalyAlert]:
        """Check if current cost deviates from baseline."""
        alerts = []
        
        spike_threshold = service_config.get("spike_threshold_percent", 20)
        
        if baseline_cost == 0:
            # Edge case: can't compute percentage
            if current_cost > 0:
                alerts.append(CostAnomalyAlert(
                    service_name=service_name,
                    current_cost=current_cost,
                    baseline_cost=baseline_cost,
                    alert_level=AlertLevel.WARNING,
                    reason=f"Cost increased from ${baseline_cost:.2f} to ${current_cost:.2f}",
                    timestamp=timestamp,
                    deviation_percent=None
                ))
            return alerts
        
        deviation_percent = ((current_cost - baseline_cost) / baseline_cost) * 100
        
        if deviation_percent >= spike_threshold:
            # Determine severity based on deviation magnitude
            if deviation_percent >= 50:
                level = AlertLevel.CRITICAL
                reason = f"CRITICAL: Cost spike {deviation_percent:.1f}% above baseline"
            else:
                level = AlertLevel.WARNING
                reason = f"WARNING: Cost spike {deviation_percent:.1f}% above baseline"
            
            alerts.append(CostAnomalyAlert(
                service_name=service_name,
                current_cost=current_cost,
                baseline_cost=baseline_cost,
                alert_level=level,
                reason=reason,
                timestamp=timestamp,
                deviation_percent=deviation_percent
            ))
        
        return alerts
    
    def _check_rate_of_change(self, service_name: str, rate_of_change: float,
                             service_config: Dict, baseline_cost: Optional[float],
                             timestamp: datetime) -> List[CostAnomalyAlert]:
        """Check if cost is accelerating abnormally."""
        alerts = []
        
        multiplier = service_config.get("rate_of_change_multiplier", 2.0)
        
        # Only alert if acceleration is significant
        if abs(rate_of_change) >= (multiplier * 100):
            alerts.append(CostAnomalyAlert(
                service_name=service_name,
                current_cost=0,  # We don't have absolute cost here
                baseline_cost=baseline_cost,
                alert_level=AlertLevel.WARNING,
                reason=f"Cost acceleration detected: {rate_of_change:+.1f}% change rate",
                timestamp=timestamp,
                deviation_percent=rate_of_change
            ))
        
        return alerts
    
    def _check_absolute_limit(self, service_name: str, current_cost: float,
                             service_config: Dict, baseline_cost: Optional[float],
                             timestamp: datetime) -> List[CostAnomalyAlert]:
        """Check if cost exceeds absolute budget cap."""
        alerts = []
        
        daily_budget = service_config.get("daily_budget_usd")
        if daily_budget is None:
            return alerts
        
        if current_cost > daily_budget:
            excess = current_cost - daily_budget
            percent_over = (excess / daily_budget) * 100
            
            alerts.append(CostAnomalyAlert(
                service_name=service_name,
                current_cost=current_cost,
                baseline_cost=baseline_cost,
                alert_level=AlertLevel.CRITICAL,
                reason=f"CRITICAL: Exceeded daily budget (${daily_budget:.2f}) by ${excess:.2f} ({percent_over:.1f}%)",
                timestamp=timestamp,
                deviation_percent=percent_over
            ))
        
        return alerts


__all__ = ["CostAnomalyDetector", "CostAnomalyAlert", "AlertLevel"]
