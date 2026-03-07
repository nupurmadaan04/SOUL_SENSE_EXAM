"""
Integration tests for Connection Pool Starvation Diagnostics (#1408).

Tests the integration between pool diagnostics and the database service,
including health endpoint integration and real pool monitoring.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.utils.connection_pool_diagnostics import (
    PoolDiagnostics,
    PoolHealthStatus,
    StarvationRiskLevel,
    DiagnosticsConfig,
    ConnectionPoolHealthCheck,
    get_pool_diagnostics,
    shutdown_pool_diagnostics,
)
from api.services.db_service import engine, get_pool_status


@pytest.fixture
def pool_diagnostics():
    """Create pool diagnostics instance for testing."""
    diagnostics = PoolDiagnostics(
        engine,
        DiagnosticsConfig(
            utilization_warning_threshold=70.0,
            utilization_critical_threshold=90.0,
            metrics_collection_interval_seconds=1.0,  # Short interval for testing
        )
    )
    return diagnostics


@pytest.mark.asyncio
async def test_pool_status_retrieval(pool_diagnostics):
    """Test retrieving pool status from real engine."""
    status = await pool_diagnostics.get_pool_status()
    
    assert status is not None
    assert "pool_type" in status
    
    # Should be QueuePool for PostgreSQL or StaticPool for SQLite
    assert status["pool_type"] in ["QueuePool", "StaticPool", "NullPool"]


@pytest.mark.asyncio
async def test_metrics_collection(pool_diagnostics):
    """Test collecting metrics from real pool."""
    metrics = await pool_diagnostics.collect_metrics()
    
    if metrics:
        assert metrics.timestamp is not None
        assert metrics.pool_size >= 0
        assert metrics.checked_in >= 0
        assert metrics.checked_out >= 0
        assert metrics.total_connections >= 0
        assert 0 <= metrics.utilization_percent <= 100


@pytest.mark.asyncio
async def test_health_check(pool_diagnostics):
    """Test health check on real pool."""
    report = await pool_diagnostics.health_check()
    
    assert report is not None
    assert report.status in [
        PoolHealthStatus.HEALTHY,
        PoolHealthStatus.DEGRADED,
        PoolHealthStatus.CRITICAL,
        PoolHealthStatus.UNKNOWN,
    ]
    assert isinstance(report.alerts, list)
    assert isinstance(report.recommendations, list)


@pytest.mark.asyncio
async def test_metrics_history(pool_diagnostics):
    """Test metrics history tracking."""
    # Collect multiple metrics
    for _ in range(5):
        await pool_diagnostics.collect_metrics()
        await asyncio.sleep(0.1)  # Small delay between collections
    
    history = pool_diagnostics.get_metrics_history()
    assert len(history) > 0
    
    # Test limit
    limited_history = pool_diagnostics.get_metrics_history(limit=3)
    assert len(limited_history) <= 3


@pytest.mark.asyncio
async def test_alert_history(pool_diagnostics):
    """Test alert history tracking."""
    history = pool_diagnostics.get_alert_history()
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_statistics(pool_diagnostics):
    """Test statistics collection."""
    stats = pool_diagnostics.get_statistics()
    
    assert "total_timeouts" in stats
    assert "total_starved_requests" in stats
    assert "metrics_collected" in stats
    assert "alerts_triggered" in stats
    assert "monitoring_active" in stats


@pytest.mark.asyncio
async def test_monitoring_lifecycle(pool_diagnostics):
    """Test starting and stopping monitoring."""
    # Initially not monitoring
    assert pool_diagnostics._monitoring is False
    
    # Start monitoring
    await pool_diagnostics.start_monitoring()
    assert pool_diagnostics._monitoring is True
    
    # Let it collect some metrics
    await asyncio.sleep(1.5)
    
    # Stop monitoring
    await pool_diagnostics.stop_monitoring()
    assert pool_diagnostics._monitoring is False


@pytest.mark.asyncio
async def test_health_check_adapter(pool_diagnostics):
    """Test health check adapter integration."""
    adapter = ConnectionPoolHealthCheck(pool_diagnostics)
    result = await adapter.check()
    
    assert result is not None
    assert "status" in result
    assert "details" in result
    assert result["status"] in ["healthy", "degraded", "unhealthy", "unknown"]


@pytest.mark.asyncio
async def test_comprehensive_status(pool_diagnostics):
    """Test getting comprehensive status."""
    status = await pool_diagnostics.get_status()
    
    assert "pool" in status
    assert "metrics" in status
    assert "health" in status
    assert "statistics" in status


@pytest.mark.asyncio
async def test_callback_registration(pool_diagnostics):
    """Test alert callback registration."""
    alerts_received = []
    
    def test_callback(message, metrics):
        alerts_received.append(message)
    
    pool_diagnostics.register_alert_callback(test_callback)
    
    # Verify callback is registered
    assert test_callback in pool_diagnostics._alert_callbacks


@pytest.mark.asyncio
async def test_timeout_tracking(pool_diagnostics):
    """Test timeout event tracking."""
    initial_timeouts = pool_diagnostics._total_timeouts
    initial_starved = pool_diagnostics._total_starved_requests
    
    pool_diagnostics.record_timeout()
    
    assert pool_diagnostics._total_timeouts == initial_timeouts + 1
    assert pool_diagnostics._total_starved_requests == initial_starved + 1


@pytest.mark.asyncio
async def test_starvation_risk_levels(pool_diagnostics):
    """Test different starvation risk levels."""
    from api.utils.connection_pool_diagnostics import PoolMetrics
    
    test_cases = [
        # (checked_in, checked_out, utilization, wait_time, expected_risk)
        (10, 0, 0, 0, StarvationRiskLevel.NONE),
        (5, 5, 50, 0, StarvationRiskLevel.NONE),
        (3, 7, 75, 50, StarvationRiskLevel.LOW),
        (2, 8, 85, 150, StarvationRiskLevel.MEDIUM),
        (0, 10, 95, 600, StarvationRiskLevel.HIGH),
    ]
    
    for checked_in, checked_out, utilization, wait_time, expected_risk in test_cases:
        metrics = PoolMetrics(
            timestamp=datetime.utcnow(),
            pool_size=10,
            checked_in=checked_in,
            checked_out=checked_out,
            overflow=0,
            utilization_percent=utilization,
            wait_time_ms=wait_time,
        )
        
        risk = pool_diagnostics._calculate_starvation_risk(metrics)
        
        # For critical risk, we need checked_in == 0
        if checked_in == 0 and wait_time > 500:
            expected_risk = StarvationRiskLevel.CRITICAL
        
        assert risk.value == expected_risk.value, \
            f"Expected {expected_risk.value} for utilization={utilization}, " \
            f"wait_time={wait_time}, got {risk.value}"


@pytest.mark.asyncio
async def test_global_diagnostics_lifecycle():
    """Test global diagnostics lifecycle."""
    # Reset global state
    import api.utils.connection_pool_diagnostics as cpd
    cpd._diagnostics_instance = None
    
    # Get diagnostics
    diagnostics = await get_pool_diagnostics(engine)
    assert diagnostics is not None
    assert cpd._diagnostics_instance is not None
    
    # Verify it's monitoring
    assert cpd._diagnostics_instance._monitoring is True
    
    # Shutdown
    await shutdown_pool_diagnostics()
    assert cpd._diagnostics_instance is None


@pytest.mark.asyncio
async def test_pool_utilization_boundaries(pool_diagnostics):
    """Test pool utilization boundary conditions."""
    from api.utils.connection_pool_diagnostics import PoolMetrics
    
    # Test 0% utilization
    metrics_0 = PoolMetrics(
        timestamp=datetime.utcnow(),
        pool_size=10,
        checked_in=10,
        checked_out=0,
        overflow=0,
        utilization_percent=0,
    )
    
    # Test 100% utilization
    metrics_100 = PoolMetrics(
        timestamp=datetime.utcnow(),
        pool_size=10,
        checked_in=0,
        checked_out=10,
        overflow=5,
        utilization_percent=100,
    )
    
    # Test calculation for 0% utilization
    risk_0 = pool_diagnostics._calculate_starvation_risk(metrics_0)
    assert risk_0 == StarvationRiskLevel.NONE
    
    # Test calculation for 100% utilization
    risk_100 = pool_diagnostics._calculate_starvation_risk(metrics_100)
    assert risk_100 in [StarvationRiskLevel.HIGH, StarvationRiskLevel.CRITICAL]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
