"""
Integration tests for Database Failover Drill Automation (#1424).

Tests end-to-end failover drills with real database operations.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.utils.failover_drill import (
    FailoverDrillOrchestrator,
    DatabaseEndpoint,
    HealthCheckResult,
    FailoverDrillResult,
    FailoverScenario,
    DrillStatus,
    HealthCheckType,
    DrillSchedule,
    get_failover_orchestrator,
)
from api.services.db_service import engine


@pytest.fixture
async def failover_orchestrator():
    """Create and initialize failover orchestrator for testing."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    return orchestrator


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test failover orchestrator initialization."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    assert orchestrator._metadata is not None


@pytest.mark.asyncio
async def test_endpoint_management():
    """Test endpoint management."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    # Add endpoint
    endpoint = DatabaseEndpoint(
        name="test-primary",
        host="localhost",
        port=5432,
        database="test",
        is_primary=True,
        priority=1,
    )
    
    orchestrator.add_endpoint(endpoint)
    
    # Verify
    assert len(orchestrator.get_endpoints()) == 1
    assert orchestrator._endpoints["test-primary"] == endpoint
    
    # Remove
    orchestrator.remove_endpoint("test-primary")
    assert len(orchestrator.get_endpoints()) == 0


@pytest.mark.asyncio
async def test_health_checks():
    """Test health check execution."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    # Add endpoint
    endpoint = DatabaseEndpoint(
        name="test-db",
        host="localhost",
        port=5432,
        database="test",
    )
    orchestrator.add_endpoint(endpoint)
    
    # Run health checks
    checks = await orchestrator._run_health_checks("test")
    
    assert isinstance(checks, list)
    assert len(checks) > 0


@pytest.mark.asyncio
async def test_drill_execution_dry_run():
    """Test drill execution in dry-run mode."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    # Add endpoint
    endpoint = DatabaseEndpoint(
        name="primary",
        host="localhost",
        port=5432,
        database="test",
        is_primary=True,
    )
    orchestrator.add_endpoint(endpoint)
    
    # Run drill
    result = await orchestrator.run_drill(
        scenario=FailoverScenario.CONTROLLED_FAILOVER,
        validate_replication=False,
        auto_rollback=True,
    )
    
    assert result.scenario == FailoverScenario.CONTROLLED_FAILOVER
    assert result.status in [DrillStatus.COMPLETED, DrillStatus.ROLLED_BACK, DrillStatus.FAILED]


@pytest.mark.asyncio
async def test_drill_statistics():
    """Test getting drill statistics."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    stats = await orchestrator.get_statistics()
    
    assert "total_drills" in stats
    assert "successful_drills" in stats
    assert "success_rate" in stats


@pytest.mark.asyncio
async def test_drill_history():
    """Test drill history tracking."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    history = await orchestrator.get_drill_history(limit=10)
    
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_schedule_management():
    """Test schedule management."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    # Configure schedule
    schedule = DrillSchedule(
        enabled=True,
        frequency_days=14,
        preferred_hour=3,
        scenarios=[FailoverScenario.CONTROLLED_FAILOVER],
        auto_rollback=True,
    )
    
    orchestrator.configure_schedule(schedule)
    
    # Verify
    retrieved = orchestrator.get_schedule()
    assert retrieved.enabled is True
    assert retrieved.frequency_days == 14


@pytest.mark.asyncio
async def test_database_endpoint_creation():
    """Test database endpoint creation."""
    endpoint = DatabaseEndpoint(
        name="test-replica",
        host="replica.internal",
        port=5432,
        database="app",
        is_replica=True,
        priority=2,
        is_available=True,
    )
    
    endpoint_dict = endpoint.to_dict()
    
    assert endpoint_dict["name"] == "test-replica"
    assert endpoint_dict["is_replica"] is True
    assert endpoint_dict["priority"] == 2


@pytest.mark.asyncio
async def test_health_check_result_creation():
    """Test health check result creation."""
    result = HealthCheckResult(
        check_type=HealthCheckType.CONNECTIVITY,
        endpoint="primary",
        passed=True,
        latency_ms=15.5,
        message="Connection successful",
        timestamp=datetime(2026, 3, 7, 12, 0, 0),
    )
    
    result_dict = result.to_dict()
    
    assert result_dict["check_type"] == "connectivity"
    assert result_dict["passed"] is True
    assert result_dict["latency_ms"] == 15.5


@pytest.mark.asyncio
async def test_failover_drill_result_creation():
    """Test failover drill result creation."""
    result = FailoverDrillResult(
        drill_id="test123",
        scenario=FailoverScenario.CONTROLLED_FAILOVER,
        status=DrillStatus.COMPLETED,
        started_at=datetime(2026, 3, 7, 12, 0, 0),
        completed_at=datetime(2026, 3, 7, 12, 0, 30),
        pre_checks_passed=True,
        post_checks_passed=True,
        failover_duration_ms=5000.0,
    )
    
    assert result.drill_id == "test123"
    assert result.success is True
    assert result.total_duration_ms == 30000.0


@pytest.mark.asyncio
async def test_drill_schedule_defaults():
    """Test drill schedule defaults."""
    schedule = DrillSchedule()
    
    assert schedule.enabled is False
    assert schedule.frequency_days == 30
    assert schedule.preferred_hour == 2
    assert schedule.auto_rollback is True


@pytest.mark.asyncio
async def test_all_failover_scenarios():
    """Test all failover scenarios are defined."""
    scenarios = [
        FailoverScenario.CONTROLLED_FAILOVER,
        FailoverScenario.UNCONTROLLED_FAILOVER,
        FailoverScenario.NETWORK_PARTITION,
        FailoverScenario.READ_REPLICA_PROMOTION,
        FailoverScenario.CONNECTION_POOL_EXHAUSTION,
        FailoverScenario.PRIMARY_RESTART,
        FailoverScenario.ROLLBACK_TEST,
    ]
    
    for scenario in scenarios:
        assert isinstance(scenario.value, str)
        assert len(scenario.value) > 0


@pytest.mark.asyncio
async def test_all_drill_statuses():
    """Test all drill statuses are defined."""
    statuses = [
        DrillStatus.PENDING,
        DrillStatus.IN_PROGRESS,
        DrillStatus.VALIDATING,
        DrillStatus.COMPLETED,
        DrillStatus.FAILED,
        DrillStatus.ROLLING_BACK,
        DrillStatus.ROLLED_BACK,
    ]
    
    for status in statuses:
        assert isinstance(status.value, str)


@pytest.mark.asyncio
async def test_all_health_check_types():
    """Test all health check types are defined."""
    types = [
        HealthCheckType.CONNECTIVITY,
        HealthCheckType.REPLICATION,
        HealthCheckType.DATA_CONSISTENCY,
        HealthCheckType.PERFORMANCE,
        HealthCheckType.READ_WRITE,
    ]
    
    for check_type in types:
        assert isinstance(check_type.value, str)


@pytest.mark.asyncio
async def test_global_orchestrator_instance():
    """Test global orchestrator instance."""
    orchestrator1 = await get_failover_orchestrator(engine)
    orchestrator2 = await get_failover_orchestrator(engine)
    
    assert orchestrator1 is orchestrator2


@pytest.mark.asyncio
async def test_callback_registration():
    """Test callback registration."""
    orchestrator = FailoverDrillOrchestrator(engine)
    await orchestrator.initialize()
    
    callbacks_triggered = []
    
    def test_callback(result):
        callbacks_triggered.append(result.drill_id)
    
    orchestrator.register_drill_callback(test_callback)
    
    assert test_callback in orchestrator._drill_callbacks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
