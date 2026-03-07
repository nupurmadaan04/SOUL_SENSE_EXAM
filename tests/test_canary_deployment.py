"""
Comprehensive tests for Canary Deployment module.

Tests cover:
- Deployment creation and management
- Rollout strategies
- Traffic splitting
- Health monitoring
- Promotion and rollback
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from backend.fastapi.api.utils.canary_deployment import (
    CanaryDeploymentManager,
    CanaryStatus,
    RolloutStrategy,
    MetricOperator,
    HealthStatus,
    CanaryDeployment,
    CanaryStep,
    MetricThreshold,
    HealthMetric,
    RolloutStrategyCalculator,
    HealthAnalyzer,
    get_canary_manager,
    reset_canary_manager
)


# Fixtures

def get_manager_sync():
    """Get canary manager synchronously."""
    reset_canary_manager()
    return asyncio.run(get_canary_manager())


@pytest.fixture
def canary_manager():
    """Fixture for canary manager."""
    manager = get_manager_sync()
    yield manager
    reset_canary_manager()


@pytest.fixture
def sample_deployment_data():
    """Sample deployment data for testing."""
    return {
        "name": "Test Canary",
        "description": "Test canary deployment",
        "service_name": "test-service",
        "canary_version": "v2.0.0",
        "baseline_version": "v1.0.0"
    }


# Unit Tests

class TestCanaryStatus:
    """Test canary status enums."""
    
    def test_status_values(self):
        """Test that all statuses have correct values."""
        assert CanaryStatus.PENDING.value == "pending"
        assert CanaryStatus.RUNNING.value == "running"
        assert CanaryStatus.PROMOTED.value == "promoted"
        assert CanaryStatus.ROLLED_BACK.value == "rolled_back"


class TestRolloutStrategy:
    """Test rollout strategy enums."""
    
    def test_strategy_values(self):
        """Test that all strategies have correct values."""
        assert RolloutStrategy.LINEAR.value == "linear"
        assert RolloutStrategy.EXPONENTIAL.value == "exponential"
        assert RolloutStrategy.CUSTOM.value == "custom"


class TestRolloutStrategyCalculator:
    """Test rollout strategy calculator."""
    
    def test_linear_steps(self):
        """Test linear step calculation."""
        weights = RolloutStrategyCalculator.calculate_linear_steps(
            num_steps=5,
            final_weight=100
        )
        
        assert len(weights) == 5
        assert weights == [20, 40, 60, 80, 100]
    
    def test_exponential_steps(self):
        """Test exponential step calculation."""
        weights = RolloutStrategyCalculator.calculate_exponential_steps(
            num_steps=5,
            final_weight=100,
            base=2.0
        )
        
        assert len(weights) == 5
        assert weights[0] == 2
        assert weights[1] == 4
        assert weights[2] == 8
        assert weights[4] == 100  # Capped at final_weight
    
    def test_generate_linear_steps(self):
        """Test generating linear canary steps."""
        steps = RolloutStrategyCalculator.generate_steps(
            strategy=RolloutStrategy.LINEAR,
            num_steps=3,
            step_duration=10
        )
        
        assert len(steps) == 3
        assert steps[0].canary_weight == 33
        assert steps[1].canary_weight == 67
        assert steps[2].canary_weight == 100
        assert steps[0].duration_minutes == 10


class TestHealthAnalyzer:
    """Test health analyzer."""
    
    def test_evaluate_metric_direct_threshold(self):
        """Test metric evaluation with direct threshold."""
        metric = HealthMetric(
            metric_name="error_rate",
            timestamp=datetime.utcnow(),
            canary_value=0.05
        )
        
        threshold = MetricThreshold(
            metric_name="error_rate",
            operator=MetricOperator.LESS_THAN,
            threshold_value=0.10
        )
        
        status = HealthAnalyzer.evaluate_metric(metric, threshold)
        assert status == HealthStatus.HEALTHY
    
    def test_evaluate_metric_baseline_comparison(self):
        """Test metric evaluation with baseline comparison."""
        metric = HealthMetric(
            metric_name="latency",
            timestamp=datetime.utcnow(),
            canary_value=105.0,
            baseline_value=100.0
        )
        
        threshold = MetricThreshold(
            metric_name="latency",
            operator=MetricOperator.LESS_THAN,
            threshold_value=0,  # Not used
            baseline_comparison=True,
            tolerance_percentage=10.0
        )
        
        status = HealthAnalyzer.evaluate_metric(metric, threshold)
        assert status == HealthStatus.HEALTHY  # 5% diff within 10% tolerance
    
    def test_analyze_deployment_healthy(self):
        """Test analyzing healthy deployment."""
        canary = CanaryDeployment(
            canary_id="test_123",
            name="Test",
            description="Test",
            service_name="svc",
            canary_version="v2",
            baseline_version="v1",
            status=CanaryStatus.RUNNING,
            metric_thresholds=[
                MetricThreshold(
                    metric_name="error_rate",
                    operator=MetricOperator.LESS_THAN,
                    threshold_value=0.10
                )
            ]
        )
        
        metrics = [
            HealthMetric(
                metric_name="error_rate",
                timestamp=datetime.utcnow(),
                canary_value=0.05
            )
        ]
        
        analysis = HealthAnalyzer.analyze_deployment(canary, metrics)
        
        assert analysis.recommendation == "continue"
        assert analysis.confidence_score > 0.8
        assert len(analysis.issues) == 0


class TestCanaryManagerInitialization:
    """Test canary manager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, canary_manager):
        """Test that manager initializes correctly."""
        assert canary_manager._initialized is True


