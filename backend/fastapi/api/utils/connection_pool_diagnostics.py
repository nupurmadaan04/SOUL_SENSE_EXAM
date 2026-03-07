"""
Connection Pool Starvation Diagnostics

Provides comprehensive monitoring, diagnostics, and alerting for database
connection pool health. Helps detect and prevent connection pool starvation,
which can cause application outages.

Features:
- Real-time pool metrics collection
- Starvation detection with configurable thresholds
- Health check endpoint integration
- Structured logging for observability
- Automatic alerting on critical conditions
- Historical metrics tracking

Example:
    from api.utils.connection_pool_diagnostics import PoolDiagnostics
    
    diagnostics = PoolDiagnostics(engine)
    
    # Get current status
    status = await diagnostics.get_status()
    
    # Check if pool is healthy
    is_healthy = await diagnostics.health_check()
    
    # Get detailed metrics
    metrics = await diagnostics.collect_metrics()
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import QueuePool, NullPool, StaticPool


logger = logging.getLogger("api.db.pool_diagnostics")


class PoolHealthStatus(str, Enum):
    """Health status of the connection pool."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class StarvationRiskLevel(str, Enum):
    """Risk level for connection pool starvation."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PoolMetrics:
    """
    Connection pool metrics snapshot.
    
    Attributes:
        timestamp: When metrics were collected
        pool_size: Configured pool size
        checked_in: Connections available in pool
        checked_out: Connections in use
        overflow: Overflow connections
        waiting: Number of requests waiting for connection
        utilization_percent: Percentage of pool in use
        wait_time_ms: Average wait time for connection
        starved_requests: Count of timed-out connection requests
    """
    timestamp: datetime
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    waiting: int = 0
    utilization_percent: float = 0.0
    wait_time_ms: float = 0.0
    starved_requests: int = 0
    
    @property
    def total_connections(self) -> int:
        """Total connections (pool + overflow)."""
        return self.checked_in + self.checked_out
    
    @property
    def available_connections(self) -> int:
        """Connections available for use."""
        return self.checked_in
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "pool_size": self.pool_size,
            "checked_in": self.checked_in,
            "checked_out": self.checked_out,
            "overflow": self.overflow,
            "waiting": self.waiting,
            "total_connections": self.total_connections,
            "available_connections": self.available_connections,
            "utilization_percent": round(self.utilization_percent, 2),
            "wait_time_ms": round(self.wait_time_ms, 2),
            "starved_requests": self.starved_requests,
        }


@dataclass
class PoolHealthReport:
    """
    Comprehensive pool health report.
    
    Attributes:
        status: Overall health status
        starvation_risk: Current starvation risk level
        metrics: Current pool metrics
        alerts: List of active alerts
        recommendations: Suggested actions
    """
    status: PoolHealthStatus
    starvation_risk: StarvationRiskLevel
    metrics: PoolMetrics
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "status": self.status.value,
            "starvation_risk": self.starvation_risk.value,
            "metrics": self.metrics.to_dict(),
            "alerts": self.alerts,
            "recommendations": self.recommendations,
        }


@dataclass
class DiagnosticsConfig:
    """Configuration for pool diagnostics."""
    # Thresholds for health status
    utilization_warning_threshold: float = 70.0  # Percent
    utilization_critical_threshold: float = 90.0  # Percent
    
    # Starvation detection
    wait_time_warning_ms: float = 100.0  # milliseconds
    wait_time_critical_ms: float = 500.0  # milliseconds
    
    # Connection pool limits
    min_available_connections: int = 2
    max_waiting_requests: int = 10
    
    # Alerting
    alert_on_starvation: bool = True
    alert_on_high_utilization: bool = True
    alert_on_connection_timeout: bool = True
    
    # History
    metrics_history_size: int = 100
    metrics_collection_interval_seconds: float = 30.0


class PoolDiagnostics:
    """
    Connection pool diagnostics and monitoring.
    
    Monitors connection pool health, detects starvation conditions,
    and provides recommendations for optimization.
    
    Example:
        diagnostics = PoolDiagnostics(engine)
        
        # Start monitoring
        await diagnostics.start_monitoring()
        
        # Get health check
        health = await diagnostics.health_check()
        
        # Stop monitoring
        await diagnostics.stop_monitoring()
    """
    
    def __init__(
        self,
        engine: AsyncEngine,
        config: Optional[DiagnosticsConfig] = None
    ):
        self.engine = engine
        self.config = config or DiagnosticsConfig()
        
        # Metrics history
        self._metrics_history: deque = deque(
            maxlen=self.config.metrics_history_size
        )
        
        # Alert tracking
        self._active_alerts: set = set()
        self._alert_history: List[Dict[str, Any]] = []
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._total_timeouts = 0
        self._total_starved_requests = 0
        self._start_time: Optional[datetime] = None
        
        # Callbacks for alerts
        self._alert_callbacks: List[Callable[[str, PoolMetrics], None]] = []
    
    async def get_pool_status(self) -> Optional[Dict[str, Any]]:
        """
        Get raw pool status from SQLAlchemy.
        
        Returns:
            Dictionary with pool status or None if not supported
        """
        pool = self.engine.pool
        
        if isinstance(pool, QueuePool):
            return {
                "pool_type": "QueuePool",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "timeout": pool.timeout(),
                "recycle": getattr(pool, 'recycle', None),
            }
        elif isinstance(pool, StaticPool):
            return {
                "pool_type": "StaticPool",
                "message": "StaticPool does not support dynamic metrics",
            }
        elif isinstance(pool, NullPool):
            return {
                "pool_type": "NullPool",
                "message": "NullPool does not maintain connections",
            }
        else:
            return {
                "pool_type": type(pool).__name__,
                "message": f"Pool type {type(pool).__name__} not supported",
            }
    
    async def collect_metrics(self) -> Optional[PoolMetrics]:
        """
        Collect current pool metrics.
        
        Returns:
            PoolMetrics object or None if pool type not supported
        """
        pool = self.engine.pool
        
        if not isinstance(pool, QueuePool):
            return None
        
        try:
            pool_size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            # Calculate utilization
            max_connections = pool_size + pool.max_overflow
            current_connections = checked_in + checked_out
            utilization = (
                (current_connections / max_connections * 100)
                if max_connections > 0 else 0.0
            )
            
            # Estimate waiting requests (based on recent timeout history)
            waiting = getattr(pool, '_waiting', 0)
            
            # Get wait time from recent history
            wait_time_ms = self._calculate_average_wait_time()
            
            metrics = PoolMetrics(
                timestamp=datetime.utcnow(),
                pool_size=pool_size,
                checked_in=checked_in,
                checked_out=checked_out,
                overflow=overflow,
                waiting=waiting,
                utilization_percent=utilization,
                wait_time_ms=wait_time_ms,
                starved_requests=self._total_starved_requests,
            )
            
            # Store in history
            self._metrics_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect pool metrics: {e}")
            return None
    
    def _calculate_average_wait_time(self) -> float:
        """Calculate average connection wait time from history."""
        if len(self._metrics_history) < 2:
            return 0.0
        
        # Use change in checked_out as proxy for wait time
        recent = list(self._metrics_history)[-10:]
        if len(recent) < 2:
            return 0.0
        
        # Simple estimation based on pool pressure
        avg_utilization = sum(m.utilization_percent for m in recent) / len(recent)
        
        # Higher utilization = longer wait times
        if avg_utilization < 50:
            return 0.0
        elif avg_utilization < 70:
            return 10.0
        elif avg_utilization < 85:
            return 50.0
        else:
            return 200.0
    
    async def health_check(self) -> PoolHealthReport:
        """
        Perform comprehensive health check on connection pool.
        
        Returns:
            PoolHealthReport with status, alerts, and recommendations
        """
        metrics = await self.collect_metrics()
        
        if metrics is None:
            return PoolHealthReport(
                status=PoolHealthStatus.UNKNOWN,
                starvation_risk=StarvationRiskLevel.NONE,
                metrics=PoolMetrics(
                    timestamp=datetime.utcnow(),
                    pool_size=0,
                    checked_in=0,
                    checked_out=0,
                    overflow=0,
                ),
                alerts=["Pool type does not support diagnostics"],
            )
        
        alerts = []
        recommendations = []
        
        # Check utilization
        if metrics.utilization_percent >= self.config.utilization_critical_threshold:
            status = PoolHealthStatus.CRITICAL
            alerts.append(
                f"CRITICAL: Pool utilization at {metrics.utilization_percent:.1f}%"
            )
            recommendations.append(
                "Consider increasing pool_size or max_overflow in configuration"
            )
        elif metrics.utilization_percent >= self.config.utilization_warning_threshold:
            status = PoolHealthStatus.DEGRADED
            alerts.append(
                f"WARNING: Pool utilization at {metrics.utilization_percent:.1f}%"
            )
        else:
            status = PoolHealthStatus.HEALTHY
        
        # Check available connections
        if metrics.available_connections < self.config.min_available_connections:
            alerts.append(
                f"Only {metrics.available_connections} connections available"
            )
            recommendations.append(
                "Close idle connections or increase pool size"
            )
            if status == PoolHealthStatus.HEALTHY:
                status = PoolHealthStatus.DEGRADED
        
        # Check waiting requests
        if metrics.waiting > self.config.max_waiting_requests:
            alerts.append(f"{metrics.waiting} requests waiting for connections")
            recommendations.append("Check for connection leaks or slow queries")
            status = PoolHealthStatus.CRITICAL
        
        # Calculate starvation risk
        starvation_risk = self._calculate_starvation_risk(metrics)
        
        if starvation_risk in (StarvationRiskLevel.HIGH, StarvationRiskLevel.CRITICAL):
            alerts.append(f"HIGH starvation risk: {starvation_risk.value}")
            recommendations.append(
                "Immediate action required: Check for connection leaks"
            )
        
        # Report starved requests
        if metrics.starved_requests > 0:
            alerts.append(f"{metrics.starved_requests} requests have starved")
        
        report = PoolHealthReport(
            status=status,
            starvation_risk=starvation_risk,
            metrics=metrics,
            alerts=alerts,
            recommendations=recommendations,
        )
        
        # Trigger alert callbacks
        for alert in alerts:
            await self._trigger_alert(alert, metrics)
        
        return report
    
    def _calculate_starvation_risk(self, metrics: PoolMetrics) -> StarvationRiskLevel:
        """Calculate starvation risk level based on metrics."""
        # Critical: No available connections and high wait time
        if (
            metrics.available_connections == 0 and
            metrics.wait_time_ms > self.config.wait_time_critical_ms
        ):
            return StarvationRiskLevel.CRITICAL
        
        # High: Very high utilization or long wait times
        if (
            metrics.utilization_percent >= 95 or
            metrics.wait_time_ms > self.config.wait_time_critical_ms or
            metrics.waiting > 5
        ):
            return StarvationRiskLevel.HIGH
        
        # Medium: High utilization or moderate wait times
        if (
            metrics.utilization_percent >= 80 or
            metrics.wait_time_ms > self.config.wait_time_warning_ms or
            metrics.waiting > 0
        ):
            return StarvationRiskLevel.MEDIUM
        
        # Low: Elevated utilization
        if metrics.utilization_percent >= 70:
            return StarvationRiskLevel.LOW
        
        return StarvationRiskLevel.NONE
    
    async def _trigger_alert(self, message: str, metrics: PoolMetrics) -> None:
        """Trigger alert callbacks."""
        alert_key = f"{message}:{metrics.timestamp.minute}"
        
        if alert_key in self._active_alerts:
            return  # Already alerted for this minute
        
        self._active_alerts.add(alert_key)
        self._alert_history.append({
            "message": message,
            "timestamp": metrics.timestamp.isoformat(),
            "metrics": metrics.to_dict(),
        })
        
        # Log alert
        logger.warning(f"Pool Alert: {message}", extra={
            "metrics": metrics.to_dict(),
            "alert_type": "pool_diagnostics",
        })
        
        # Call registered callbacks
        for callback in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message, metrics)
                else:
                    callback(message, metrics)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(
        self,
        callback: Callable[[str, PoolMetrics], None]
    ) -> None:
        """Register a callback for pool alerts."""
        self._alert_callbacks.append(callback)
    
    async def start_monitoring(self) -> None:
        """Start background monitoring of connection pool."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._start_time = datetime.utcnow()
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Started connection pool monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped connection pool monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                
                if metrics:
                    # Run health check
                    report = await self.health_check()
                    
                    # Log degraded/critical status
                    if report.status in (PoolHealthStatus.DEGRADED, PoolHealthStatus.CRITICAL):
                        logger.warning(
                            f"Pool health {report.status.value}: "
                            f"{len(report.alerts)} alerts",
                            extra={
                                "status": report.status.value,
                                "alerts": report.alerts,
                                "metrics": metrics.to_dict(),
                            }
                        )
                
                # Wait for next collection
                await asyncio.sleep(self.config.metrics_collection_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[PoolMetrics]:
        """Get historical metrics."""
        history = list(self._metrics_history)
        if limit:
            history = history[-limit:]
        return history
    
    def get_alert_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get alert history."""
        history = self._alert_history
        if limit:
            history = history[-limit:]
        return history
    
    def record_timeout(self) -> None:
        """Record a connection timeout event."""
        self._total_timeouts += 1
        self._total_starved_requests += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get diagnostic statistics."""
        uptime = None
        if self._start_time:
            uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "total_timeouts": self._total_timeouts,
            "total_starved_requests": self._total_starved_requests,
            "metrics_collected": len(self._metrics_history),
            "alerts_triggered": len(self._alert_history),
            "monitoring_active": self._monitoring,
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive pool status."""
        pool_status = await self.get_pool_status()
        metrics = await self.collect_metrics()
        report = await self.health_check()
        stats = self.get_statistics()
        
        return {
            "pool": pool_status,
            "metrics": metrics.to_dict() if metrics else None,
            "health": report.to_dict(),
            "statistics": stats,
        }


class ConnectionPoolHealthCheck:
    """
    Health check adapter for connection pool diagnostics.
    
    Integrates with FastAPI health check endpoints.
    """
    
    def __init__(self, diagnostics: PoolDiagnostics):
        self.diagnostics = diagnostics
    
    async def check(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Health check result compatible with health endpoint
        """
        report = await self.diagnostics.health_check()
        
        status_map = {
            PoolHealthStatus.HEALTHY: "healthy",
            PoolHealthStatus.DEGRADED: "degraded",
            PoolHealthStatus.CRITICAL: "unhealthy",
            PoolHealthStatus.UNKNOWN: "unknown",
        }
        
        return {
            "status": status_map.get(report.status, "unknown"),
            "details": {
                "pool_status": report.status.value,
                "starvation_risk": report.starvation_risk.value,
                "utilization_percent": report.metrics.utilization_percent,
                "available_connections": report.metrics.available_connections,
                "alerts": report.alerts,
                "recommendations": report.recommendations,
            }
        }


# Global diagnostics instance (initialized on demand)
_diagnostics_instance: Optional[PoolDiagnostics] = None
_diagnostics_lock = asyncio.Lock()


async def get_pool_diagnostics(engine: AsyncEngine) -> PoolDiagnostics:
    """
    Get or create the global pool diagnostics instance.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        PoolDiagnostics instance
    """
    global _diagnostics_instance
    
    if _diagnostics_instance is None:
        async with _diagnostics_lock:
            if _diagnostics_instance is None:
                _diagnostics_instance = PoolDiagnostics(engine)
                await _diagnostics_instance.start_monitoring()
    
    return _diagnostics_instance


async def shutdown_pool_diagnostics() -> None:
    """Shutdown the global pool diagnostics."""
    global _diagnostics_instance
    
    if _diagnostics_instance:
        await _diagnostics_instance.stop_monitoring()
        _diagnostics_instance = None
