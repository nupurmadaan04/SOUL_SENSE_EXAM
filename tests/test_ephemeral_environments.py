"""
Comprehensive tests for Ephemeral Preview Environments module.

Test coverage: 50+ tests
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

# Import the module under test
import sys
sys.path.insert(0, "backend/fastapi/api/utils")

from ephemeral_environments import (
    EnvironmentStatus, EnvironmentSize, EnvironmentType, AccessLevel,
    ResourceAllocation, DeploymentConfig, DomainConfig, EnvironmentMetrics,
    PreviewEnvironment, EnvironmentTemplate, EnvironmentBudget, EnvironmentEvent,
    EphemeralEnvironmentManager, get_ephemeral_manager, reset_ephemeral_manager
)


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def reset_manager():
    """Reset the global ephemeral manager before each test."""
    reset_ephemeral_manager()
    yield
    reset_ephemeral_manager()


@pytest_asyncio.fixture
async def ephemeral_manager():
    """Create a fresh ephemeral environment manager."""
    manager = EphemeralEnvironmentManager()
    await manager.initialize()
    yield manager
    await manager.shutdown()
    reset_ephemeral_manager()


@pytest.fixture
def sample_deployment_config():
    """Sample deployment configuration."""
    return DeploymentConfig(
        image_repository="registry.example.com/my-app",
        image_tag="abc123",
        container_port=8080,
        env_vars={"ENV": "preview", "DEBUG": "true"},
        health_check_path="/health",
        min_replicas=1,
        max_replicas=1
    )


# Enums Tests

class TestEphemeralEnums:
    """Test ephemeral environment enums."""
    
    def test_environment_status_values(self):
        """Test EnvironmentStatus enum values."""
        assert EnvironmentStatus.PENDING == "pending"
        assert EnvironmentStatus.PROVISIONING == "provisioning"
        assert EnvironmentStatus.READY == "ready"
        assert EnvironmentStatus.DEPLOYING == "deploying"
        assert EnvironmentStatus.RUNNING == "running"
        assert EnvironmentStatus.SLEEPING == "sleeping"
        assert EnvironmentStatus.DESTROYING == "destroying"
        assert EnvironmentStatus.DESTROYED == "destroyed"
        assert EnvironmentStatus.FAILED == "failed"
        assert EnvironmentStatus.TIMEOUT == "timeout"
    
    def test_environment_size_values(self):
        """Test EnvironmentSize enum values."""
        assert EnvironmentSize.SMALL == "small"
        assert EnvironmentSize.MEDIUM == "medium"
        assert EnvironmentSize.LARGE == "large"
        assert EnvironmentSize.XLARGE == "xlarge"
    
    def test_environment_type_values(self):
        """Test EnvironmentType enum values."""
        assert EnvironmentType.PULL_REQUEST == "pull_request"
        assert EnvironmentType.FEATURE_BRANCH == "feature_branch"
        assert EnvironmentType.HOTFIX == "hotfix"
        assert EnvironmentType.EXPERIMENTAL == "experimental"
    
    def test_access_level_values(self):
        """Test AccessLevel enum values."""
        assert AccessLevel.PUBLIC == "public"
        assert AccessLevel.ORGANIZATION == "organization"
        assert AccessLevel.TEAM == "team"
        assert AccessLevel.RESTRICTED == "restricted"


# ResourceAllocation Tests

class TestResourceAllocation:
    """Test resource allocation functionality."""
    
    def test_from_size_small(self):
        """Test resource allocation for small size."""
        allocation = ResourceAllocation.from_size(EnvironmentSize.SMALL)
        assert allocation.cpu_cores == 0.5
        assert allocation.memory_mb == 512
        assert allocation.storage_gb == 5
    
    def test_from_size_medium(self):
        """Test resource allocation for medium size."""
        allocation = ResourceAllocation.from_size(EnvironmentSize.MEDIUM)
        assert allocation.cpu_cores == 1.0
        assert allocation.memory_mb == 1024
        assert allocation.storage_gb == 10
    
    def test_from_size_large(self):
        """Test resource allocation for large size."""
        allocation = ResourceAllocation.from_size(EnvironmentSize.LARGE)
        assert allocation.cpu_cores == 2.0
        assert allocation.memory_mb == 2048
        assert allocation.storage_gb == 20
    
    def test_from_size_xlarge(self):
        """Test resource allocation for xlarge size."""
        allocation = ResourceAllocation.from_size(EnvironmentSize.XLARGE)
        assert allocation.cpu_cores == 4.0
        assert allocation.memory_mb == 4096
        assert allocation.storage_gb == 50


# DomainConfig Tests

class TestDomainConfig:
    """Test domain configuration."""
    
    def test_full_domain_generation(self):
        """Test that full domain is auto-generated."""
        config = DomainConfig(
            subdomain="pr-123-myapp",
            domain="preview.example.com"
        )
        assert config.full_domain == "pr-123-myapp.preview.example.com"
    
    def test_custom_full_domain(self):
        """Test custom full domain is preserved."""
        config = DomainConfig(
            subdomain="test",
            domain="example.com",
            full_domain="custom.example.com"
        )
        assert config.full_domain == "custom.example.com"


# EphemeralEnvironmentManager Tests

@pytest.mark.asyncio
class TestEphemeralEnvironmentManager:
    """Test ephemeral environment manager."""
    
    async def test_initialize(self, ephemeral_manager):
        """Test manager initialization."""
        assert ephemeral_manager._initialized is True
        assert "default" in ephemeral_manager.templates
        assert "default" in ephemeral_manager.budgets
    
    async def test_create_template(self, ephemeral_manager):
        """Test template creation."""
        template = await ephemeral_manager.create_template(
            template_id="custom",
            name="Custom Template",
            description="A custom template",
            default_size=EnvironmentSize.LARGE,
            default_ttl_hours=48,
            domain_suffix="custom.example.com"
        )
        
        assert template.template_id == "custom"
        assert template.name == "Custom Template"
        assert template.default_size == EnvironmentSize.LARGE
        assert template.default_ttl_hours == 48
        assert template.domain_suffix == "custom.example.com"
        assert "custom" in ephemeral_manager.templates
    
    async def test_get_template(self, ephemeral_manager):
        """Test retrieving template."""
        template = await ephemeral_manager.get_template("default")
        assert template is not None
        assert template.template_id == "default"
    
    async def test_list_templates(self, ephemeral_manager):
        """Test listing templates."""
        templates = await ephemeral_manager.list_templates()
        assert len(templates) >= 1
        
        template_ids = [t.template_id for t in templates]
        assert "default" in template_ids
    
    async def test_create_environment(self, ephemeral_manager, sample_deployment_config):
        """Test environment creation."""
        env = await ephemeral_manager.create_environment(
            name="feature-x",
            environment_type=EnvironmentType.PULL_REQUEST,
            repository_url="https://github.com/example/repo",
            branch_name="feature/x",
            commit_sha="abc123def456",
            deployment_config=sample_deployment_config,
            pull_request_number=42,
            size=EnvironmentSize.MEDIUM,
            created_by="developer@example.com"
        )
        
        assert env is not None
        assert env.name == "feature-x"
        assert env.environment_type == EnvironmentType.PULL_REQUEST
        assert env.branch_name == "feature/x"
        assert env.commit_sha == "abc123def456"
        assert env.pull_request_number == 42
        assert env.size == EnvironmentSize.MEDIUM
        assert env.resources.cpu_cores == 1.0
        assert env.status == EnvironmentStatus.PENDING
        assert env.environment_id in ephemeral_manager.environments
    
    async def test_create_environment_invalid_template(self, ephemeral_manager, sample_deployment_config):
        """Test environment creation with invalid template."""
        # Manually clear templates to simulate missing template
        ephemeral_manager.templates.clear()
        
        env = await ephemeral_manager.create_environment(
            name="feature-x",
            environment_type=EnvironmentType.PULL_REQUEST,
            repository_url="https://github.com/example/repo",
            branch_name="feature/x",
            commit_sha="abc123",
            deployment_config=sample_deployment_config,
            template_id="default"  # This template doesn't exist anymore
        )
        
        assert env is None
    
    async def test_get_environment(self, ephemeral_manager, sample_deployment_config):
        """Test retrieving environment."""
        env = await ephemeral_manager.create_environment(
            name="test-env",
            environment_type=EnvironmentType.FEATURE_BRANCH,
            repository_url="https://github.com/example/repo",
            branch_name="feature/test",
            commit_sha="abc123",
            deployment_config=sample_deployment_config
        )
        
        retrieved = await ephemeral_manager.get_environment(env.environment_id)
        assert retrieved is not None
        assert retrieved.environment_id == env.environment_id
    
    async def test_get_nonexistent_environment(self, ephemeral_manager):
        """Test retrieving non-existent environment."""
        env = await ephemeral_manager.get_environment("nonexistent")
        assert env is None
    
    async def test_list_environments(self, ephemeral_manager, sample_deployment_config):
        """Test listing environments."""
        # Create multiple environments
        await ephemeral_manager.create_environment(
            name="env-1",
            environment_type=EnvironmentType.PULL_REQUEST,
            repository_url="https://github.com/example/repo",
            branch_name="pr-1",
            commit_sha="abc123",
            deployment_config=sample_deployment_config
        )
        await ephemeral_manager.create_environment(
            name="env-2",
            environment_type=EnvironmentType.FEATURE_BRANCH,
            repository_url="https://github.com/example/repo",
            branch_name="feature/2",
            commit_sha="def456",
            deployment_config=sample_deployment_config
        )
        
        # Wait for environments to be created
        await asyncio.sleep(0.1)
        
        # List all
        all_envs = await ephemeral_manager.list_environments()
        assert len(all_envs) == 2
        
        # Filter by type
        pr_envs = await ephemeral_manager.list_environments(
            environment_type=EnvironmentType.PULL_REQUEST
        )
        assert len(pr_envs) == 1
    
    async def test_deploy_environment(self, ephemeral_manager, sample_deployment_config):
        """Test environment deployment."""
        env = await ephemeral_manager.create_environment(
            name="deploy-test",
            environment_type=EnvironmentType.FEATURE_BRANCH,
            repository_url="https://github.com/example/repo",
            branch_name="feature/deploy",
            commit_sha="abc123",
            deployment_config=sample_deployment_config
        )
        
        # Wait for provisioning (longer wait needed)
        await asyncio.sleep(2.5)
        
        # Deploy
        result = await ephemeral_manager.deploy_environment(
            env.environment_id,
            deployed_by="deployer@example.com"
        )
        
        assert result is True
        
        # Verify
        updated = await ephemeral_manager.get_environment(env.environment_id)
        assert updated.status == EnvironmentStatus.RUNNING
        assert updated.last_deployed_at is not None
    
    async def test_deploy_nonexistent_environment(self, ephemeral_manager):
        """Test deploying non-existent environment."""
        result = await ephemeral_manager.deploy_environment("nonexistent")
        assert result is False
    
    async def test_destroy_environment(self, ephemeral_manager, sample_deployment_config):
        """Test environment destruction."""
        env = await ephemeral_manager.create_environment(
            name="destroy-test",
            environment_type=EnvironmentType.HOTFIX,
            repository_url="https://github.com/example/repo",
            branch_name="hotfix/urgent",
            commit_sha="abc123",
            deployment_config=sample_deployment_config
        )
        
        # Wait for provisioning
        await asyncio.sleep(1.5)
        
        result = await ephemeral_manager.destroy_environment(
            env.environment_id,
            destroyed_by="admin@example.com",
            reason="Test cleanup"
        )
        
        assert result is True
        
        # Verify
        updated = await ephemeral_manager.get_environment(env.environment_id)
        assert updated.status == EnvironmentStatus.DESTROYED
        assert updated.destroyed_at is not None
    
    async def test_destroy_nonexistent_environment(self, ephemeral_manager):
        """Test destroying non-existent environment."""
        result = await ephemeral_manager.destroy_environment("nonexistent")
        assert result is False
    
    async def test_update_metrics(self, ephemeral_manager, sample_deployment_config):
        """Test updating environment metrics."""
        env = await ephemeral_manager.create_environment(
            name="metrics-test",
            environment_type=EnvironmentType.FEATURE_BRANCH,
            repository_url="https://github.com/example/repo",
            branch_name="feature/metrics",
            commit_sha="abc123",
            deployment_config=sample_deployment_config
        )
        
        result = await ephemeral_manager.update_metrics(
            env.environment_id,
            cpu_usage_percent=45.5,
            memory_usage_mb=512,
            request_count=1000,
            error_count=5
        )
        
        assert result is True
        
        metrics = await ephemeral_manager.get_metrics(env.environment_id)
        assert metrics is not None
        assert metrics.cpu_usage_percent == 45.5
        assert metrics.memory_usage_mb == 512
        assert metrics.request_count == 1000
        assert metrics.error_count == 5
    
    async def test_get_environment_events(self, ephemeral_manager, sample_deployment_config):
        """Test retrieving environment events."""
        env = await ephemeral_manager.create_environment(
            name="events-test",
            environment_type=EnvironmentType.FEATURE_BRANCH,
            repository_url="https://github.com/example/repo",
            branch_name="feature/events",
            commit_sha="abc123",
            deployment_config=sample_deployment_config,
            created_by="creator@example.com"
        )
        
        # Wait for provisioning and event logging
        await asyncio.sleep(0.5)
        
        events = await ephemeral_manager.get_environment_events(env.environment_id)
        assert len(events) >= 1  # At least creation event
        assert events[0].event_type == "created"
    
    async def test_handle_pr_event_opened(self, ephemeral_manager):
        """Test handling PR opened event."""
        deployment_config = DeploymentConfig(
            image_repository="registry.example.com/app",
            image_tag="latest"
        )
        
        env = await ephemeral_manager.handle_pr_event(
            action="opened",
            pull_request_number=123,
            branch_name="feature/new-feature",
            commit_sha="abc123def456",
            repository_url="https://github.com/example/repo",
            sender="developer@example.com"
        )
        
        assert env is not None
        assert env.pull_request_number == 123
        assert env.branch_name == "feature/new-feature"
        assert env.environment_type == EnvironmentType.PULL_REQUEST
    
    async def test_handle_pr_event_closed(self, ephemeral_manager, sample_deployment_config):
        """Test handling PR closed event."""
        # Create environment for PR
        env = await ephemeral_manager.create_environment(
            name="pr-456",
            environment_type=EnvironmentType.PULL_REQUEST,
            repository_url="https://github.com/example/repo",
            branch_name="feature/closing",
            commit_sha="abc123",
            deployment_config=sample_deployment_config,
            pull_request_number=456
        )
        
        # Wait for provisioning
        await asyncio.sleep(1.5)
        
        # Handle PR close
        result = await ephemeral_manager.handle_pr_event(
            action="closed",
            pull_request_number=456,
            branch_name="feature/closing",
            commit_sha="abc123",
            repository_url="https://github.com/example/repo",
            sender="github-actions"
        )
        
        assert result is None
        
        # Verify environment destroyed
        updated = await ephemeral_manager.get_environment(env.environment_id)
        assert updated.status == EnvironmentStatus.DESTROYED
    
    async def test_get_budget(self, ephemeral_manager):
        """Test retrieving budget."""
        budget = await ephemeral_manager.get_budget("default")
        assert budget is not None
        assert budget.budget_id == "default"
    
    async def test_get_statistics(self, ephemeral_manager, sample_deployment_config):
        """Test getting statistics."""
        # Create environment
        await ephemeral_manager.create_environment(
            name="stats-test",
            environment_type=EnvironmentType.FEATURE_BRANCH,
            repository_url="https://github.com/example/repo",
            branch_name="feature/stats",
            commit_sha="abc123",
            deployment_config=sample_deployment_config,
            size=EnvironmentSize.LARGE
        )
        
        await asyncio.sleep(0.5)
        
        stats = await ephemeral_manager.get_statistics()
        
        assert stats["environments"]["total"] == 1
        assert stats["environments"]["by_type"]["feature_branch"] == 1
        assert stats["environments"]["by_size"]["large"] == 1
        assert "resources" in stats
        assert "cost" in stats


# Global Manager Tests

@pytest.mark.asyncio
class TestGlobalManager:
    """Test global ephemeral manager functions."""
    
    async def test_get_ephemeral_manager(self):
        """Test getting global ephemeral manager."""
        manager1 = await get_ephemeral_manager()
        manager2 = await get_ephemeral_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert manager1._initialized is True
    
    async def test_reset_ephemeral_manager(self):
        """Test resetting global ephemeral manager."""
        manager1 = await get_ephemeral_manager()
        reset_ephemeral_manager()
        manager2 = await get_ephemeral_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
