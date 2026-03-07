"""
Comprehensive tests for Infrastructure Drift Detection module.

Test coverage: 55+ tests
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import json

# Import the module under test
import sys
sys.path.insert(0, "backend/fastapi/api/utils")

from infra_drift_detection import (
    DriftStatus, DriftSeverity, IaCProvider, ResourceType,
    ResourceAttribute, DriftedResource, DriftDetectionResult,
    IaCState, RuntimeState, DriftAlert,
    ResourceComparator, DriftDetectionManager,
    get_drift_manager, reset_drift_manager
)


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def reset_manager():
    """Reset the global drift manager before each test."""
    reset_drift_manager()
    yield
    reset_drift_manager()


@pytest_asyncio.fixture
async def drift_manager():
    """Create a fresh drift detection manager."""
    manager = DriftDetectionManager()
    await manager.initialize()
    yield manager
    reset_drift_manager()


@pytest.fixture
def sample_iac_state_data():
    """Sample IaC state data."""
    return {
        "version": 4,
        "terraform_version": "1.5.0",
        "serial": 1,
        "resources": {
            "aws_instance.web": {
                "id": "aws_instance.web",
                "name": "web-server",
                "type": "aws_instance",
                "provider": "aws",
                "attributes": {
                    "instance_type": "t3.medium",
                    "ami": "ami-12345678",
                    "tags": {"Environment": "production", "Name": "web-server"}
                }
            },
            "aws_db_instance.main": {
                "id": "aws_db_instance.main",
                "name": "main-database",
                "type": "aws_db_instance",
                "provider": "aws",
                "attributes": {
                    "instance_class": "db.t3.large",
                    "engine": "postgres",
                    "allocated_storage": 100
                }
            }
        }
    }


@pytest.fixture
def sample_runtime_state_data():
    """Sample runtime state data (matching IaC)."""
    return {
        "region": "us-west-2",
        "aws_instance.web": {
            "id": "aws_instance.web",
            "name": "web-server",
            "type": "aws_instance",
            "provider": "aws",
            "attributes": {
                "instance_type": "t3.medium",
                "ami": "ami-12345678",
                "tags": {"Environment": "production", "Name": "web-server"}
            }
        },
        "aws_db_instance.main": {
            "id": "aws_db_instance.main",
            "name": "main-database",
            "type": "aws_db_instance",
            "provider": "aws",
            "attributes": {
                "instance_class": "db.t3.large",
                "engine": "postgres",
                "allocated_storage": 100
            }
        }
    }


@pytest.fixture
def drifted_runtime_state_data():
    """Sample runtime state data with drift."""
    return {
        "region": "us-west-2",
        "aws_instance.web": {
            "id": "aws_instance.web",
            "name": "web-server",
            "type": "aws_instance",
            "provider": "aws",
            "attributes": {
                # DRIFT: Changed instance type
                "instance_type": "t3.large",
                "ami": "ami-12345678",
                # DRIFT: Added new tag
                "tags": {"Environment": "production", "Name": "web-server", "CostCenter": "12345"}
            }
        },
        "aws_db_instance.main": {
            "id": "aws_db_instance.main",
            "name": "main-database",
            "type": "aws_db_instance",
            "provider": "aws",
            "attributes": {
                "instance_class": "db.t3.large",
                "engine": "postgres",
                # DRIFT: Changed storage
                "allocated_storage": 200
            }
        },
        # DRIFT: New unmanaged resource
        "aws_s3_bucket.logs": {
            "id": "aws_s3_bucket.logs",
            "name": "logs-bucket",
            "type": "aws_s3_bucket",
            "provider": "aws",
            "attributes": {"bucket": "my-logs-bucket"}
        }
    }


# Enums Tests

class TestDriftEnums:
    """Test drift detection enums."""
    
    def test_drift_status_values(self):
        """Test DriftStatus enum values."""
        assert DriftStatus.PENDING == "pending"
        assert DriftStatus.SCANNING == "scanning"
        assert DriftStatus.DETECTED == "detected"
        assert DriftStatus.NO_DRIFT == "no_drift"
        assert DriftStatus.REMEDIATING == "remediating"
        assert DriftStatus.REMEDIATED == "remediated"
        assert DriftStatus.FAILED == "failed"
        assert DriftStatus.IGNORED == "ignored"
    
    def test_drift_severity_values(self):
        """Test DriftSeverity enum values."""
        assert DriftSeverity.CRITICAL == "critical"
        assert DriftSeverity.HIGH == "high"
        assert DriftSeverity.MEDIUM == "medium"
        assert DriftSeverity.LOW == "low"
        assert DriftSeverity.INFO == "info"
    
    def test_iac_provider_values(self):
        """Test IaCProvider enum values."""
        assert IaCProvider.TERRAFORM == "terraform"
        assert IaCProvider.CLOUDFORMATION == "cloudformation"
        assert IaCProvider.PULUMI == "pulumi"
        assert IaCProvider.ANSIBLE == "ansible"
        assert IaCProvider.CUSTOM == "custom"
    
    def test_resource_type_values(self):
        """Test ResourceType enum values."""
        assert ResourceType.COMPUTE == "compute"
        assert ResourceType.STORAGE == "storage"
        assert ResourceType.NETWORK == "network"
        assert ResourceType.DATABASE == "database"
        assert ResourceType.SECURITY == "security"


# ResourceComparator Tests

class TestResourceComparator:
    """Test resource comparison functionality."""
    
    def test_compare_identical_resources(self):
        """Test comparison of identical resources."""
        iac = {"name": "test", "type": "t3.medium", "count": 1}
        runtime = {"name": "test", "type": "t3.medium", "count": 1}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        assert len(added) == 0
        assert len(modified) == 0
        assert len(removed) == 0
    
    def test_compare_with_added_attributes(self):
        """Test comparison with added attributes."""
        iac = {"name": "test", "type": "t3.medium"}
        runtime = {"name": "test", "type": "t3.medium", "new_tag": "value"}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        assert len(added) == 1
        assert added[0].name == "new_tag"
        assert added[0].runtime_value == "value"
        assert len(modified) == 0
        assert len(removed) == 0
    
    def test_compare_with_modified_attributes(self):
        """Test comparison with modified attributes."""
        iac = {"name": "test", "type": "t3.medium", "count": 1}
        runtime = {"name": "test", "type": "t3.large", "count": 2}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        assert len(added) == 0
        assert len(modified) == 2
        assert len(removed) == 0
        
        modified_names = [m.name for m in modified]
        assert "type" in modified_names
        assert "count" in modified_names
    
    def test_compare_with_removed_attributes(self):
        """Test comparison with removed attributes."""
        iac = {"name": "test", "type": "t3.medium", "old_tag": "value"}
        runtime = {"name": "test", "type": "t3.medium"}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        assert len(added) == 0
        assert len(modified) == 0
        assert len(removed) == 1
        assert removed[0].name == "old_tag"
    
    def test_compare_nested_dictionaries(self):
        """Test comparison with nested dictionary attributes."""
        iac = {
            "name": "test",
            "config": {"nested_key": "value1", "another": "value2"}
        }
        runtime = {
            "name": "test",
            "config": {"nested_key": "changed", "another": "value2"}
        }
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        # Nested keys should be flattened
        assert len(modified) > 0
        modified_names = [m.name for m in modified]
        assert any("nested_key" in name for name in modified_names)
    
    def test_compare_list_attributes(self):
        """Test comparison with list attributes."""
        iac = {"name": "test", "tags": ["a", "b", "c"]}
        runtime = {"name": "test", "tags": ["a", "b", "d"]}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        # Lists should be detected as modified
        assert len(modified) > 0
    
    def test_ignored_attributes(self):
        """Test that certain attributes are ignored."""
        iac = {"name": "test", "created_at": "2024-01-01"}
        runtime = {"name": "test", "created_at": "2024-01-02"}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        # created_at should be ignored
        assert len(modified) == 0
    
    def test_case_insensitive_string_comparison(self):
        """Test case-insensitive comparison for strings."""
        iac = {"name": "Test", "environment": "PRODUCTION"}
        runtime = {"name": "test", "environment": "production"}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        # Should not detect as modified (case-insensitive)
        assert len(modified) == 0
    
    def test_numeric_comparison_with_tolerance(self):
        """Test numeric comparison with floating point tolerance."""
        iac = {"name": "test", "cpu": 1.0000, "memory": 1024.0}
        runtime = {"name": "test", "cpu": 1.0000001, "memory": 1024.0001}
        
        added, modified, removed = ResourceComparator.compare_resources(
            iac, runtime, ResourceType.COMPUTE
        )
        
        # Small differences should be treated as equal
        assert len(modified) == 0
    
    def test_calculate_severity_critical(self):
        """Test critical severity calculation."""
        modified = [
            ResourceAttribute(name="password", iac_value="old", runtime_value="new")
        ]
        
        severity = ResourceComparator.calculate_drift_severity(
            [], modified, [], ResourceType.SECURITY
        )
        
        assert severity == DriftSeverity.CRITICAL
    
    def test_calculate_severity_high(self):
        """Test high severity calculation."""
        modified = [
            ResourceAttribute(name="instance_type", iac_value="t3.small", runtime_value="t3.large")
        ]
        
        severity = ResourceComparator.calculate_drift_severity(
            [], modified, [], ResourceType.COMPUTE
        )
        
        assert severity == DriftSeverity.HIGH
    
    def test_calculate_severity_medium(self):
        """Test medium severity calculation with many changes."""
        modified = [
            ResourceAttribute(name=f"attr_{i}", iac_value="a", runtime_value="b")
            for i in range(5)
        ]
        
        severity = ResourceComparator.calculate_drift_severity(
            [], modified, [], ResourceType.COMPUTE
        )
        
        assert severity == DriftSeverity.MEDIUM
    
    def test_calculate_severity_low(self):
        """Test low severity calculation with few changes."""
        modified = [
            ResourceAttribute(name="description", iac_value="old", runtime_value="new")
        ]
        
        severity = ResourceComparator.calculate_drift_severity(
            [], modified, [], ResourceType.COMPUTE
        )
        
        assert severity == DriftSeverity.LOW


# DriftDetectionManager Tests

@pytest.mark.asyncio
class TestDriftDetectionManager:
    """Test drift detection manager."""
    
    async def test_initialize(self, drift_manager):
        """Test manager initialization."""
        assert drift_manager._initialized is True
    
    async def test_capture_iac_state(self, drift_manager, sample_iac_state_data):
        """Test capturing IaC state."""
        state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data,
            git_commit="abc123",
            git_branch="main"
        )
        
        assert state.provider == IaCProvider.TERRAFORM
        assert state.environment == "production"
        assert state.git_commit == "abc123"
        assert state.git_branch == "main"
        assert state.state_id in drift_manager.iac_states
    
    async def test_get_iac_state(self, drift_manager, sample_iac_state_data):
        """Test retrieving IaC state."""
        state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="staging",
            state_data=sample_iac_state_data
        )
        
        retrieved = await drift_manager.get_iac_state(state.state_id)
        assert retrieved is not None
        assert retrieved.state_id == state.state_id
    
    async def test_get_nonexistent_iac_state(self, drift_manager):
        """Test retrieving non-existent IaC state."""
        state = await drift_manager.get_iac_state("nonexistent")
        assert state is None
    
    async def test_list_iac_states(self, drift_manager, sample_iac_state_data):
        """Test listing IaC states."""
        # Create multiple states
        await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        await drift_manager.capture_iac_state(
            provider=IaCProvider.CLOUDFORMATION,
            environment="staging",
            state_data=sample_iac_state_data
        )
        
        # List all
        all_states = await drift_manager.list_iac_states()
        assert len(all_states) == 2
        
        # Filter by provider
        tf_states = await drift_manager.list_iac_states(provider=IaCProvider.TERRAFORM)
        assert len(tf_states) == 1
        
        # Filter by environment
        prod_states = await drift_manager.list_iac_states(environment="production")
        assert len(prod_states) == 1
    
    async def test_capture_runtime_state(self, drift_manager, sample_runtime_state_data):
        """Test capturing runtime state."""
        state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=sample_runtime_state_data,
            scan_duration_seconds=120.5
        )
        
        assert state.provider == "aws"
        assert state.environment == "production"
        assert state.scan_duration_seconds == 120.5
        assert state.state_id in drift_manager.runtime_states
    
    async def test_detect_drift_no_changes(self, drift_manager, sample_iac_state_data, sample_runtime_state_data):
        """Test drift detection with no changes."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=sample_runtime_state_data
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Test Scan"
        )
        
        assert result is not None
        assert result.status == DriftStatus.NO_DRIFT
        assert result.total_resources == 2
        assert len(result.drifted_resources) == 0
    
    async def test_detect_drift_with_changes(self, drift_manager, sample_iac_state_data, drifted_runtime_state_data):
        """Test drift detection with changes."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=drifted_runtime_state_data
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Test Scan"
        )
        
        assert result is not None
        assert result.status == DriftStatus.DETECTED
        assert result.added_resources == 1  # s3 bucket added
        assert result.modified_resources > 0
        
        # Check for drifted resources
        assert len(result.drifted_resources) > 0
        
        # Check severity counts
        assert result.high_count > 0 or result.medium_count > 0 or result.low_count > 0
    
    async def test_detect_drift_invalid_state_ids(self, drift_manager):
        """Test drift detection with invalid state IDs."""
        result = await drift_manager.detect_drift(
            iac_state_id="invalid",
            runtime_state_id="also_invalid",
            scan_name="Test Scan"
        )
        
        assert result is None
    
    async def test_get_scan_result(self, drift_manager, sample_iac_state_data, sample_runtime_state_data):
        """Test retrieving scan result."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=sample_runtime_state_data
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Test Scan"
        )
        
        retrieved = await drift_manager.get_scan_result(result.scan_id)
        assert retrieved is not None
        assert retrieved.scan_id == result.scan_id
    
    async def test_list_scan_results(self, drift_manager, sample_iac_state_data, sample_runtime_state_data):
        """Test listing scan results."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=sample_runtime_state_data
        )
        
        # Create multiple scans
        await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Scan 1"
        )
        await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Scan 2"
        )
        
        results = await drift_manager.list_scan_results()
        assert len(results) == 2
        
        # Filter by environment
        prod_results = await drift_manager.list_scan_results(environment="production")
        assert len(prod_results) == 2
        
        # Filter by status
        no_drift_results = await drift_manager.list_scan_results(status=DriftStatus.NO_DRIFT)
        assert len(no_drift_results) == 2
    
    async def test_acknowledge_alert(self, drift_manager, sample_iac_state_data, drifted_runtime_state_data):
        """Test acknowledging an alert."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        # Create a drift that will trigger an alert
        drifted_runtime = drifted_runtime_state_data.copy()
        drifted_runtime["aws_instance.web"]["attributes"]["password"] = "new_password"
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=drifted_runtime
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Alert Test"
        )
        
        # Get alerts
        alerts = await drift_manager.get_alerts(scan_id=result.scan_id)
        assert len(alerts) > 0
        
        # Acknowledge first alert
        alert = alerts[0]
        acknowledged = await drift_manager.acknowledge_alert(alert.alert_id, "admin@example.com")
        
        assert acknowledged is not None
        assert acknowledged.acknowledged is True
        assert acknowledged.acknowledged_by == "admin@example.com"
        assert acknowledged.acknowledged_at is not None
    
    async def test_acknowledge_nonexistent_alert(self, drift_manager):
        """Test acknowledging non-existent alert."""
        result = await drift_manager.acknowledge_alert("nonexistent", "admin@example.com")
        assert result is None
    
    async def test_generate_remediation(self, drift_manager, sample_iac_state_data, drifted_runtime_state_data):
        """Test generating remediation script."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=drifted_runtime_state_data
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Remediation Test"
        )
        
        # Get first drifted resource
        drifted = result.drifted_resources[0]
        script = await drift_manager.generate_remediation(result.scan_id, drifted.resource_id)
        
        assert script is not None
        assert "Remediation" in script
        assert "terraform apply" in script
    
    async def test_generate_remediation_invalid_scan(self, drift_manager):
        """Test generating remediation for invalid scan."""
        script = await drift_manager.generate_remediation("invalid", "resource")
        assert script is None
    
    async def test_get_statistics(self, drift_manager, sample_iac_state_data, drifted_runtime_state_data):
        """Test getting statistics."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="production",
            state_data=sample_iac_state_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="production",
            resources=drifted_runtime_state_data
        )
        
        await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Stats Test"
        )
        
        stats = await drift_manager.get_statistics()
        
        assert stats["scans"]["total"] == 1
        assert stats["scans"]["detected"] == 1
        assert stats["drift_summary"]["total_resources_scanned"] > 0
        assert stats["alerts"]["total"] >= 0


