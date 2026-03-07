"""
Unit tests for Database Failover Drill Automation (#1424).

Tests failover scenarios, health checks, and drill orchestration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
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


class TestDatabaseEndpoint:
    """Test DatabaseEndpoint dataclass."""

    def test_basic_creation(self):
        """Test creating a database endpoint."""
        endpoint = DatabaseEndpoint(
            name="primary",
            host="db-primary.internal",
            port=5432,
            database="app",
            is_primary=True,
            priority=1,
        )
        
        assert endpoint.name == "primary"
        assert endpoint.host == "db-primary.internal"
        assert endpoint.is_primary is True
        assert endpoint.priority == 1

    def test_to_dict(self):
        """Test converting to dictionary."""
        endpoint = DatabaseEndpoint(
            name="replica",
            host="db-replica.internal",
            port=5432,
            database="app",
            is_replica=True,
            priority=2,
            is_available=True,
            last_checked=datetime(2026, 3, 7, 12, 0, 0),
        )
        
        result = endpoint.to_dict()
        
        assert result["name"] == "replica"
        assert result["is_replica"] is True
        assert result["last_checked"] == "2026-03-07T12:00:00"


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_basic_creation(self):
        """Test creating a health check result."""
        result = HealthCheckResult(
            check_type=HealthCheckType.CONNECTIVITY,
            endpoint="primary",
            passed=True,
            latency_ms=15.5,
            message="Connection successful",
        )
        
        assert result.check_type == HealthCheckType.CONNECTIVITY
        assert result.passed is True
        assert result.latency_ms == 15.5

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = HealthCheckResult(
            check_type=HealthCheckType.READ_WRITE,
            endpoint="primary",
            passed=False,
            latency_ms=100.0,
            message="Write failed",
            details={"error": "timeout"},
            timestamp=datetime(2026, 3, 7, 12, 0, 0),
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["check_type"] == "read_write"
        assert dict_result["passed"] is False
        assert dict_result["details"]["error"] == "timeout"


class TestFailoverDrillResult:
    """Test FailoverDrillResult dataclass."""

    def test_basic_creation(self):
        """Test creating a drill result."""
        result = FailoverDrillResult(
            drill_id="abc123",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.COMPLETED,
            started_at=datetime.utcnow(),
        )
        
        assert result.drill_id == "abc123"
        assert result.scenario == FailoverScenario.CONTROLLED_FAILOVER
        assert result.status == DrillStatus.COMPLETED

    def test_success_property(self):
        """Test success property calculation."""
        # Successful drill
        success_result = FailoverDrillResult(
            drill_id="test1",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.COMPLETED,
            started_at=datetime.utcnow(),
            pre_checks_passed=True,
            post_checks_passed=True,
        )
        assert success_result.success is True
        
        # Failed drill - status not completed
        failed_status = FailoverDrillResult(
            drill_id="test2",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.FAILED,
            started_at=datetime.utcnow(),
        )
        assert failed_status.success is False
        
        # Failed drill - pre-checks failed
        failed_preco = FailoverDrillResult(
            drill_id="test3",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.COMPLETED,
            started_at=datetime.utcnow(),
            pre_checks_passed=False,
            post_checks_passed=True,
        )
        assert failed_preco.success is False
        
        # Failed drill - post-checks failed
        failed_post = FailoverDrillResult(
            drill_id="test4",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.COMPLETED,
            started_at=datetime.utcnow(),
            pre_checks_passed=True,
            post_checks_passed=False,
        )
        assert failed_post.success is False

    def test_total_duration_ms(self):
        """Test total duration calculation."""
        start = datetime(2026, 3, 7, 12, 0, 0)
        end = datetime(2026, 3, 7, 12, 0, 30)  # 30 seconds
        
        result = FailoverDrillResult(
            drill_id="test",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.COMPLETED,
            started_at=start,
            completed_at=end,
        )
        
        assert result.total_duration_ms == 30000.0  # 30 seconds

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = FailoverDrillResult(
            drill_id="abc123",
            scenario=FailoverScenario.CONTROLLED_FAILOVER,
            status=DrillStatus.COMPLETED,
            started_at=datetime(2026, 3, 7, 12, 0, 0),
            completed_at=datetime(2026, 3, 7, 12, 0, 45),
            pre_checks_passed=True,
            post_checks_passed=True,
            failover_duration_ms=5000.0,
            rollback_duration_ms=3000.0,
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["drill_id"] == "abc123"
        assert dict_result["scenario"] == "controlled_failover"
        assert dict_result["success"] is True
        assert dict_result["total_duration_ms"] == 45000.0


class TestDrillSchedule:
    """Test DrillSchedule dataclass."""

    def test_default_schedule(self):
        """Test default schedule configuration."""
        schedule = DrillSchedule()
        
        assert schedule.enabled is False
        assert schedule.frequency_days == 30
        assert schedule.preferred_hour == 2
        assert schedule.auto_rollback is True
        assert len(schedule.scenarios) == 1

    def test_to_dict(self):
        """Test converting to dictionary."""
        schedule = DrillSchedule(
            enabled=True,
            frequency_days=14,
            scenarios=[FailoverScenario.CONTROLLED_FAILOVER, FailoverScenario.UNCONTROLLED_FAILOVER],
        )
        
        result = schedule.to_dict()
        
        assert result["enabled"] is True
        assert result["frequency_days"] == 14
        assert len(result["scenarios"]) == 2


class TestFailoverDrillOrchestratorInitialization:
    """Test FailoverDrillOrchestrator initialization."""

    def test_init_with_engine(self):
        """Test initialization with engine."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        assert orchestrator.engine == mock_engine
        assert len(orchestrator._endpoints) == 0
        assert len(orchestrator._drill_history) == 0

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test orchestrator initialization."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        with patch.object(orchestrator, '_ensure_history_tables') as mock_ensure:
            await orchestrator.initialize()
            mock_ensure.assert_called_once()


