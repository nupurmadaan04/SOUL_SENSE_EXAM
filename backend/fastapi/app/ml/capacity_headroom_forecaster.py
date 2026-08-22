"""
Capacity Headroom Forecasting for Peak Windows

This module provides capacity headroom forecasting to predict resource utilization
during peak windows and prevent performance degradation. It analyzes historical
metrics to forecast when capacity thresholds will be exceeded.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from statistics import mean, stdev
import psutil

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for capacity forecasting."""
    LOW = "low"              # > 50% headroom remaining
    MEDIUM = "medium"        # 30-50% headroom remaining
    HIGH = "high"            # 10-30% headroom remaining
    CRITICAL = "critical"    # < 10% headroom remaining


@dataclass
class CapacityMetrics:
    """Current capacity metrics snapshot."""
    cpu_usage: float                    # CPU usage percentage (0-100)
    memory_usage: float                 # Memory usage percentage (0-100)
    disk_usage: float                   # Disk usage percentage (0-100)
    request_rate: int                   # Requests per second
    active_users: int                   # Number of active users
    db_connections_active: int          # Active database connections
    avg_response_time_ms: float         # Average response time in milliseconds
    timestamp: datetime                 # When metrics were collected

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'request_rate': self.request_rate,
            'active_users': self.active_users,
            'db_connections_active': self.db_connections_active,
            'avg_response_time_ms': self.avg_response_time_ms,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PeakWindow:
    """Predicted peak window characteristics."""
    start_time: datetime
    end_time: datetime
    predicted_cpu: float
    predicted_memory: float
    predicted_disk: float
    predicted_request_rate: int
    confidence: float                   # Confidence score 0-1

    def duration_minutes(self) -> int:
        """Get duration of peak window in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_minutes': self.duration_minutes(),
            'predicted_cpu': self.predicted_cpu,
            'predicted_memory': self.predicted_memory,
            'predicted_disk': self.predicted_disk,
            'predicted_request_rate': self.predicted_request_rate,
            'confidence': round(self.confidence, 2)
        }


@dataclass
class CapacityForecast:
    """Complete capacity forecast result."""
    current_headroom: Dict[str, float]
    peak_window: Optional[PeakWindow]
    time_to_capacity_minutes: Optional[int]
    risk_level: RiskLevel
    recommendations: List[str] = field(default_factory=list)
    forecast_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert forecast to dictionary."""
        return {
            'current_headroom': self.current_headroom,
            'peak_window': self.peak_window.to_dict() if self.peak_window else None,
            'time_to_capacity_minutes': self.time_to_capacity_minutes,
            'risk_level': self.risk_level.value,
            'recommendations': self.recommendations,
            'forecast_timestamp': self.forecast_timestamp.isoformat()
        }


