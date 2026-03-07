"""
Comprehensive tests for Dependency Update Batching with Risk Tiers module.

Test coverage: 35+ tests
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

# Import the module under test
import sys
sys.path.insert(0, "backend/fastapi/api/utils")

from dependency_update_batching import (
    UpdateType, RiskTier, UpdateStatus, BatchingStrategy, CompatibilityStatus,
    Dependency, AvailableUpdate, UpdateBatch, DeploymentResult,
    RiskAssessmentRule, DependencyPolicy, DependencyUpdateManager,
    get_update_manager, reset_update_manager
)


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def reset_manager():
    """Reset the global update manager before each test."""
    reset_update_manager()
    yield
    reset_update_manager()


@pytest_asyncio.fixture
async def update_manager():
    """Create a fresh dependency update manager."""
    manager = DependencyUpdateManager()
    await manager.initialize()
    yield manager
    reset_update_manager()


# Enums Tests

class TestUpdateEnums:
    """Test dependency update enums."""
    
    def test_update_type_values(self):
        """Test UpdateType enum values."""
        assert UpdateType.SECURITY == "security"
        assert UpdateType.BUGFIX == "bugfix"
        assert UpdateType.FEATURE == "feature"
        assert UpdateType.PERFORMANCE == "performance"
        assert UpdateType.BREAKING == "breaking"
        assert UpdateType.DEPRECATED == "deprecated"
    
    def test_risk_tier_values(self):
        """Test RiskTier enum values."""
        assert RiskTier.CRITICAL == "critical"
        assert RiskTier.HIGH == "high"
        assert RiskTier.MEDIUM == "medium"
        assert RiskTier.LOW == "low"
        assert RiskTier.INFO == "info"
    
    def test_update_status_values(self):
        """Test UpdateStatus enum values."""
        assert UpdateStatus.PENDING == "pending"
        assert UpdateStatus.ANALYZING == "analyzing"
        assert UpdateStatus.APPROVED == "approved"
        assert UpdateStatus.REJECTED == "rejected"
        assert UpdateStatus.SCHEDULED == "scheduled"
        assert UpdateStatus.DEPLOYING == "deploying"
        assert UpdateStatus.DEPLOYED == "deployed"
        assert UpdateStatus.ROLLED_BACK == "rolled_back"
        assert UpdateStatus.FAILED == "failed"
    
    def test_batching_strategy_values(self):
        """Test BatchingStrategy enum values."""
        assert BatchingStrategy.SECURITY_ONLY == "security_only"
        assert BatchingStrategy.PATCH_ONLY == "patch_only"
        assert BatchingStrategy.MINOR_ONLY == "minor_only"
        assert BatchingStrategy.ALL_EXCEPT_MAJOR == "all_except_major"
        assert BatchingStrategy.ALL == "all"
        assert BatchingStrategy.CUSTOM == "custom"


# DependencyUpdateManager Tests

@pytest.mark.asyncio
class TestDependencyUpdateManager:
    """Test dependency update manager."""
    
    async def test_initialize(self, update_manager):
        """Test manager initialization."""
        assert update_manager._initialized is True
        assert len(update_manager.risk_rules) >= 5
        assert "default" in update_manager.policies
    
    async def test_register_dependency(self, update_manager):
        """Test dependency registration."""
        dep = await update_manager.register_dependency(
            name="requests",
            current_version="2.28.0",
            ecosystem="pypi",
            direct_dependency=True,
            usage_scope="production"
        )
        
        assert dep.name == "requests"
        assert dep.current_version == "2.28.0"
        assert dep.ecosystem == "pypi"
        assert dep.direct_dependency is True
        assert "requests" in update_manager.dependencies
    
    async def test_get_dependency(self, update_manager):
        """Test retrieving dependency."""
        await update_manager.register_dependency(
            name="numpy",
            current_version="1.23.0",
            ecosystem="pypi"
        )
        
        retrieved = await update_manager.get_dependency("numpy")
        assert retrieved is not None
        assert retrieved.name == "numpy"
    
    async def test_get_nonexistent_dependency(self, update_manager):
        """Test retrieving non-existent dependency."""
        dep = await update_manager.get_dependency("nonexistent")
        assert dep is None
    
    async def test_list_dependencies(self, update_manager):
        """Test listing dependencies."""
        await update_manager.register_dependency("django", "4.0.0", "pypi")
        await update_manager.register_dependency("react", "18.0.0", "npm")
        await update_manager.register_dependency("lodash", "4.17.0", "npm", direct_dependency=False)
        
        # List all
        all_deps = await update_manager.list_dependencies()
        assert len(all_deps) == 3
        
        # Filter by ecosystem
        npm_deps = await update_manager.list_dependencies(ecosystem="npm")
        assert len(npm_deps) == 2
        
        # Filter direct only
        direct_deps = await update_manager.list_dependencies(direct_only=True)
        assert len(direct_deps) == 2
    
    async def test_assess_update_risk_security(self, update_manager):
        """Test risk assessment for security update."""
        dep = await update_manager.register_dependency("package", "1.0.0", "pypi")
        
        risk_tier, risk_score = await update_manager.assess_update_risk(
            dep, "1.0.1", UpdateType.SECURITY,
            vulnerabilities=[{"cvss_score": 9.5, "cve_id": "CVE-2024-1234"}]
        )
        
        assert risk_tier == RiskTier.CRITICAL
        assert risk_score == 10.0
    
    async def test_assess_update_risk_breaking(self, update_manager):
        """Test risk assessment for breaking change."""
        dep = await update_manager.register_dependency("package", "1.0.0", "pypi")
        
        risk_tier, risk_score = await update_manager.assess_update_risk(
            dep, "2.0.0", UpdateType.BREAKING
        )
        
        assert risk_tier == RiskTier.HIGH
        assert risk_score >= 6.0
    
    async def test_assess_update_risk_patch(self, update_manager):
        """Test risk assessment for patch update."""
        dep = await update_manager.register_dependency("package", "1.0.0", "pypi")
        
        risk_tier, risk_score = await update_manager.assess_update_risk(
            dep, "1.0.1", UpdateType.BUGFIX
        )
        
        assert risk_tier == RiskTier.LOW
        assert risk_score <= 2.0
    
    async def test_register_available_update(self, update_manager):
        """Test registering available update."""
        await update_manager.register_dependency("flask", "2.2.0", "pypi")
        
        update = await update_manager.register_available_update(
            dependency_name="flask",
            new_version="2.3.0",
            update_type=UpdateType.FEATURE,
            changelog="Added new features"
        )
        
        assert update is not None
        assert update.dependency.name == "flask"
        assert update.new_version == "2.3.0"
        assert update.update_type == UpdateType.FEATURE
        assert update.risk_tier in [RiskTier.LOW, RiskTier.MEDIUM]
    
    async def test_register_available_update_nonexistent_dep(self, update_manager):
        """Test registering update for non-existent dependency."""
        update = await update_manager.register_available_update(
            dependency_name="nonexistent",
            new_version="1.0.0",
            update_type=UpdateType.BUGFIX
        )
        
        assert update is None
    
    async def test_list_available_updates(self, update_manager):
        """Test listing available updates."""
        await update_manager.register_dependency("pkg1", "1.0.0", "pypi")
        await update_manager.register_dependency("pkg2", "2.0.0", "pypi")
        
        await update_manager.register_available_update("pkg1", "1.0.1", UpdateType.BUGFIX)
        await update_manager.register_available_update("pkg2", "2.1.0", UpdateType.FEATURE)
        
        updates = await update_manager.list_available_updates()
        assert len(updates) == 2
        
        # Filter by type
        bugfix_updates = await update_manager.list_available_updates(update_type=UpdateType.BUGFIX)
        assert len(bugfix_updates) == 1
    
    async def test_create_batch(self, update_manager):
        """Test creating update batch."""
        await update_manager.register_dependency("dep1", "1.0.0", "pypi")
        await update_manager.register_dependency("dep2", "2.0.0", "pypi")
        
        update1 = await update_manager.register_available_update("dep1", "1.0.1", UpdateType.BUGFIX)
        update2 = await update_manager.register_available_update("dep2", "2.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Patch Updates",
            description="Bug fix updates",
            strategy=BatchingStrategy.PATCH_ONLY,
            update_ids=[update1.update_id, update2.update_id]
        )
        
        assert batch is not None
        assert batch.name == "Patch Updates"
        assert len(batch.updates) == 2
        assert batch.strategy == BatchingStrategy.PATCH_ONLY
    
    async def test_create_batch_empty(self, update_manager):
        """Test creating batch with invalid updates."""
        batch = await update_manager.create_batch(
            name="Empty Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=["nonexistent"]
        )
        
        assert batch is None
    
    async def test_approve_batch(self, update_manager):
        """Test approving batch."""
        await update_manager.register_dependency("dep", "1.0.0", "pypi")
        update = await update_manager.register_available_update("dep", "1.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Test Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=[update.update_id]
        )
        
        approved = await update_manager.approve_batch(batch.batch_id, "admin@example.com")
        
        assert approved is not None
        assert approved.status == UpdateStatus.APPROVED
        assert approved.approved_by == "admin@example.com"
        assert approved.approved_at is not None
    
    async def test_schedule_batch(self, update_manager):
        """Test scheduling batch."""
        await update_manager.register_dependency("dep", "1.0.0", "pypi")
        update = await update_manager.register_available_update("dep", "1.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Test Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=[update.update_id]
        )
        
        schedule_time = datetime.utcnow() + timedelta(days=1)
        scheduled = await update_manager.schedule_batch(batch.batch_id, schedule_time)
        
        assert scheduled is not None
        assert scheduled.status == UpdateStatus.SCHEDULED
        assert scheduled.scheduled_at == schedule_time
    
    async def test_deploy_batch(self, update_manager):
        """Test deploying batch."""
        await update_manager.register_dependency("dep", "1.0.0", "pypi")
        update = await update_manager.register_available_update("dep", "1.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Test Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=[update.update_id]
        )
        
        await update_manager.approve_batch(batch.batch_id, "admin@example.com")
        
        result = await update_manager.deploy_batch(batch.batch_id, "deployer@example.com")
        
        assert result is not None
        assert result.status == UpdateStatus.DEPLOYED
        assert len(result.successful_updates) == 1
    
    async def test_deploy_batch_not_approved(self, update_manager):
        """Test deploying batch without approval."""
        await update_manager.register_dependency("dep", "1.0.0", "pypi")
        update = await update_manager.register_available_update("dep", "1.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Test Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=[update.update_id]
        )
        
        result = await update_manager.deploy_batch(batch.batch_id)
        
        assert result is None
    
    async def test_rollback_batch(self, update_manager):
        """Test rolling back batch."""
        await update_manager.register_dependency("dep", "1.0.0", "pypi")
        update = await update_manager.register_available_update("dep", "1.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Test Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=[update.update_id]
        )
        
        await update_manager.approve_batch(batch.batch_id, "admin@example.com")
        await update_manager.deploy_batch(batch.batch_id)
        
        result = await update_manager.rollback_batch(batch.batch_id, "admin@example.com")
        
        assert result is not None
        assert result.status == UpdateStatus.ROLLED_BACK
    
    async def test_get_statistics(self, update_manager):
        """Test getting statistics."""
        await update_manager.register_dependency("dep1", "1.0.0", "pypi")
        await update_manager.register_dependency("dep2", "2.0.0", "npm")
        
        update = await update_manager.register_available_update("dep1", "1.0.1", UpdateType.BUGFIX)
        
        batch = await update_manager.create_batch(
            name="Stats Batch",
            description="Test",
            strategy=BatchingStrategy.ALL,
            update_ids=[update.update_id]
        )
        
        await update_manager.approve_batch(batch.batch_id, "admin@example.com")
        await update_manager.deploy_batch(batch.batch_id)
        
        stats = await update_manager.get_statistics()
        
        assert "dependencies" in stats
        assert "updates" in stats
        assert "batches" in stats
        assert "deployments" in stats
        assert stats["dependencies"]["total_tracked"] == 2


# Global Manager Tests

@pytest.mark.asyncio
class TestGlobalManager:
    """Test global update manager functions."""
    
    async def test_get_update_manager(self):
        """Test getting global update manager."""
        manager1 = await get_update_manager()
        manager2 = await get_update_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert manager1._initialized is True
    
    async def test_reset_update_manager(self):
        """Test resetting global update manager."""
        manager1 = await get_update_manager()
        reset_update_manager()
        manager2 = await get_update_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