class TestEndpointManagement:
    """Test endpoint management."""

    def test_add_endpoint(self):
        """Test adding an endpoint."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        endpoint = DatabaseEndpoint(
            name="primary",
            host="db.internal",
            port=5432,
            database="app",
            is_primary=True,
        )
        
        orchestrator.add_endpoint(endpoint)
        
        assert "primary" in orchestrator._endpoints
        assert orchestrator._endpoints["primary"] == endpoint

    def test_remove_endpoint(self):
        """Test removing an endpoint."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        endpoint = DatabaseEndpoint(
            name="primary",
            host="db.internal",
            port=5432,
            database="app",
        )
        
        orchestrator.add_endpoint(endpoint)
        orchestrator.remove_endpoint("primary")
        
        assert "primary" not in orchestrator._endpoints

    def test_get_endpoints(self):
        """Test getting all endpoints."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        endpoint1 = DatabaseEndpoint("primary", "host1", 5432, "app")
        endpoint2 = DatabaseEndpoint("replica", "host2", 5432, "app")
        
        orchestrator.add_endpoint(endpoint1)
        orchestrator.add_endpoint(endpoint2)
        
        endpoints = orchestrator.get_endpoints()
        
        assert len(endpoints) == 2
        assert endpoint1 in endpoints
        assert endpoint2 in endpoints


class TestHealthChecks:
    """Test health check operations."""

    @pytest.mark.asyncio
    async def test_run_health_checks(self):
        """Test running health checks."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        # Add endpoint
        endpoint = DatabaseEndpoint("primary", "host1", 5432, "app")
        orchestrator.add_endpoint(endpoint)
        
        with patch('api.utils.failover_drill.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            checks = await orchestrator._run_health_checks("test")
            
            assert len(checks) > 0


class TestFailoverExecution:
    """Test failover execution."""

    @pytest.mark.asyncio
    async def test_execute_controlled_failover(self):
        """Test controlled failover execution."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        await orchestrator._execute_failover(FailoverScenario.CONTROLLED_FAILOVER)
        
        # Should complete without exception

    @pytest.mark.asyncio
    async def test_execute_uncontrolled_failover(self):
        """Test uncontrolled failover execution."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        await orchestrator._execute_failover(FailoverScenario.UNCONTROLLED_FAILOVER)

    @pytest.mark.asyncio
    async def test_execute_rollback(self):
        """Test rollback execution."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        await orchestrator._execute_rollback()


class TestDrillExecution:
    """Test full drill execution."""

    @pytest.mark.asyncio
    async def test_run_drill_success(self):
        """Test successful drill execution."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        # Mock health checks
        mock_checks = [
            HealthCheckResult(
                HealthCheckType.CONNECTIVITY, "primary", True, 10, "OK"
            )
        ]
        
        with patch.object(orchestrator, '_run_health_checks', return_value=mock_checks):
            with patch.object(orchestrator, '_execute_failover'):
                with patch.object(orchestrator, '_execute_rollback'):
                    with patch.object(orchestrator, '_record_drill_result'):
                        result = await orchestrator.run_drill(
                            scenario=FailoverScenario.CONTROLLED_FAILOVER,
                            auto_rollback=True,
                        )
                        
                        assert result.scenario == FailoverScenario.CONTROLLED_FAILOVER
                        assert result.pre_checks_passed is True
                        assert result.post_checks_passed is True

    @pytest.mark.asyncio
    async def test_run_drill_pre_check_failure(self):
        """Test drill with pre-check failure."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        # Mock failed health checks
        mock_checks = [
            HealthCheckResult(
                HealthCheckType.CONNECTIVITY, "primary", False, 0, "Failed"
            )
        ]
        
        with patch.object(orchestrator, '_run_health_checks', return_value=mock_checks):
            with patch.object(orchestrator, '_record_drill_result'):
                result = await orchestrator.run_drill(
                    scenario=FailoverScenario.CONTROLLED_FAILOVER,
                )
                
                assert result.status == DrillStatus.FAILED
                assert result.pre_checks_passed is False


class TestScheduleManagement:
    """Test schedule management."""

    def test_configure_schedule(self):
        """Test configuring schedule."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        schedule = DrillSchedule(
            enabled=True,
            frequency_days=14,
        )
        
        orchestrator.configure_schedule(schedule)
        
        assert orchestrator._schedule.enabled is True
        assert orchestrator._schedule.frequency_days == 14

    def test_get_schedule(self):
        """Test getting schedule."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        schedule = DrillSchedule(enabled=True)
        orchestrator.configure_schedule(schedule)
        
        retrieved = orchestrator.get_schedule()
        
        assert retrieved.enabled is True


class TestStatisticsAndHistory:
    """Test statistics and history tracking."""

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting statistics."""
        mock_engine = Mock()
        orchestrator = FailoverDrillOrchestrator(mock_engine)
        
        mock_results = [
            Mock(scalar=lambda: 10),   # total_drills
            Mock(scalar=lambda: 8),    # successful
            Mock(scalar=lambda: 2),    # failed
            Mock(scalar=lambda: 5000), # avg time
            Mock(scalar=lambda: 1),    # recent
        ]
        
        with patch('api.utils.failover_drill.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.execute.side_effect = mock_results
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            stats = await orchestrator.get_statistics()
            
            assert stats["total_drills"] == 10
            assert stats["successful_drills"] == 8
            assert stats["success_rate"] == 80.0


class TestEnums:
    """Test enum classes."""

    def test_failover_scenario_values(self):
        """Test failover scenario enum values."""
        assert FailoverScenario.CONTROLLED_FAILOVER.value == "controlled_failover"
        assert FailoverScenario.UNCONTROLLED_FAILOVER.value == "uncontrolled_failover"
        assert FailoverScenario.NETWORK_PARTITION.value == "network_partition"
        assert FailoverScenario.READ_REPLICA_PROMOTION.value == "read_replica_promotion"
        assert FailoverScenario.CONNECTION_POOL_EXHAUSTION.value == "connection_pool_exhaustion"
        assert FailoverScenario.PRIMARY_RESTART.value == "primary_restart"
        assert FailoverScenario.ROLLBACK_TEST.value == "rollback_test"

    def test_drill_status_values(self):
        """Test drill status enum values."""
        assert DrillStatus.PENDING.value == "pending"
        assert DrillStatus.IN_PROGRESS.value == "in_progress"
        assert DrillStatus.VALIDATING.value == "validating"
        assert DrillStatus.COMPLETED.value == "completed"
        assert DrillStatus.FAILED.value == "failed"
        assert DrillStatus.ROLLING_BACK.value == "rolling_back"
        assert DrillStatus.ROLLED_BACK.value == "rolled_back"

    def test_health_check_type_values(self):
        """Test health check type enum values."""
        assert HealthCheckType.CONNECTIVITY.value == "connectivity"
        assert HealthCheckType.REPLICATION.value == "replication"
        assert HealthCheckType.DATA_CONSISTENCY.value == "data_consistency"
        assert HealthCheckType.PERFORMANCE.value == "performance"
        assert HealthCheckType.READ_WRITE.value == "read_write"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
