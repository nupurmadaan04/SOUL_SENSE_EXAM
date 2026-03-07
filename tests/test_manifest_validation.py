"""
Comprehensive tests for Manifest Validation module.

Tests cover:
- Manifest parsing
- Validation rules
- Policy enforcement
- Resource validation
- Image scanning
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from backend.fastapi.api.utils.manifest_validation import (
    ManifestValidationManager,
    ValidationSeverity,
    ValidationStatus,
    ResourceType,
    PolicyRuleType,
    GoldenPolicy,
    ValidationRule,
    ManifestParser,
    ResourceValidator,
    get_validation_manager,
    reset_validation_manager
)


# Fixtures

def get_manager_sync():
    """Get validation manager synchronously."""
    reset_validation_manager()
    return asyncio.run(get_validation_manager())


@pytest.fixture
def validation_manager():
    """Fixture for validation manager."""
    manager = get_manager_sync()
    yield manager
    reset_validation_manager()


# Unit Tests

class TestValidationSeverity:
    """Test validation severity enums."""
    
    def test_severity_values(self):
        """Test that all severities have correct values."""
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationStatus:
    """Test validation status enums."""
    
    def test_status_values(self):
        """Test that all statuses have correct values."""
        assert ValidationStatus.PENDING.value == "pending"
        assert ValidationStatus.VALID.value == "valid"
        assert ValidationStatus.INVALID.value == "invalid"
        assert ValidationStatus.PARTIAL.value == "partial"


class TestResourceType:
    """Test resource type enums."""
    
    def test_resource_values(self):
        """Test that all resource types have correct values."""
        assert ResourceType.DEPLOYMENT.value == "Deployment"
        assert ResourceType.SERVICE.value == "Service"
        assert ResourceType.CONFIGMAP.value == "ConfigMap"


class TestManifestParser:
    """Test manifest parser."""
    
    def test_parse_yaml_single_document(self):
        """Test parsing single YAML document."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  ports:
  - port: 80
"""
        documents = ManifestParser.parse_yaml(yaml_content)
        
        assert len(documents) == 1
        assert documents[0]["kind"] == "Service"
        assert documents[0]["metadata"]["name"] == "my-service"
    
    def test_parse_yaml_multiple_documents(self):
        """Test parsing multiple YAML documents."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
"""
        documents = ManifestParser.parse_yaml(yaml_content)
        
        assert len(documents) == 2
        assert documents[0]["kind"] == "Service"
        assert documents[1]["kind"] == "Deployment"
    
    def test_parse_json(self):
        """Test parsing JSON manifest."""
        json_content = '{"apiVersion": "v1", "kind": "Service", "metadata": {"name": "my-service"}}'
        documents = ManifestParser.parse_json(json_content)
        
        assert len(documents) == 1
        assert documents[0]["kind"] == "Service"
    
    def test_calculate_hash(self):
        """Test manifest hash calculation."""
        content = '{"kind": "Service"}'
        hash1 = ManifestParser.calculate_hash(content)
        hash2 = ManifestParser.calculate_hash(content)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
    
    def test_get_resource_key(self):
        """Test resource key generation."""
        doc = {
            "kind": "Deployment",
            "metadata": {
                "name": "my-app",
                "namespace": "production"
            }
        }
        key = ManifestParser.get_resource_key(doc)
        
        assert key == "Deployment/production/my-app"


class TestResourceValidator:
    """Test resource validator."""
    
    def test_validate_required_labels_present(self):
        """Test validation when required labels are present."""
        doc = {
            "kind": "Deployment",
            "metadata": {
                "name": "my-app",
                "labels": {
                    "app": "my-app",
                    "version": "v1"
                }
            }
        }
        
        findings = ResourceValidator.validate_required_labels(
            doc, ["app", "version"]
        )
        
        assert len(findings) == 0
    
    def test_validate_required_labels_missing(self):
        """Test validation when required labels are missing."""
        doc = {
            "kind": "Deployment",
            "metadata": {
                "name": "my-app",
                "labels": {
                    "app": "my-app"
                }
            }
        }
        
        findings = ResourceValidator.validate_required_labels(
            doc, ["app", "version"]
        )
        
        assert len(findings) == 1
        assert findings[0].severity == ValidationSeverity.ERROR
        assert "version" in findings[0].message
    
    def test_validate_resource_limits_missing(self):
        """Test validation when resource limits are missing."""
        doc = {
            "kind": "Deployment",
            "metadata": {
                "name": "my-app"
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "app",
                                "image": "myapp:latest"
                            }
                        ]
                    }
                }
            }
        }
        
        findings = ResourceValidator.validate_resource_limits(doc)
        
        assert len(findings) >= 2  # CPU and memory limits missing
        assert all(f.severity == ValidationSeverity.ERROR for f in findings[:2])
    
    def test_validate_resource_limits_present(self):
        """Test validation when resource limits are present."""
        doc = {
            "kind": "Deployment",
            "metadata": {
                "name": "my-app"
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "app",
                                "image": "myapp:latest",
                                "resources": {
                                    "limits": {
                                        "cpu": "500m",
                                        "memory": "256Mi"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        findings = ResourceValidator.validate_resource_limits(doc)
        
        assert len(findings) == 0
    
    def test_validate_image_policy_latest_tag(self):
        """Test validation of 'latest' image tag."""
        doc = {
            "kind": "Deployment",
            "metadata": {
                "name": "my-app"
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "app",
                                "image": "myapp:latest"
                            }
                        ]
                    }
                }
            }
        }
        
        findings = ResourceValidator.validate_image_policy(
            doc, ["docker.io"], require_digest=False
        )
        
        latest_warnings = [f for f in findings if "latest" in f.message]
        assert len(latest_warnings) == 1
        assert latest_warnings[0].severity == ValidationSeverity.WARNING


class TestValidationManagerInitialization:
    """Test validation manager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, validation_manager):
        """Test that manager initializes correctly."""
        assert validation_manager._initialized is True
        assert "golden-policy-default" in validation_manager.policies


