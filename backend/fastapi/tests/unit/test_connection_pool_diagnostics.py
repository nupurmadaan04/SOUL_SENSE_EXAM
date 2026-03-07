"""
Unit tests for Connection Pool Starvation Diagnostics (#1408).

Tests pool metrics collection, health checks, starvation detection,
and alerting functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.utils.connection_pool_diagnostics import (
    PoolDiagnostics,
    PoolMetrics,
    PoolHealthReport,
    PoolHealthStatus,
    StarvationRiskLevel,
    DiagnosticsConfig,
    ConnectionPoolHealthCheck,
    get_pool_diagnostics,
    shutdown_pool_diagnostics,
)


class TestPoolMetrics:
    """Test PoolMetrics dataclass."""

    def test_basic_creation(self):
        """Test creating PoolMetrics."""
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=5,
            checked_out=3,
            overflow=2,
        )
        
        assert metrics.pool_size == 10
        assert metrics.checked_in == 5
        assert metrics.checked_out == 3
        assert metrics.overflow == 2
        assert metrics.total_connections == 8
        assert metrics.available_connections == 5

    def test_to_dict(self):
        """Test converting to dictionary."""
        metrics = PoolMetrics(
            timestamp=datetime(2026, 3, 7, 12, 0, 0),
            pool_size=10,
            checked_in=5,
            checked_out=3,
            overflow=2,
            waiting=1,
            utilization_percent=75.5,
            wait_time_ms=100.0,
            starved_requests=2,
        )
        
        result = metrics.to_dict()
        
        assert result["pool_size"] == 10
        assert result["checked_in"] == 5
        assert result["checked_out"] == 3
        assert result["total_connections"] == 8
        assert result["available_connections"] == 5
        assert result["utilization_percent"] == 75.5
        assert result["wait_time_ms"] == 100.0


class TestDiagnosticsConfig:
    """Test DiagnosticsConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DiagnosticsConfig()
        
        assert config.utilization_warning_threshold == 70.0
        assert config.utilization_critical_threshold == 90.0
        assert config.wait_time_warning_ms == 100.0
        assert config.wait_time_critical_ms == 500.0
        assert config.min_available_connections == 2
        assert config.max_waiting_requests == 10
        assert config.metrics_history_size == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = DiagnosticsConfig(
            utilization_warning_threshold=60.0,
            min_available_connections=5,
        )
        
        assert config.utilization_warning_threshold == 60.0
        assert config.min_available_connections == 5
        # Other values remain default
        assert config.utilization_critical_threshold == 90.0


class TestPoolDiagnosticsInitialization:
    """Test PoolDiagnostics initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default config."""
        mock_engine = Mock()
        diagnostics = PoolDiagnostics(mock_engine)
        
        assert diagnostics.engine == mock_engine
        assert diagnostics.config is not None
        assert diagnostics._monitoring is False
        assert len(diagnostics._metrics_history) == 0

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        mock_engine = Mock()
        config = DiagnosticsConfig(pool_size=20)
        diagnostics = PoolDiagnostics(mock_engine, config)
        
        assert diagnostics.config == config