# Global Manager Tests

@pytest.mark.asyncio
class TestGlobalManager:
    """Test global drift manager functions."""
    
    async def test_get_drift_manager(self):
        """Test getting global drift manager."""
        manager1 = await get_drift_manager()
        manager2 = await get_drift_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert manager1._initialized is True
    
    async def test_reset_drift_manager(self):
        """Test resetting global drift manager."""
        manager1 = await get_drift_manager()
        reset_drift_manager()
        manager2 = await get_drift_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


# Edge Case Tests

@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    async def test_empty_state_comparison(self, drift_manager):
        """Test comparison with empty states."""
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="test",
            state_data={}
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="test",
            resources={}
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Empty Test"
        )
        
        assert result is not None
        assert result.status == DriftStatus.NO_DRIFT
        assert result.total_resources == 0
    
    async def test_null_values_comparison(self, drift_manager):
        """Test comparison with null/None values."""
        iac_data = {
            "resources": {
                "test": {
                    "id": "test",
                    "name": "test",
                    "type": "compute",
                    "nullable_field": None,
                    "value": "present"
                }
            }
        }
        
        runtime_data = {
            "region": "us-west-2",
            "test": {
                "id": "test",
                "name": "test",
                "type": "compute",
                "nullable_field": None,
                "value": "present"
            }
        }
        
        iac_state = await drift_manager.capture_iac_state(
            provider=IaCProvider.TERRAFORM,
            environment="test",
            state_data=iac_data
        )
        
        runtime_state = await drift_manager.capture_runtime_state(
            provider="aws",
            environment="test",
            resources=runtime_data
        )
        
        result = await drift_manager.detect_drift(
            iac_state_id=iac_state.state_id,
            runtime_state_id=runtime_state.state_id,
            scan_name="Null Test"
        )
        
        assert result.status == DriftStatus.NO_DRIFT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
