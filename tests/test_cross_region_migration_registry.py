"""
Tests for Cross-Region Migration Registry.

Covers persistence, state tracking, and query functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from app.infra.cross_region_migration_registry import CrossRegionMigrationRegistry
from app.infra.cross_region_migration_sequencer import (
    CrossRegionMigrationPlan,
    RegionDefinition,
    RegionalMigrationStep,
    MigrationStatus,
    RegionStatus,
)


class TestCrossRegionMigrationRegistry:
    """Tests for registry persistence and queries."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create temporary registry for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_registry.json"
            registry = CrossRegionMigrationRegistry(str(registry_path))
            yield registry
    
    def test_registry_initialization(self, temp_registry):
        """Test registry initializes with empty state."""
        assert temp_registry.data["migrations"] == []
        assert temp_registry.data["dependencies"] == {}
    
    def test_register_execution(self, temp_registry):
        """Test registering a new migration execution."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="us-east-1", database_url="db1"),
            ],
            initiated_by="test_user",
        )
        
        temp_registry.register_execution(plan)
        
        assert len(temp_registry.data["migrations"]) == 1
        record = temp_registry.data["migrations"][0]
        assert record["migration_version"] == "20260307_001"
        assert record["initiated_by"] == "test_user"
        assert record["regions"] == ["us-east-1"]
    
    def test_multiple_executions(self, temp_registry):
        """Test registering multiple migrations."""
        for i in range(3):
            plan = CrossRegionMigrationPlan(
                migration_version=f"20260307_00{i}",
                regions=[
                    RegionDefinition(name="us-east-1", database_url="db1"),
                ],
            )
            temp_registry.register_execution(plan)
        
        assert len(temp_registry.data["migrations"]) == 3
    
    def test_update_region_status(self, temp_registry):
        """Test updating regional migration step status."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="us-east-1", database_url="db1"),
            ],
        )
        
        temp_registry.register_execution(plan)
        
        step = RegionalMigrationStep(
            region_name="us-east-1",
            migration_version="20260307_001",
            status=RegionStatus.COMPLETED,
            duration_seconds=5.2,
        )
        
        temp_registry.update_region_status("20260307_001", "us-east-1", step)
        
        record = temp_registry.data["migrations"][0]
        assert len(record["steps"]) == 1
        assert record["steps"][0]["region_name"] == "us-east-1"
        assert record["steps"][0]["status"] == "completed"
    
    def test_get_execution_history_all(self, temp_registry):
        """Test retrieving all execution history."""
        for i in range(3):
            plan = CrossRegionMigrationPlan(
                migration_version=f"20260307_00{i}",
                regions=[],
            )
            temp_registry.register_execution(plan)
        
        history = temp_registry.get_execution_history()
        assert len(history) == 3
    
    def test_get_execution_history_filtered(self, temp_registry):
        """Test retrieving specific migration history."""
        for i in range(3):
            plan = CrossRegionMigrationPlan(
                migration_version=f"20260307_00{i}",
                regions=[],
            )
            temp_registry.register_execution(plan)
        
        # Register same version twice
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[],
        )
        temp_registry.register_execution(plan)
        
        history = temp_registry.get_execution_history("20260307_001")
        assert len(history) == 2  # Same version registered twice
    
    def test_get_last_migration(self, temp_registry):
        """Test getting the most recent migration."""
        # Empty registry
        last = temp_registry.get_last_migration()
        assert last is None
        
        # Add migration
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[],
        )
        temp_registry.register_execution(plan)
        
        last = temp_registry.get_last_migration()
        assert last["migration_version"] == "20260307_001"
    
    def test_is_migration_safe_to_retry_never_attempted(self, temp_registry):
        """Test retry safety for never-attempted migration."""
        is_safe, reason = temp_registry.is_migration_safe_to_retry("never_run")
        assert is_safe is True
        assert reason is None
    
    def test_is_migration_safe_to_retry_completed(self, temp_registry):
        """Test retry safety for completed migration."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[],
            status=MigrationStatus.COMPLETED,
        )
        temp_registry.register_execution(plan)
        
        is_safe, reason = temp_registry.is_migration_safe_to_retry("20260307_001")
        assert is_safe is False
        assert "already completed" in reason.lower()
    
    def test_is_migration_safe_to_retry_failed(self, temp_registry):
        """Test retry safety for failed migration."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[],
            status=MigrationStatus.FAILED,
        )
        temp_registry.register_execution(plan)
        
        is_safe, reason = temp_registry.is_migration_safe_to_retry("20260307_001")
        assert is_safe is True
    
    def test_is_migration_safe_to_retry_in_progress(self, temp_registry):
        """Test retry safety for in-progress migration."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[],
            status=MigrationStatus.IN_PROGRESS,
        )
        temp_registry.register_execution(plan)
        
        is_safe, reason = temp_registry.is_migration_safe_to_retry("20260307_001")
        assert is_safe is False
        assert "in progress" in reason.lower()
    
    def test_get_failed_regions_no_migration(self, temp_registry):
        """Test getting failed regions for nonexistent migration."""
        failed = temp_registry.get_failed_regions("nonexistent")
        assert failed == []
    
    def test_get_failed_regions_with_failures(self, temp_registry):
        """Test getting failed regions from migration."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="us-east-1", database_url="db1"),
                RegionDefinition(name="us-west-2", database_url="db2"),
            ],
        )
        temp_registry.register_execution(plan)
        
        # Add failed step
        step_failed = RegionalMigrationStep(
            region_name="us-east-1",
            migration_version="20260307_001",
            status=RegionStatus.FAILED,
            error_message="Test error",
        )
        temp_registry.update_region_status("20260307_001", "us-east-1", step_failed)
        
        # Add successful step
        step_ok = RegionalMigrationStep(
            region_name="us-west-2",
            migration_version="20260307_001",
            status=RegionStatus.COMPLETED,
        )
        temp_registry.update_region_status("20260307_001", "us-west-2", step_ok)
        
        failed = temp_registry.get_failed_regions("20260307_001")
        assert failed == ["us-east-1"]
    
    def test_store_and_get_dependency_graph(self, temp_registry):
        """Test storing and retrieving dependency graph."""
        deps = {
            "us-east-1": [],
            "us-west-2": ["us-east-1"],
            "eu-west-1": ["us-east-1"],
        }
        
        temp_registry.store_dependency_graph(deps)
        retrieved = temp_registry.get_dependency_graph()
        
        assert retrieved == deps
    
    def test_persistence_to_file(self):
        """Test that registry persists to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_registry.json"
            
            # Create registry and add data
            registry1 = CrossRegionMigrationRegistry(str(registry_path))
            plan = CrossRegionMigrationPlan(
                migration_version="20260307_001",
                regions=[],
            )
            registry1.register_execution(plan)
            
            # Load from persisted file
            registry2 = CrossRegionMigrationRegistry(str(registry_path))
            history = registry2.get_execution_history()
            
            assert len(history) == 1
            assert history[0]["migration_version"] == "20260307_001"
    
    def test_registry_file_format(self):
        """Test registry JSON file format is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_registry.json"
            
            registry = CrossRegionMigrationRegistry(str(registry_path))
            plan = CrossRegionMigrationPlan(
                migration_version="20260307_001",
                regions=[],
            )
            registry.register_execution(plan)
            
            # Verify JSON is valid
            with open(registry_path, 'r') as f:
                data = json.load(f)
            
            assert "migrations" in data
            assert isinstance(data["migrations"], list)
            assert len(data["migrations"]) == 1
    
    def test_multiple_region_steps_update(self, temp_registry):
        """Test updating multiple regions in one migration."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="r1", database_url="db1"),
                RegionDefinition(name="r2", database_url="db2"),
                RegionDefinition(name="r3", database_url="db3"),
            ],
        )
        temp_registry.register_execution(plan)
        
        # Update each region
        for region_name in ["r1", "r2", "r3"]:
            step = RegionalMigrationStep(
                region_name=region_name,
                migration_version="20260307_001",
                status=RegionStatus.COMPLETED,
            )
            temp_registry.update_region_status("20260307_001", region_name, step)
        
        record = temp_registry.data["migrations"][0]
        assert len(record["steps"]) == 3


class TestRegistryEdgeCases:
    """Tests for edge cases in registry."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create temporary registry for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "test_registry.json"
            registry = CrossRegionMigrationRegistry(str(registry_path))
            yield registry
    
    def test_update_nonexistent_migration(self, temp_registry):
        """Test updating status for nonexistent migration."""
        step = RegionalMigrationStep(
            region_name="region-a",
            migration_version="nonexistent",
            status=RegionStatus.COMPLETED,
        )
        
        # Should not raise, just log warning
        temp_registry.update_region_status("nonexistent", "region-a", step)
        assert len(temp_registry.data["migrations"]) == 0
    
    def test_repeated_region_step_update(self, temp_registry):
        """Test updating same region step multiple times."""
        plan = CrossRegionMigrationPlan(
            migration_version="20260307_001",
            regions=[
                RegionDefinition(name="r1", database_url="db1"),
            ],
        )
        temp_registry.register_execution(plan)
        
        # Update same region multiple times
        for status in [RegionStatus.HEALTH_CHECK, RegionStatus.EXECUTING, RegionStatus.COMPLETED]:
            step = RegionalMigrationStep(
                region_name="r1",
                migration_version="20260307_001",
                status=status,
            )
            temp_registry.update_region_status("20260307_001", "r1", step)
        
        record = temp_registry.data["migrations"][0]
        assert len(record["steps"]) == 1
        assert record["steps"][0]["status"] == "completed"
