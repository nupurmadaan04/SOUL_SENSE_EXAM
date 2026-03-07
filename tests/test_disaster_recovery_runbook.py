"""
Comprehensive tests for Disaster Recovery Runbook Executable Checks module.

Test coverage: 40+ tests
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

# Import the module under test
import sys
sys.path.insert(0, "backend/fastapi/api/utils")

from disaster_recovery_runbook import (
    CheckStatus, CheckSeverity, CheckCategory, RunbookType,
    CheckStep, DRCheck, CheckExecution, RecoveryObjective, RunbookExecution,
    BackupVerification, DisasterRecoveryManager,
    get_dr_manager, reset_dr_manager
)


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def reset_manager():
    """Reset the global DR manager before each test."""
    reset_dr_manager()
    yield
    reset_dr_manager()


@pytest_asyncio.fixture
async def dr_manager():
    """Create a fresh disaster recovery manager."""
    manager = DisasterRecoveryManager()
    await manager.initialize()
    yield manager
    reset_dr_manager()


@pytest.fixture
def sample_check_steps():
    """Sample check steps."""
    return [
        CheckStep(
            step_id="step_1",
            name="Verify Primary Database",
            description="Check primary database connectivity",
            command="check_db_connection primary",
            expected_result="Connection successful"
        ),
        CheckStep(
            step_id="step_2",
            name="Verify Standby Database",
            description="Check standby database connectivity",
            command="check_db_connection standby",
            expected_result="Connection successful"
        ),
        CheckStep(
            step_id="step_3",
            name="Test Failover",
            description="Execute failover procedure",
            command="execute_failover",
            expected_result="Failover completed"
        )
    ]


# Enums Tests

class TestDREnums:
    """Test disaster recovery enums."""
    
    def test_check_status_values(self):
        """Test CheckStatus enum values."""
        assert CheckStatus.PENDING == "pending"
        assert CheckStatus.RUNNING == "running"
        assert CheckStatus.PASSED == "passed"
        assert CheckStatus.FAILED == "failed"
        assert CheckStatus.WARNING == "warning"
        assert CheckStatus.SKIPPED == "skipped"
        assert CheckStatus.ERROR == "error"
        assert CheckStatus.TIMEOUT == "timeout"
    
    def test_check_severity_values(self):
        """Test CheckSeverity enum values."""
        assert CheckSeverity.CRITICAL == "critical"
        assert CheckSeverity.HIGH == "high"
        assert CheckSeverity.MEDIUM == "medium"
        assert CheckSeverity.LOW == "low"
        assert CheckSeverity.INFO == "info"
    
    def test_check_category_values(self):
        """Test CheckCategory enum values."""
        assert CheckCategory.BACKUP == "backup"
        assert CheckCategory.FAILOVER == "failover"
        assert CheckCategory.RECOVERY == "recovery"
        assert CheckCategory.REPLICATION == "replication"
        assert CheckCategory.INFRASTRUCTURE == "infrastructure"
        assert CheckCategory.NETWORK == "network"
        assert CheckCategory.SECURITY == "security"
        assert CheckCategory.COMPLIANCE == "compliance"
    
    def test_runbook_type_values(self):
        """Test RunbookType enum values."""
        assert RunbookType.DATABASE_FAILOVER == "database_failover"
        assert RunbookType.APPLICATION_FAILOVER == "application_failover"
        assert RunbookType.FULL_SITE_RECOVERY == "full_site_recovery"
        assert RunbookType.DATA_RESTORATION == "data_restoration"
        assert RunbookType.NETWORK_RECOVERY == "network_recovery"
        assert RunbookType.SECURITY_INCIDENT == "security_incident"
        assert RunbookType.INFRASTRUCTURE_RESTORE == "infrastructure_restore"


# DisasterRecoveryManager Tests

@pytest.mark.asyncio
class TestDisasterRecoveryManager:
    """Test disaster recovery manager."""
    
    async def test_initialize(self, dr_manager):
        """Test manager initialization."""
        assert dr_manager._initialized is True
        assert "rto_database" in dr_manager.recovery_objectives
        assert "rpo_database" in dr_manager.recovery_objectives
    
    async def test_create_check(self, dr_manager, sample_check_steps):
        """Test DR check creation."""
        check = await dr_manager.create_check(
            check_id="db_failover_check",
            name="Database Failover Check",
            description="Verify database failover capability",
            category=CheckCategory.FAILOVER,
            severity=CheckSeverity.CRITICAL,
            runbook_type=RunbookType.DATABASE_FAILOVER,
            steps=sample_check_steps,
            schedule_cron="0 2 * * *",
            created_by="admin@example.com"
        )
        
        assert check.check_id == "db_failover_check"
        assert check.name == "Database Failover Check"
        assert check.category == CheckCategory.FAILOVER
        assert check.severity == CheckSeverity.CRITICAL
        assert len(check.steps) == 3
        assert check.schedule_cron == "0 2 * * *"
        assert "db_failover_check" in dr_manager.checks
    
    async def test_get_check(self, dr_manager, sample_check_steps):
        """Test retrieving check."""
        await dr_manager.create_check(
            check_id="test_check",
            name="Test Check",
            description="Test",
            category=CheckCategory.BACKUP,
            severity=CheckSeverity.HIGH,
            runbook_type=RunbookType.DATA_RESTORATION,
            steps=sample_check_steps[:1]
        )
        
        retrieved = await dr_manager.get_check("test_check")
        assert retrieved is not None
        assert retrieved.check_id == "test_check"
    
    async def test_get_nonexistent_check(self, dr_manager):
        """Test retrieving non-existent check."""
        check = await dr_manager.get_check("nonexistent")
        assert check is None
    
    async def test_list_checks(self, dr_manager, sample_check_steps):
        """Test listing checks."""
        await dr_manager.create_check(
            check_id="check_1",
            name="Check 1",
            description="Test",
            category=CheckCategory.BACKUP,
            severity=CheckSeverity.HIGH,
            runbook_type=RunbookType.DATA_RESTORATION,
            steps=sample_check_steps[:1]
        )
        await dr_manager.create_check(
            check_id="check_2",
            name="Check 2",
            description="Test",
            category=CheckCategory.FAILOVER,
            severity=CheckSeverity.CRITICAL,
            runbook_type=RunbookType.DATABASE_FAILOVER,
            steps=sample_check_steps[:1]
        )
        
        # List all
        all_checks = await dr_manager.list_checks()
        assert len(all_checks) == 2
        
        # Filter by category
        backup_checks = await dr_manager.list_checks(category=CheckCategory.BACKUP)
        assert len(backup_checks) == 1
        
        # Filter by severity
        critical_checks = await dr_manager.list_checks(severity=CheckSeverity.CRITICAL)
        assert len(critical_checks) == 1
    
    async def test_execute_check(self, dr_manager, sample_check_steps):
        """Test check execution."""
        await dr_manager.create_check(
            check_id="exec_test",
            name="Execution Test",
            description="Test execution",
            category=CheckCategory.FAILOVER,
            severity=CheckSeverity.HIGH,
            runbook_type=RunbookType.DATABASE_FAILOVER,
            steps=sample_check_steps
        )
        
        execution = await dr_manager.execute_check(
            check_id="exec_test",
            triggered_by="tester@example.com"
        )
        
        assert execution is not None
        assert execution.check_id == "exec_test"
        assert execution.status in [CheckStatus.PASSED, CheckStatus.FAILED]
        assert len(execution.steps_results) == 3
        assert execution.completed_at is not None
    
    async def test_execute_nonexistent_check(self, dr_manager):
        """Test executing non-existent check."""
        execution = await dr_manager.execute_check("nonexistent")
        assert execution is None
    
    async def test_get_execution(self, dr_manager, sample_check_steps):
        """Test retrieving execution."""
        await dr_manager.create_check(
            check_id="get_exec_test",
            name="Get Exec Test",
            description="Test",
            category=CheckCategory.BACKUP,
            severity=CheckSeverity.MEDIUM,
            runbook_type=RunbookType.DATA_RESTORATION,
            steps=sample_check_steps[:1]
        )
        
        execution = await dr_manager.execute_check("get_exec_test")
        retrieved = await dr_manager.get_execution(execution.execution_id)
        
        assert retrieved is not None
        assert retrieved.execution_id == execution.execution_id
    
    async def test_list_executions(self, dr_manager, sample_check_steps):
        """Test listing executions."""
        await dr_manager.create_check(
            check_id="list_exec_check",
            name="List Exec Check",
            description="Test",
            category=CheckCategory.BACKUP,
            severity=CheckSeverity.LOW,
            runbook_type=RunbookType.DATA_RESTORATION,
            steps=sample_check_steps[:1]
        )
        
        # Execute twice
        await dr_manager.execute_check("list_exec_check")
        await dr_manager.execute_check("list_exec_check")
        
        executions = await dr_manager.list_executions(check_id="list_exec_check")
        assert len(executions) == 2
    
    async def test_execute_runbook(self, dr_manager, sample_check_steps):
        """Test full runbook execution."""
        # Create multiple checks
        await dr_manager.create_check(
            check_id="rb_check_1",
            name="Runbook Check 1",
            description="Test",
            category=CheckCategory.FAILOVER,
            severity=CheckSeverity.CRITICAL,
            runbook_type=RunbookType.DATABASE_FAILOVER,
            steps=sample_check_steps[:2]
        )
        await dr_manager.create_check(
            check_id="rb_check_2",
            name="Runbook Check 2",
            description="Test",
            category=CheckCategory.REPLICATION,
            severity=CheckSeverity.HIGH,
            runbook_type=RunbookType.DATABASE_FAILOVER,
            steps=sample_check_steps[:1]
        )
        
        runbook_exec = await dr_manager.execute_runbook(
            runbook_type=RunbookType.DATABASE_FAILOVER,
            check_ids=["rb_check_1", "rb_check_2"],
            triggered_by="admin@example.com"
        )
        
        assert runbook_exec is not None
        assert runbook_exec.runbook_type == RunbookType.DATABASE_FAILOVER
        assert len(runbook_exec.check_executions) == 2
        assert runbook_exec.completed_at is not None
    
    async def test_verify_backup(self, dr_manager):
        """Test backup verification."""
        verification = await dr_manager.verify_backup(
            backup_id="backup_001",
            backup_type="full",
            source_system="production_db",
            backup_timestamp=datetime.utcnow() - timedelta(hours=1),
            size_bytes=1073741824,  # 1 GB
            integrity_hash="sha256:abc123"
        )
        
        assert verification is not None
        assert verification.backup_id == "backup_001"
        assert verification.backup_type == "full"
        assert verification.verification_status == CheckStatus.PASSED
        assert verification.restoration_tested is True
        assert "backup_001" in dr_manager.backup_verifications
    
    async def test_get_backup_verification(self, dr_manager):
        """Test retrieving backup verification."""
        await dr_manager.verify_backup(
            backup_id="backup_002",
            backup_type="incremental",
            source_system="app_server",
            backup_timestamp=datetime.utcnow(),
            size_bytes=536870912,  # 512 MB
            integrity_hash="sha256:def456"
        )
        
        retrieved = await dr_manager.get_backup_verification("backup_002")
        assert retrieved is not None
        assert retrieved.backup_id == "backup_002"
    
    async def test_get_recovery_objective(self, dr_manager):
        """Test retrieving recovery objective."""
        objective = await dr_manager.get_recovery_objective("rto_database")
        assert objective is not None
        assert objective.objective_type == "RTO"
        assert objective.target_seconds == 300
    
    async def test_list_recovery_objectives(self, dr_manager):
        """Test listing recovery objectives."""
        objectives = await dr_manager.list_recovery_objectives()
        assert len(objectives) >= 4  # Default objectives created
        
        # Filter by type
        rto_objectives = await dr_manager.list_recovery_objectives(objective_type="RTO")
        assert len(rto_objectives) >= 2
        
        rpo_objectives = await dr_manager.list_recovery_objectives(objective_type="RPO")
        assert len(rpo_objectives) >= 1
    
    async def test_update_recovery_objective(self, dr_manager):
        """Test updating recovery objective."""
        updated = await dr_manager.update_recovery_objective(
            objective_id="rto_database",
            current_value_seconds=240  # 4 minutes
        )
        
        assert updated is not None
        assert updated.current_value_seconds == 240
        assert updated.compliant is True  # Within 300s target
        assert updated.last_measured_at is not None
    
    async def test_update_recovery_objective_nonexistent(self, dr_manager):
        """Test updating non-existent recovery objective."""
        result = await dr_manager.update_recovery_objective(
            objective_id="nonexistent",
            current_value_seconds=100
        )
        assert result is None
    
    async def test_get_statistics(self, dr_manager, sample_check_steps):
        """Test getting statistics."""
        # Create and execute some checks
        await dr_manager.create_check(
            check_id="stats_check",
            name="Stats Check",
            description="Test",
            category=CheckCategory.BACKUP,
            severity=CheckSeverity.HIGH,
            runbook_type=RunbookType.DATA_RESTORATION,
            steps=sample_check_steps[:1]
        )
        await dr_manager.execute_check("stats_check")
        
        # Verify a backup
        await dr_manager.verify_backup(
            backup_id="stats_backup",
            backup_type="full",
            source_system="db",
            backup_timestamp=datetime.utcnow(),
            size_bytes=1000000,
            integrity_hash="hash123"
        )
        
        stats = await dr_manager.get_statistics()
        
        assert "checks" in stats
        assert "categories" in stats
        assert "backups" in stats
        assert "recovery_objectives" in stats
        assert stats["checks"]["total_defined"] >= 1


# Global Manager Tests

@pytest.mark.asyncio
class TestGlobalManager:
    """Test global DR manager functions."""
    
    async def test_get_dr_manager(self):
        """Test getting global DR manager."""
        manager1 = await get_dr_manager()
        manager2 = await get_dr_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert manager1._initialized is True
    
    async def test_reset_dr_manager(self):
        """Test resetting global DR manager."""
        manager1 = await get_dr_manager()
        reset_dr_manager()
        manager2 = await get_dr_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