class TestPoolStatus:
    """Test pool status retrieval."""

    @pytest.mark.asyncio
    async def test_get_pool_status_queue_pool(self):
        """Test getting status for QueuePool."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_pool.timeout.return_value = 30
        mock_pool.recycle = 3600
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        status = await diagnostics.get_pool_status()
        
        assert status["pool_type"] == "QueuePool"
        assert status["pool_size"] == 10
        assert status["checked_in"] == 5
        assert status["checked_out"] == 3

    @pytest.mark.asyncio
    async def test_get_pool_status_static_pool(self):
        """Test getting status for StaticPool."""
        from sqlalchemy.pool import StaticPool
        
        mock_engine = Mock()
        mock_engine.pool = Mock(spec=StaticPool)
        
        diagnostics = PoolDiagnostics(mock_engine)
        status = await diagnostics.get_pool_status()
        
        assert status["pool_type"] == "StaticPool"
        assert "message" in status

    @pytest.mark.asyncio
    async def test_get_pool_status_null_pool(self):
        """Test getting status for NullPool."""
        from sqlalchemy.pool import NullPool
        
        mock_engine = Mock()
        mock_engine.pool = Mock(spec=NullPool)
        
        diagnostics = PoolDiagnostics(mock_engine)
        status = await diagnostics.get_pool_status()
        
        assert status["pool_type"] == "NullPool"


class TestMetricsCollection:
    """Test metrics collection."""

    @pytest.mark.asyncio
    async def test_collect_metrics_queue_pool(self):
        """Test collecting metrics from QueuePool."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        metrics = await diagnostics.collect_metrics()
        
        assert metrics is not None
        assert metrics.pool_size == 10
        assert metrics.checked_in == 5
        assert metrics.checked_out == 3
        assert metrics.overflow == 2
        assert metrics.utilization_percent > 0

    @pytest.mark.asyncio
    async def test_collect_metrics_unsupported_pool(self):
        """Test collecting metrics from unsupported pool type."""
        mock_engine = Mock()
        mock_engine.pool = Mock(spec=object)  # Unknown pool type
        
        diagnostics = PoolDiagnostics(mock_engine)
        metrics = await diagnostics.collect_metrics()
        
        assert metrics is None

    @pytest.mark.asyncio
    async def test_metrics_history(self):
        """Test metrics history tracking."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        
        # Collect multiple metrics
        for _ in range(5):
            await diagnostics.collect_metrics()
        
        history = diagnostics.get_metrics_history()
        assert len(history) == 5


class TestStarvationRiskCalculation:
    """Test starvation risk calculation."""

    def test_no_risk(self):
        """Test no starvation risk."""
        diagnostics = PoolDiagnostics(Mock())
        
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=8,
            checked_out=2,
            overflow=0,
            utilization_percent=20.0,
            wait_time_ms=0.0,
        )
        
        risk = diagnostics._calculate_starvation_risk(metrics)
        assert risk == StarvationRiskLevel.NONE

    def test_low_risk(self):
        """Test low starvation risk."""
        diagnostics = PoolDiagnostics(Mock())
        
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=3,
            checked_out=7,
            overflow=0,
            utilization_percent=75.0,
            wait_time_ms=0.0,
        )
        
        risk = diagnostics._calculate_starvation_risk(metrics)
        assert risk == StarvationRiskLevel.LOW

    def test_medium_risk(self):
        """Test medium starvation risk."""
        diagnostics = PoolDiagnostics(Mock())
        
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=2,
            checked_out=8,
            overflow=0,
            utilization_percent=85.0,
            wait_time_ms=150.0,
        )
        
        risk = diagnostics._calculate_starvation_risk(metrics)
        assert risk == StarvationRiskLevel.MEDIUM

    def test_high_risk(self):
        """Test high starvation risk."""
        diagnostics = PoolDiagnostics(Mock())
        
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=0,
            checked_out=10,
            overflow=2,
            utilization_percent=95.0,
            wait_time_ms=600.0,
        )
        
        risk = diagnostics._calculate_starvation_risk(metrics)
        assert risk == StarvationRiskLevel.HIGH

    def test_critical_risk(self):
        """Test critical starvation risk."""
        diagnostics = PoolDiagnostics(Mock())
        
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=0,
            checked_out=10,
            overflow=5,
            utilization_percent=100.0,
            wait_time_ms=600.0,
        )
        
        risk = diagnostics._calculate_starvation_risk(metrics)
        assert risk == StarvationRiskLevel.CRITICAL


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_healthy_pool(self):
        """Test health check for healthy pool."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        report = await diagnostics.health_check()
        
        assert report.status == PoolHealthStatus.HEALTHY
        assert report.starvation_risk == StarvationRiskLevel.NONE
        assert len(report.alerts) == 0

    @pytest.mark.asyncio
    async def test_degraded_pool(self):
        """Test health check for degraded pool."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 3
        mock_pool.checkedout.return_value = 7
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        config = DiagnosticsConfig(utilization_warning_threshold=60.0)
        diagnostics = PoolDiagnostics(mock_engine, config)
        report = await diagnostics.health_check()
        
        assert report.status == PoolHealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_critical_pool(self):
        """Test health check for critical pool."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 5
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        report = await diagnostics.health_check()
        
        assert report.status == PoolHealthStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_health_check_with_recommendations(self):
        """Test health check provides recommendations."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 1  # Very few available
        mock_pool.checkedout.return_value = 9
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        config = DiagnosticsConfig(min_available_connections=2)
        diagnostics = PoolDiagnostics(mock_engine, config)
        report = await diagnostics.health_check()
        
        assert len(report.recommendations) > 0


class TestAlerting:
    """Test alert functionality."""

    @pytest.mark.asyncio
    async def test_alert_callback(self):
        """Test alert callback registration and triggering."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 5
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        
        # Register callback
        callback_called = False
        received_message = None
        
        def alert_callback(message: str, metrics: PoolMetrics):
            nonlocal callback_called, received_message
            callback_called = True
            received_message = message
        
        diagnostics.register_alert_callback(alert_callback)
        
        # Trigger health check which should generate alerts
        await diagnostics.health_check()
        
        assert callback_called is True
        assert received_message is not None

    @pytest.mark.asyncio
    async def test_alert_deduplication(self):
        """Test that duplicate alerts are not triggered."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 5
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        
        callback_count = 0
        
        def alert_callback(message: str, metrics: PoolMetrics):
            nonlocal callback_count
            callback_count += 1
        
        diagnostics.register_alert_callback(alert_callback)
        
        # Trigger multiple health checks
        await diagnostics.health_check()
        await diagnostics.health_check()
        
        # Should only trigger once per minute (deduplication)
        assert callback_count == 1

    def test_record_timeout(self):
        """Test recording timeout events."""
        diagnostics = PoolDiagnostics(Mock())
        
        diagnostics.record_timeout()
        assert diagnostics._total_timeouts == 1
        assert diagnostics._total_starved_requests == 1
        
        diagnostics.record_timeout()
        assert diagnostics._total_timeouts == 2


class TestStatistics:
    """Test statistics tracking."""

    def test_get_statistics(self):
        """Test getting diagnostic statistics."""
        diagnostics = PoolDiagnostics(Mock())
        
        # Add some history
        diagnostics._total_timeouts = 5
        diagnostics._total_starved_requests = 3
        diagnostics._start_time = datetime.utcnow() - timedelta(hours=1)
        
        stats = diagnostics.get_statistics()
        
        assert stats["total_timeouts"] == 5
        assert stats["total_starved_requests"] == 3
        assert stats["uptime_seconds"] is not None
        assert stats["monitoring_active"] is False

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting comprehensive status."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 2
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        status = await diagnostics.get_status()
        
        assert "pool" in status
        assert "metrics" in status
        assert "health" in status
        assert "statistics" in status


class TestMonitoring:
    """Test background monitoring."""

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 5
        mock_pool.checkedout.return_value = 3
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        
        assert diagnostics._monitoring is False
        
        await diagnostics.start_monitoring()
        assert diagnostics._monitoring is True
        assert diagnostics._start_time is not None
        
        await diagnostics.stop_monitoring()
        assert diagnostics._monitoring is False

    @pytest.mark.asyncio
    async def test_monitoring_idempotent(self):
        """Test that start/stop are idempotent."""
        diagnostics = PoolDiagnostics(Mock())
        
        await diagnostics.start_monitoring()
        await diagnostics.start_monitoring()  # Should not error
        
        await diagnostics.stop_monitoring()
        await diagnostics.stop_monitoring()  # Should not error


class TestConnectionPoolHealthCheck:
    """Test ConnectionPoolHealthCheck adapter."""

    @pytest.mark.asyncio
    async def test_health_check_adapter(self):
        """Test health check adapter."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        adapter = ConnectionPoolHealthCheck(diagnostics)
        
        result = await adapter.check()
        
        assert result["status"] in ["healthy", "degraded", "unhealthy", "unknown"]
        assert "details" in result


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_zero_pool_size(self):
        """Test handling of zero pool size."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 0
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 0
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        metrics = await diagnostics.collect_metrics()
        
        assert metrics is not None
        assert metrics.utilization_percent == 0.0

    @pytest.mark.asyncio
    async def test_all_connections_available(self):
        """Test when all connections are available."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 10
        mock_pool.checkedout.return_value = 0
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        metrics = await diagnostics.collect_metrics()
        
        assert metrics.utilization_percent < 70.0  # Should be low
        risk = diagnostics._calculate_starvation_risk(metrics)
        assert risk == StarvationRiskLevel.NONE

    @pytest.mark.asyncio
    async def test_all_connections_in_use(self):
        """Test when all connections are in use."""
        from sqlalchemy.pool import QueuePool
        
        mock_pool = Mock(spec=QueuePool)
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 0
        mock_pool.checkedout.return_value = 10
        mock_pool.overflow.return_value = 0
        mock_pool.max_overflow = 5
        
        mock_engine = Mock()
        mock_engine.pool = mock_pool
        
        diagnostics = PoolDiagnostics(mock_engine)
        report = await diagnostics.health_check()
        
        assert report.status in [PoolHealthStatus.DEGRADED, PoolHealthStatus.CRITICAL]


class TestGlobalDiagnostics:
    """Test global diagnostics functions."""

    @pytest.mark.asyncio
    async def test_get_pool_diagnostics(self):
        """Test getting global pool diagnostics."""
        mock_engine = Mock()
        
        # Reset global state
        import api.utils.connection_pool_diagnostics as cpd
        cpd._diagnostics_instance = None
        
        diagnostics = await get_pool_diagnostics(mock_engine)
        
        assert diagnostics is not None
        assert cpd._diagnostics_instance is not None
        
        # Cleanup
        await shutdown_pool_diagnostics()

    @pytest.mark.asyncio
    async def test_shutdown_pool_diagnostics(self):
        """Test shutting down global diagnostics."""
        mock_engine = Mock()
        
        # Reset global state
        import api.utils.connection_pool_diagnostics as cpd
        cpd._diagnostics_instance = None
        
        # Create instance
        await get_pool_diagnostics(mock_engine)
        assert cpd._diagnostics_instance is not None
        
        # Shutdown
        await shutdown_pool_diagnostics()
        assert cpd._diagnostics_instance is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