class CapacityHeadroomForecaster:
    """
    Forecasts capacity headroom and predicts when peak windows will exceed thresholds.
    
    This class analyzes historical metrics to:
    - Calculate current available headroom
    - Detect peak usage patterns (hourly, daily, weekly)
    - Forecast future resource utilization
    - Identify when capacity thresholds will be breached
    - Recommend scaling actions
    """

    # Capacity threshold percentages
    CRITICAL_THRESHOLD = 90.0      # Alert when any resource > 90%
    WARNING_THRESHOLD = 75.0       # Warn when any resource > 75%
    SAFETY_MARGIN = 20.0           # Keep at least 20% headroom

    def __init__(
        self,
        history_days: int = 30,
        forecast_window_hours: int = 24,
        min_historical_points: int = 10
    ):
        """
        Initialize the capacity forecaster.
        
        Args:
            history_days: Number of days of historical data to analyze
            forecast_window_hours: Hours ahead to forecast
            min_historical_points: Minimum historical data points required for forecasting
        """
        self.history_days = history_days
        self.forecast_window_hours = forecast_window_hours
        self.min_historical_points = min_historical_points
        self.historical_metrics: List[CapacityMetrics] = []

    def add_historical_metrics(self, metrics_list: List[CapacityMetrics]) -> None:
        """
        Add historical metrics for analysis.
        
        Args:
            metrics_list: List of historical CapacityMetrics
        """
        # Sort by timestamp and keep only recent data
        self.historical_metrics = sorted(metrics_list, key=lambda m: m.timestamp)
        cutoff_time = datetime.now() - timedelta(days=self.history_days)
        self.historical_metrics = [
            m for m in self.historical_metrics if m.timestamp >= cutoff_time
        ]
        logger.info(
            "historical_metrics_loaded",
            extra={
                "count": len(self.historical_metrics),
                "time_span_days": self.history_days
            }
        )

    def collect_system_metrics(self) -> CapacityMetrics:
        """
        Collect current system resource metrics.
        
        Returns:
            CapacityMetrics with current system state
        """
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            
            metrics = CapacityMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_info.percent,
                disk_usage=disk_info.percent,
                request_rate=0,  # Would be populated by application metrics
                active_users=0,  # Would be populated by application
                db_connections_active=0,  # Would be populated by DB monitor
                avg_response_time_ms=0.0,  # Would be populated by monitoring
                timestamp=datetime.now()
            )
            
            logger.info(
                "system_metrics_collected",
                extra=metrics.to_dict()
            )
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {str(e)}")
            raise

    def calculate_current_headroom(self, metrics: Optional[CapacityMetrics] = None) -> Dict[str, float]:
        """
        Calculate current available headroom for each resource.
        
        Args:
            metrics: CapacityMetrics to analyze (uses current if None)
            
        Returns:
            Dict with headroom percentages for each resource
        """
        if metrics is None:
            metrics = self.collect_system_metrics()

        headroom = {
            'cpu_headroom_pct': max(0, 100 - metrics.cpu_usage),
            'memory_headroom_pct': max(0, 100 - metrics.memory_usage),
            'disk_headroom_pct': max(0, 100 - metrics.disk_usage),
            'min_headroom_pct': min(
                100 - metrics.cpu_usage,
                100 - metrics.memory_usage,
                100 - metrics.disk_usage
            )
        }
        
        logger.info(
            "headroom_calculated",
            extra=headroom
        )
        return headroom

    def detect_peak_windows(self) -> List[PeakWindow]:
        """
        Detect peak usage windows from historical data.
        
        Analyzes patterns by:
        - Hour of day
        - Day of week
        - Seasonal trends
        
        Returns:
            List of detected or predicted peak windows
        """
        if len(self.historical_metrics) < self.min_historical_points:
            logger.warning(
                "insufficient_historical_data",
                extra={
                    "available_points": len(self.historical_metrics),
                    "required": self.min_historical_points
                }
            )
            return []

        peak_windows = []
        
        # Group metrics by hour of day
        hourly_stats = self._calculate_hourly_stats()
        
        # Find peak hours (above mean + 1 std dev)
        if hourly_stats:
            request_rates = [stats['avg_request_rate'] for stats in hourly_stats.values()]
            if request_rates:
                mean_rate = mean(request_rates)
                std_rate = stdev(request_rates) if len(request_rates) > 1 else 0
                threshold = mean_rate + std_rate
                
                # Detect peak hours
                peak_hours = [
                    hour for hour, stats in hourly_stats.items()
                    if stats['avg_request_rate'] >= threshold
                ]
                
                if peak_hours:
                    # Create peak window predictions for next N hours
                    now = datetime.now()
                    for hour_offset in range(self.forecast_window_hours):
                        check_time = now + timedelta(hours=hour_offset)
                        hour_of_day = check_time.hour
                        
                        if hour_of_day in peak_hours and len(peak_windows) < 5:
                            stats = hourly_stats[hour_of_day]
                            peak_window = PeakWindow(
                                start_time=check_time.replace(minute=0, second=0, microsecond=0),
                                end_time=check_time.replace(minute=59, second=59, microsecond=0),
                                predicted_cpu=stats['avg_cpu'],
                                predicted_memory=stats['avg_memory'],
                                predicted_disk=stats['avg_disk'],
                                predicted_request_rate=int(stats['avg_request_rate']),
                                confidence=0.8
                            )
                            peak_windows.append(peak_window)

        logger.info(
            "peak_windows_detected",
            extra={
                "count": len(peak_windows),
                "forecast_window_hours": self.forecast_window_hours
            }
        )
        return peak_windows

    def _calculate_hourly_stats(self) -> Dict[int, Dict[str, float]]:
        """
        Calculate average metrics grouped by hour of day.
        
        Returns:
            Dict mapping hour (0-23) to average metrics
        """
        hourly_data: Dict[int, List[CapacityMetrics]] = {}
        
        for metric in self.historical_metrics:
            hour = metric.timestamp.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(metric)
        
        hourly_stats = {}
        for hour, metrics_list in hourly_data.items():
            if metrics_list:
                hourly_stats[hour] = {
                    'avg_cpu': mean([m.cpu_usage for m in metrics_list]),
                    'avg_memory': mean([m.memory_usage for m in metrics_list]),
                    'avg_disk': mean([m.disk_usage for m in metrics_list]),
                    'avg_request_rate': mean([m.request_rate for m in metrics_list]),
                    'count': len(metrics_list)
                }
        
        return hourly_stats

    def forecast_capacity(self, current_metrics: Optional[CapacityMetrics] = None) -> CapacityForecast:
        """
        Generate capacity forecast for peak windows.
        
        Main forecasting method that:
        1. Collects current metrics
        2. Calculates current headroom
        3. Detects upcoming peak windows
        4. Projects resource utilization forward
        5. Identifies capacity breaches
        6. Assigns risk level
        
        Args:
            current_metrics: Current metrics (uses collected if None)
            
        Returns:
            CapacityForecast with predictions and recommendations
        """
        if current_metrics is None:
            try:
                current_metrics = self.collect_system_metrics()
            except Exception as e:
                logger.error(f"Failed to forecast capacity: {str(e)}")
                # Return safe default forecast
                return CapacityForecast(
                    current_headroom={'status': 'unavailable'},
                    peak_window=None,
                    time_to_capacity_minutes=None,
                    risk_level=RiskLevel.MEDIUM,
                    recommendations=['Unable to collect metrics. Check system health.']
                )

        # Calculate current headroom
        headroom = self.calculate_current_headroom(current_metrics)
        
        # Detect peak windows
        peak_windows = self.detect_peak_windows()
        next_peak = peak_windows[0] if peak_windows else None
        
        # Determine risk level based on current headroom
        min_headroom = headroom['min_headroom_pct']
        risk_level = self._calculate_risk_level(min_headroom)
        
        # Calculate time to capacity
        time_to_capacity = self._calculate_time_to_capacity(
            current_metrics, peak_windows
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            current_metrics, risk_level, peak_windows
        )
        
        forecast = CapacityForecast(
            current_headroom=headroom,
            peak_window=next_peak,
            time_to_capacity_minutes=time_to_capacity,
            risk_level=risk_level,
            recommendations=recommendations
        )
        
        logger.info(
            "capacity_forecast_generated",
            extra={
                "risk_level": risk_level.value,
                "min_headroom_pct": min_headroom,
                "time_to_capacity_minutes": time_to_capacity,
                "peak_window_detected": next_peak is not None,
                "recommendation_count": len(recommendations)
            }
        )
        
        return forecast

    def _calculate_risk_level(self, min_headroom_pct: float) -> RiskLevel:
        """
        Determine risk level based on headroom percentage.
        
        Args:
            min_headroom_pct: Minimum headroom percentage across all resources
            
        Returns:
            RiskLevel enum value
        """
        if min_headroom_pct < 10:
            return RiskLevel.CRITICAL
        elif min_headroom_pct < 30:
            return RiskLevel.HIGH
        elif min_headroom_pct < 50:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_time_to_capacity(
        self,
        current_metrics: CapacityMetrics,
        peak_windows: List[PeakWindow]
    ) -> Optional[int]:
        """
        Calculate minutes until capacity threshold is breached.
        
        Args:
            current_metrics: Current system metrics
            peak_windows: Detected peak windows
            
        Returns:
            Minutes until threshold breach, or None if safe
        """
        if not peak_windows:
            return None

        peak = peak_windows[0]
        time_until_peak = (peak.start_time - datetime.now()).total_seconds() / 60
        
        # If peak CPU/memory will exceed threshold, calculate time to breach
        if peak.predicted_cpu > self.WARNING_THRESHOLD:
            # Linear extrapolation from current to peak
            cpu_growth_rate = (peak.predicted_cpu - current_metrics.cpu_usage) / max(1, time_until_peak)
            minutes_to_threshold = (self.WARNING_THRESHOLD - current_metrics.cpu_usage) / max(0.01, cpu_growth_rate)
            return max(0, int(minutes_to_threshold))
        
        return None if time_until_peak > 0 else 0

    def _generate_recommendations(
        self,
        current_metrics: CapacityMetrics,
        risk_level: RiskLevel,
        peak_windows: List[PeakWindow]
    ) -> List[str]:
        """
        Generate scaling and optimization recommendations.
        
        Args:
            current_metrics: Current metrics
            risk_level: Current risk level
            peak_windows: Predicted peak windows
            
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        # Critical risk - immediate action required
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("🚨 CRITICAL: Scale up resources immediately")
            recommendations.append("Activate on-call engineers")
            recommendations.append("Consider temporary traffic shedding or rate limiting")
        
        # High risk - preventive action needed
        elif risk_level == RiskLevel.HIGH:
            if peak_windows:
                minutes = int((peak_windows[0].start_time - datetime.now()).total_seconds() / 60)
                recommendations.append(
                    f"⚠️  HIGH RISK: Scale up {minutes} minutes before next peak"
                )
            recommendations.append("Optimize database queries")
            recommendations.append("Review and compress logs")
        
        # Medium risk - monitor closely
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("📊 MEDIUM RISK: Increase monitoring frequency")
            if peak_windows:
                recommendations.append(
                    f"Schedule maintenance outside peak hours: {peak_windows[0].start_time.strftime('%H:%M')}"
                )
        
        # Low risk - normal operations
        else:
            recommendations.append("✅ LOW RISK: System operating normally")
            recommendations.append("Continue routine monitoring")

        # Resource-specific recommendations
        if current_metrics.cpu_usage > self.WARNING_THRESHOLD:
            recommendations.append("📈 High CPU usage: Consider horizontal scaling")
        
        if current_metrics.memory_usage > self.WARNING_THRESHOLD:
            recommendations.append("💾 High memory usage: Investigate memory leaks, increase capacity")
        
        if current_metrics.disk_usage > self.WARNING_THRESHOLD:
            recommendations.append("💿 High disk usage: Archive old data, increase storage")

        return recommendations

    def validate_forecast(self, forecast: CapacityForecast) -> bool:
        """
        Validate forecast for consistency and sanity checks.
        
        Args:
            forecast: CapacityForecast to validate
            
        Returns:
            True if forecast passes validation
        """
        try:
            # Validate headroom values
            for key, value in forecast.current_headroom.items():
                if not isinstance(value, (int, float)):
                    logger.warning(f"Invalid headroom value: {key}={value}")
                    return False
                if value < -1 or value > 101:  # Allow small margin of error
                    logger.warning(f"Headroom out of range: {key}={value}")
                    return False
            
            # Validate peak window if present
            if forecast.peak_window:
                if forecast.peak_window.confidence < 0 or forecast.peak_window.confidence > 1:
                    logger.warning(f"Invalid peak window confidence: {forecast.peak_window.confidence}")
                    return False
                
                if forecast.peak_window.predicted_cpu < 0 or forecast.peak_window.predicted_cpu > 100:
                    logger.warning(f"Invalid peak window CPU: {forecast.peak_window.predicted_cpu}")
                    return False
            
            # Validate risk level
            if not isinstance(forecast.risk_level, RiskLevel):
                logger.warning("Invalid risk level")
                return False
            
            # Validate time to capacity
            if forecast.time_to_capacity_minutes is not None:
                if forecast.time_to_capacity_minutes < 0:
                    logger.warning("Negative time to capacity")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Forecast validation error: {str(e)}")
            return False
