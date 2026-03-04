"""
Capacity Metrics Collection Service

This service collects system, application, and database metrics at regular intervals
for use in capacity headroom forecasting.
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List
import psutil

from app.ml.capacity_headroom_forecaster import CapacityMetrics

logger = logging.getLogger(__name__)


class CapacityMetricsService:
    """
    Service for collecting and managing capacity metrics.
    
    Collects metrics from:
    - System resources (CPU, memory, disk)
    - Application (request rate, active users)
    - Database (connection pool, query performance)
    
    Stores metrics in database for historical analysis.
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize metrics service.
        
        Args:
            config: Configuration dict with keys:
                - collection_interval_seconds: How often to collect (default: 300)
                - retention_days: Keep metrics for N days (default: 30)
                - enabled: Whether service is enabled (default: True)
        """
        if config is None:
            config = {}
        
        self.collection_interval_seconds = config.get('collection_interval_seconds', 300)
        self.retention_days = config.get('retention_days', 30)
        self.enabled = config.get('enabled', True)
        
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._metrics_store: List[CapacityMetrics] = []
        
        logger.info(
            "metrics_service_initialized",
            extra={
                "collection_interval_seconds": self.collection_interval_seconds,
                "retention_days": self.retention_days,
                "enabled": self.enabled
            }
        )

    def start(self) -> None:
        """Start the background metrics collection thread."""
        if not self.enabled:
            logger.info("Metrics service disabled, not starting")
            return
        
        if self._collection_thread is not None and self._collection_thread.is_alive():
            logger.warning("Metrics collection already running")
            return
        
        self._stop_event.clear()
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            daemon=False,
            name="CapacityMetricsCollector"
        )
        self._collection_thread.start()
        logger.info("Metrics collection service started")

    def stop(self) -> None:
        """Stop the background metrics collection thread."""
        if self._collection_thread is None:
            return
        
        logger.info("Stopping metrics collection service")
        self._stop_event.set()
        
        if self._collection_thread.is_alive():
            self._collection_thread.join(timeout=10)
        
        logger.info("Metrics collection service stopped")

    def _collection_loop(self) -> None:
        """Background loop that collects metrics at regular intervals."""
        while not self._stop_event.is_set():
            try:
                metrics = self.collect_all_metrics()
                if metrics:
                    self._store_metrics(metrics)
                    self._cleanup_old_metrics()
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {str(e)}", exc_info=True)
            
            # Wait for next collection interval or stop signal
            self._stop_event.wait(timeout=self.collection_interval_seconds)

    def collect_all_metrics(self) -> Optional[CapacityMetrics]:
        """
        Collect all metrics from system, application, and database.
        
        Returns:
            CapacityMetrics object with all current metrics, or None on error
        """
        try:
            # System metrics
            cpu_usage = self._collect_cpu_metrics()
            memory_usage = self._collect_memory_metrics()
            disk_usage = self._collect_disk_metrics()
            
            # Application metrics (would be populated by monitoring)
            request_rate = self._collect_request_rate()
            active_users = self._collect_active_users()
            
            # Database metrics
            db_connections = self._collect_db_connections()
            avg_response_time = self._collect_avg_response_time()
            
            metrics = CapacityMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                request_rate=request_rate,
                active_users=active_users,
                db_connections_active=db_connections,
                avg_response_time_ms=avg_response_time,
                timestamp=datetime.now()
            )
            
            logger.info(
                "metrics_collected",
                extra=metrics.to_dict()
            )
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}", exc_info=True)
            return None

    def _collect_cpu_metrics(self) -> float:
        """Collect CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=1)
        except Exception as e:
            logger.error(f"Failed to collect CPU metrics: {str(e)}")
            return 0.0

    def _collect_memory_metrics(self) -> float:
        """Collect memory usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {str(e)}")
            return 0.0

    def _collect_disk_metrics(self) -> float:
        """Collect disk usage percentage."""
        try:
            return psutil.disk_usage('/').percent
        except Exception as e:
            logger.error(f"Failed to collect disk metrics: {str(e)}")
            return 0.0

    def _collect_request_rate(self) -> int:
        """
        Collect application request rate.
        
        In a real system, this would query the application's request counter.
        Currently returns 0 as a placeholder.
        """
        # TODO: Integrate with application request tracking
        return 0

    def _collect_active_users(self) -> int:
        """
        Collect number of active users.
        
        In a real system, this would query the database for active sessions.
        Currently returns 0 as a placeholder.
        """
        # TODO: Query user_sessions table for active sessions
        return 0

    def _collect_db_connections(self) -> int:
        """
        Collect active database connections.
        
        In a real system, this would query the connection pool status.
        Currently returns 0 as a placeholder.
        """
        # TODO: Query SQLAlchemy connection pool status
        return 0

    def _collect_avg_response_time(self) -> float:
        """
        Collect average response time.
        
        In a real system, this would calculate from request logs.
        Currently returns 0.0 as a placeholder.
        """
        # TODO: Calculate from request monitoring data
        return 0.0

    def _store_metrics(self, metrics: CapacityMetrics) -> None:
        """
        Store metrics in database.
        
        Args:
            metrics: CapacityMetrics to store
        """
        try:
            # Add to in-memory store
            self._metrics_store.append(metrics)
            
            # TODO: Also store in database for persistence
            # This would be: insert into capacity_metrics (...)
            # See app/models.py for the model definition
            
            logger.debug(f"Metrics stored. Total in memory: {len(self._metrics_store)}")
        except Exception as e:
            logger.error(f"Failed to store metrics: {str(e)}", exc_info=True)

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.retention_days)
            
            # Clean in-memory store
            original_count = len(self._metrics_store)
            self._metrics_store = [
                m for m in self._metrics_store if m.timestamp >= cutoff_time
            ]
            cleaned_count = original_count - len(self._metrics_store)
            
            if cleaned_count > 0:
                logger.info(
                    "old_metrics_cleaned",
                    extra={
                        "removed_count": cleaned_count,
                        "retention_days": self.retention_days
                    }
                )
            
            # TODO: Also clean from database
            # This would be: delete from capacity_metrics where timestamp < cutoff_time
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {str(e)}", exc_info=True)

    def get_recent_metrics(self, hours: int = 24) -> List[CapacityMetrics]:
        """
        Get recently collected metrics.
        
        Args:
            hours: Number of hours of history to return
            
        Returns:
            List of CapacityMetrics from the past N hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self._metrics_store if m.timestamp >= cutoff_time]

    def get_metrics_for_analysis(self, days: int = 30) -> List[CapacityMetrics]:
        """
        Get all metrics available for analysis.
        
        Args:
            days: Number of days of history to return
            
        Returns:
            List of CapacityMetrics from the past N days
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        return [m for m in self._metrics_store if m.timestamp >= cutoff_time]

    def clear_metrics(self) -> None:
        """Clear all in-memory metrics."""
        self._metrics_store.clear()
        logger.info("In-memory metrics cleared")


# Global instance for application-wide access
_metrics_service_instance: Optional[CapacityMetricsService] = None


def get_metrics_service(config: Optional[dict] = None) -> CapacityMetricsService:
    """
    Get or create the global metrics service instance.
    
    Args:
        config: Configuration dict (used only on first call)
        
    Returns:
        CapacityMetricsService instance
    """
    global _metrics_service_instance
    if _metrics_service_instance is None:
        _metrics_service_instance = CapacityMetricsService(config)
    return _metrics_service_instance


def reset_metrics_service() -> None:
    """Reset the global metrics service instance (for testing)."""
    global _metrics_service_instance
    if _metrics_service_instance is not None:
        _metrics_service_instance.stop()
    _metrics_service_instance = None