class TestDeploymentCreation:
    """Test deployment creation."""
    
    @pytest.mark.asyncio
    async def test_create_deployment(self, canary_manager, sample_deployment_data):
        """Test creating a canary deployment."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        assert canary.canary_id is not None
        assert canary.name == sample_deployment_data["name"]
        assert canary.status == CanaryStatus.PENDING
        assert len(canary.steps) == 5  # Default 5 steps
    
    @pytest.mark.asyncio
    async def test_create_deployment_with_strategy(self, canary_manager):
        """Test creating deployment with specific strategy."""
        canary = await canary_manager.create_deployment(
            name="Test",
            description="Test",
            service_name="svc",
            canary_version="v2",
            baseline_version="v1",
            strategy=RolloutStrategy.EXPONENTIAL,
            num_steps=3
        )
        
        assert canary.strategy == RolloutStrategy.EXPONENTIAL
        assert len(canary.steps) == 3


class TestDeploymentLifecycle:
    """Test deployment lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_deployment(self, canary_manager, sample_deployment_data):
        """Test starting a deployment."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        started = await canary_manager.start_deployment(canary.canary_id)
        
        assert started is not None
        assert started.status == CanaryStatus.RUNNING
        assert started.started_at is not None
        assert started.current_step == 1
    
    @pytest.mark.asyncio
    async def test_advance_step(self, canary_manager, sample_deployment_data):
        """Test advancing deployment step."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        await canary_manager.start_deployment(canary.canary_id)
        
        advanced = await canary_manager.advance_step(canary.canary_id)
        
        assert advanced is not None
        assert advanced.current_step == 2
    
    @pytest.mark.asyncio
    async def test_promote_deployment(self, canary_manager, sample_deployment_data):
        """Test promoting a deployment."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        await canary_manager.start_deployment(canary.canary_id)
        
        promoted = await canary_manager.promote_deployment(canary.canary_id)
        
        assert promoted is not None
        assert promoted.status == CanaryStatus.PROMOTED
        assert promoted.canary_weight == 100
        assert promoted.baseline_weight == 0
    
    @pytest.mark.asyncio
    async def test_rollback_deployment(self, canary_manager, sample_deployment_data):
        """Test rolling back a deployment."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        await canary_manager.start_deployment(canary.canary_id)
        
        rolled_back = await canary_manager.rollback_deployment(
            canary.canary_id,
            reason="Test rollback"
        )
        
        assert rolled_back is not None
        assert rolled_back.status == CanaryStatus.ROLLED_BACK
        assert rolled_back.canary_weight == 0
        assert rolled_back.baseline_weight == 100
        assert rolled_back.failure_reason == "Test rollback"


class TestTrafficManagement:
    """Test traffic management."""
    
    @pytest.mark.asyncio
    async def test_update_traffic_split(self, canary_manager, sample_deployment_data):
        """Test updating traffic split."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        split = await canary_manager.update_traffic_split(
            canary_id=canary.canary_id,
            canary_percentage=50.0
        )
        
        assert split is not None
        assert split.canary_percentage == 50.0
        assert split.baseline_percentage == 50.0
        
        # Check canary updated
        updated = await canary_manager.get_deployment(canary.canary_id)
        assert updated.canary_weight == 50
        assert updated.baseline_weight == 50


class TestHealthMonitoring:
    """Test health monitoring."""
    
    @pytest.mark.asyncio
    async def test_record_metric(self, canary_manager, sample_deployment_data):
        """Test recording a health metric."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        metric = await canary_manager.record_metric(
            canary_id=canary.canary_id,
            metric_name="error_rate",
            canary_value=0.05,
            baseline_value=0.04,
            unit="percentage"
        )
        
        assert metric.metric_name == "error_rate"
        assert metric.canary_value == 0.05
        assert metric.baseline_value == 0.04
    
    @pytest.mark.asyncio
    async def test_analyze_health(self, canary_manager, sample_deployment_data):
        """Test health analysis."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        # Add threshold
        canary.metric_thresholds = [
            MetricThreshold(
                metric_name="error_rate",
                operator=MetricOperator.LESS_THAN,
                threshold_value=0.10
            )
        ]
        
        # Record metric
        await canary_manager.record_metric(
            canary_id=canary.canary_id,
            metric_name="error_rate",
            canary_value=0.05
        )
        
        analysis = await canary_manager.analyze_health(canary.canary_id)
        
        assert analysis is not None
        assert analysis.canary_id == canary.canary_id
        assert analysis.recommendation in ["continue", "pause", "rollback", "promote"]


class TestEventLogging:
    """Test event logging."""
    
    @pytest.mark.asyncio
    async def test_get_events(self, canary_manager, sample_deployment_data):
        """Test getting deployment events."""
        canary = await canary_manager.create_deployment(
            name=sample_deployment_data["name"],
            description=sample_deployment_data["description"],
            service_name=sample_deployment_data["service_name"],
            canary_version=sample_deployment_data["canary_version"],
            baseline_version=sample_deployment_data["baseline_version"]
        )
        
        events = await canary_manager.get_events(canary_id=canary.canary_id)
        
        assert len(events) > 0  # At least creation event


class TestStatistics:
    """Test statistics generation."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, canary_manager):
        """Test getting canary statistics."""
        stats = await canary_manager.get_statistics()
        
        assert "deployments" in stats
        assert "by_strategy" in stats
        assert "rollbacks" in stats
        assert "events" in stats


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
