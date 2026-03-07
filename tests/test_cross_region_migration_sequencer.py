"""
Tests for Cross-Region Migration Sequencer.

Covers sequencing logic, health checks, execution flow, and edge cases.
"""

import pytest
from datetime import datetime

from app.infra.cross_region_migration_sequencer import (
    CrossRegionMigrationSequencer,
    CrossRegionMigrationPlan,
    RegionDefinition,
    MigrationStatus,
    RegionStatus,
)


class TestRegionDefinition:
    """Tests for RegionDefinition dataclass."""
    
    def test_create_region(self):
        """Test creating a region definition."""
        region = RegionDefinition(
            name="us-east-1",
            database_url="postgresql://localhost/mydb",
            environment="production",
            priority=1,
        )
        
        assert region.name == "us-east-1"
        assert region.database_url == "postgresql://localhost/mydb"
        assert region.environment == "production"
        assert region.priority == 1
        assert region.replica_of is None
        assert region.timeout_seconds == 120
    
    def test_region_to_dict(self):
        """Test region serialization."""
        region = RegionDefinition(
            name="us-west-2",
            database_url="postgresql://localhost/mydb",
            replica_of="us-east-1",
        )
        
        data = region.to_dict()
        assert data["name"] == "us-west-2"
        assert data["replica_of"] == "us-east-1"


class TestCrossRegionMigrationPlan:
    """Tests for CrossRegionMigrationPlan dataclass."""
    
    def test_create_plan(self):
        """Test creating a migration plan."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="us-east-1", database_url="postgresql://localhost/db1"),
                RegionDefinition(name="us-west-2", database_url="postgresql://localhost/db2"),
            ],
        )
        
        assert plan.migration_version == "20260307_001"
        assert len(plan.regions) == 2
        assert plan.status == MigrationStatus.PENDING
        assert plan.started_at is None
    
    def test_plan_to_dict(self):
        """Test plan serialization."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="us-east-1", database_url="postgresql://localhost/db1"),
            ],
        )
        
        data = plan.to_dict()
        assert data["migration_version"] == "20260307_001"
        assert data["status"] == "pending"
        assert "created_at" in data


class TestExecutionOrderResolution:
    """Tests for topological sort of region dependencies."""
    
    def test_simple_linear_order(self):
        """Test simple linear dependency chain."""
        regions = [
            RegionDefinition(name="us-east-1", database_url="url1", priority=1),
            RegionDefinition(name="us-west-2", database_url="url2", priority=2, replica_of="us-east-1"),
            RegionDefinition(name="eu-west-1", database_url="url3", priority=3, replica_of="us-west-2"),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=regions,
            dependencies={
                "us-east-1": [],
                "us-west-2": ["us-east-1"],
                "eu-west-1": ["us-west-2"],
            }
        )
        
        sequencer = CrossRegionMigrationSequencer()
        order, error = sequencer.resolve_execution_order(plan)
        
        assert error is None
        assert len(order) == 3
        # Verify dependencies are satisfied in order
        # us-east-1 must come before us-west-2, us-west-2 before eu-west-1
        assert order.index("us-east-1") < order.index("us-west-2")
        assert order.index("us-west-2") < order.index("eu-west-1")
    
    def test_parallel_independent_regions(self):
        """Test execution order with independent regions."""
        regions = [
            RegionDefinition(name="us-east-1", database_url="url1", priority=1),
            RegionDefinition(name="us-west-2", database_url="url2", priority=2),
            RegionDefinition(name="eu-west-1", database_url="url3", priority=3),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=regions,
            dependencies={
                "us-east-1": [],
                "us-west-2": [],
                "eu-west-1": [],
            }
        )
        
        sequencer = CrossRegionMigrationSequencer()
        order, error = sequencer.resolve_execution_order(plan)
        
        assert error is None
        assert len(order) == 3
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        regions = [
            RegionDefinition(name="region-a", database_url="url1"),
            RegionDefinition(name="region-b", database_url="url2"),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=regions,
            dependencies={
                "region-a": ["region-b"],
                "region-b": ["region-a"],  # Circular!
            }
        )
        
        sequencer = CrossRegionMigrationSequencer()
        order, error = sequencer.resolve_execution_order(plan)
        
        assert error is not None
        assert "circular" in error.lower()
    
    def test_missing_dependency_target(self):
        """Test handling of missing dependency."""
        regions = [
            RegionDefinition(name="us-east-1", database_url="url1"),
            RegionDefinition(name="us-west-2", database_url="url2", replica_of="nonexistent"),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=regions,
            dependencies={
                "us-east-1": [],
                "us-west-2": ["nonexistent"],
            }
        )
        
        sequencer = CrossRegionMigrationSequencer()
        order, error = sequencer.resolve_execution_order(plan)
        
        # Should still resolve but order may not be as expected
        assert order is not None