class TestPolicyManagement:
    """Test policy management."""
    
    @pytest.mark.asyncio
    async def test_create_policy(self, validation_manager):
        """Test creating a policy."""
        rules = [
            ValidationRule(
                rule_id="test-rule",
                name="Test Rule",
                description="Test rule",
                rule_type=PolicyRuleType.REQUIRED_LABELS,
                resource_types=[ResourceType.DEPLOYMENT],
                severity=ValidationSeverity.ERROR,
                parameters={"labels": ["app"]}
            )
        ]
        
        policy = await validation_manager.create_policy(
            name="Test Policy",
            description="Test policy description",
            rules=rules
        )
        
        assert policy.policy_id is not None
        assert policy.name == "Test Policy"
        assert len(policy.rules) == 1
    
    @pytest.mark.asyncio
    async def test_get_policy(self, validation_manager):
        """Test retrieving a policy."""
        policy = await validation_manager.get_policy("golden-policy-default")
        
        assert policy is not None
        assert policy.name == "Golden Deployment Policy"
        assert len(policy.rules) > 0


class TestManifestValidation:
    """Test manifest validation."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_manifest(self, validation_manager):
        """Test validating a valid manifest."""
        yaml_content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  labels:
    app: my-app
spec:
  ports:
  - port: 80
"""
        result = await validation_manager.validate_manifest(
            manifest_content=yaml_content,
            manifest_format="yaml",
            manifest_name="test-service"
        )
        
        assert result.validation_id is not None
        assert result.manifest_name == "test-service"
        assert result.status in [ValidationStatus.VALID, ValidationStatus.PARTIAL]
    
    @pytest.mark.asyncio
    async def test_validate_invalid_manifest(self, validation_manager):
        """Test validating an invalid manifest."""
        yaml_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
"""
        result = await validation_manager.validate_manifest(
            manifest_content=yaml_content,
            manifest_format="yaml",
            manifest_name="test-deployment"
        )
        
        assert result.validation_id is not None
        assert result.status in [ValidationStatus.INVALID, ValidationStatus.PARTIAL]
        assert result.error_count > 0
    
    @pytest.mark.asyncio
    async def test_get_validation_result(self, validation_manager):
        """Test getting validation result."""
        yaml_content = "apiVersion: v1\nkind: Service\nmetadata:\n  name: test"
        
        result = await validation_manager.validate_manifest(
            manifest_content=yaml_content,
            manifest_format="yaml"
        )
        
        retrieved = await validation_manager.get_validation_result(result.validation_id)
        
        assert retrieved is not None
        assert retrieved.validation_id == result.validation_id


class TestImageScanning:
    """Test image scanning."""
    
    @pytest.mark.asyncio
    async def test_scan_image(self, validation_manager):
        """Test scanning an image."""
        result = await validation_manager.scan_image(
            image_name="nginx",
            image_tag="latest"
        )
        
        assert result.image_name == "nginx"
        assert result.image_tag == "latest"
        assert result.scan_status in ["pending", "scanning", "completed"]


class TestStatistics:
    """Test statistics generation."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, validation_manager):
        """Test getting validation statistics."""
        stats = await validation_manager.get_statistics()
        
        assert "policies" in stats
        assert "validations" in stats
        assert "findings" in stats
        assert "images_scanned" in stats


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