class TestHealthCheck:
    """Tests for region health validation."""
    
    def test_health_check_with_invalid_url(self):
        """Test health check fails for bad database URL."""
        region = RegionDefinition(
            name="bad-region",
            database_url="postgresql://nonexistent-host:9999/db",
            timeout_seconds=1,
        )
        
        sequencer = CrossRegionMigrationSequencer()
        is_healthy, error = sequencer.validate_region_health(region)
        
        assert is_healthy is False
        assert error is not None
    
    def test_health_check_database_format(self):
        """Test health check respects database URL."""
        # Test with valid but unreachable SQLite (no network)
        region = RegionDefinition(
            name="local-db",
            database_url="sqlite:///nonexistent_db.db",
        )
        
        sequencer = CrossRegionMigrationSequencer()
        is_healthy, error = sequencer.validate_region_health(region)
        
        # SQLite should be "healthy" even if file doesn't exist (creates it)
        assert is_healthy is True


class TestCrossRegionExecution:
    """Tests for cross-region migration execution."""
    
    def test_execution_with_empty_regions(self):
        """Test execution with no regions."""
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=[],
        )
        
        sequencer = CrossRegionMigrationSequencer()
        result = sequencer.execute_cross_region_migration(plan)
        
        # Should complete (nothing to do)
        assert result.status in [MigrationStatus.COMPLETED, MigrationStatus.PENDING]
    
    def test_execution_single_region(self):
        """Test execution with single region."""
        regions = [
            RegionDefinition(name="local-db", database_url="sqlite:///:memory:"),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=regions,
            dependencies={"local-db": []},
        )
        
        sequencer = CrossRegionMigrationSequencer()
        result = sequencer.execute_cross_region_migration(plan)
        
        assert result.migration_version == "20260307_001"
        assert result.status == MigrationStatus.COMPLETED
        assert result.started_at is not None
    
    def test_execution_populates_timestamps(self):
        """Test that execution sets timestamps."""
        regions = [
            RegionDefinition(name="local-db", database_url="sqlite:///:memory:"),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=regions,
            dependencies={"local-db": []},
        )
        
        sequencer = CrossRegionMigrationSequencer()
        result = sequencer.execute_cross_region_migration(plan)
        
        assert result.created_at is not None
        assert result.started_at is not None
        assert result.completed_at is not None
    
    def test_execution_status_propagation(self):
        """Test that execution updates status."""
        regions = [
            RegionDefinition(name="local-db", database_url="sqlite:///:memory:"),
        ]
        
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=regions,
            dependencies={"local-db": []},
        )
        
        assert plan.status == MigrationStatus.PENDING
        
        sequencer = CrossRegionMigrationSequencer()
        result = sequencer.execute_cross_region_migration(plan)
        
        assert result.status != MigrationStatus.PENDING


class TestMigrationStatus:
    """Tests for migration status enum."""
    
    def test_status_values(self):
        """Test migration status values."""
        assert MigrationStatus.PENDING.value == "pending"
        assert MigrationStatus.IN_PROGRESS.value == "in_progress"
        assert MigrationStatus.COMPLETED.value == "completed"
        assert MigrationStatus.FAILED.value == "failed"
        assert MigrationStatus.ROLLED_BACK.value == "rolled_back"


class TestRegionStatus:
    """Tests for region step status enum."""
    
    def test_region_status_values(self):
        """Test region status values."""
        assert RegionStatus.PENDING.value == "pending"
        assert RegionStatus.HEALTH_CHECK.value == "health_check"
        assert RegionStatus.EXECUTING.value == "executing"
        assert RegionStatus.COMPLETED.value == "completed"
        assert RegionStatus.FAILED.value == "failed"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_plan_with_none_dependencies(self):
        """Test plan with None dependencies dict."""
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=[
                RegionDefinition(name="r1", database_url="sqlite:///:memory:"),
            ],
            dependencies=None,
        )
        
        sequencer = CrossRegionMigrationSequencer()
        # Should handle None gracefully
        order, error = sequencer.resolve_execution_order(plan)
        assert order is not None
    
    def test_region_with_empty_database_url(self):
        """Test region with empty database URL."""
        region = RegionDefinition(
            name="bad-region",
            database_url="",
        )
        
        sequencer = CrossRegionMigrationSequencer()
        is_healthy, error = sequencer.validate_region_health(region)
        
        assert is_healthy is False
        assert error is not None
    
    def test_plan_initiated_by_field(self):
        """Test plan tracks who initiated it."""
        plan = CrossRegionMigrationPlan(
            migration_version="test",
            regions=[],
            initiated_by="test_user",
        )
        
        assert plan.initiated_by == "test_user"
    
    def test_serialization_roundtrip(self):
        """Test plan can be serialized and inspected."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="r1", database_url="sqlite:///:memory:"),
            ],
            dependencies={"r1": []},
        )
        
        sequencer = CrossRegionMigrationSequencer()
        result = sequencer.execute_cross_region_migration(plan)
        
        # Should be serializable
        data = result.to_dict()
        assert isinstance(data, dict)
        assert "migration_version" in data
        assert "status" in data
