"""
Tests for Onboarding Template Generator (#1439)

Comprehensive tests for multi-tenant onboarding template management,
tenant provisioning, and onboarding workflow execution.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

# Import the module under test
import sys
sys.path.insert(0, 'backend/fastapi')

from api.utils.onboarding_template_generator import (
    OnboardingTemplateGenerator,
    OnboardingTemplate,
    TenantOnboarding,
    TemplateConfig,
    TemplateStatus,
    OnboardingStatus,
    ResourceType,
    ResourceConfig,
    OnboardingStep,
    ValidationResult,
    StepExecutionResult,
    get_template_generator,
)


Base = declarative_base()


# Test Fixtures

@pytest.fixture
async def async_engine():
    """Create test async engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def generator(async_engine):
    """Create initialized template generator."""
    gen = OnboardingTemplateGenerator(async_engine)
    
    # Create tables
    async with async_engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_templates (
                id INTEGER PRIMARY KEY,
                template_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                version TEXT DEFAULT '1.0.0',
                config TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                parent_template_id TEXT
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tenant_onboardings (
                id INTEGER PRIMARY KEY,
                onboarding_id TEXT UNIQUE NOT NULL,
                template_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                tenant_name TEXT NOT NULL,
                tenant_data TEXT DEFAULT '{}',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                progress_percentage FLOAT DEFAULT 0,
                current_step TEXT,
                results TEXT DEFAULT '{}',
                errors TEXT DEFAULT '[]'
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS onboarding_step_logs (
                id INTEGER PRIMARY KEY,
                log_id TEXT UNIQUE NOT NULL,
                onboarding_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                output TEXT DEFAULT '{}',
                error_message TEXT,
                execution_time_ms FLOAT,
                retry_count INTEGER DEFAULT 0,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    await gen.initialize()
    yield gen


@pytest.fixture
def sample_resources():
    """Create sample resource configs."""
    return [
        ResourceConfig(
            resource_type=ResourceType.DATABASE,
            resource_name="tenant_db",
            config={"size": "small"},
            required=True,
        ),
        ResourceConfig(
            resource_type=ResourceType.API_KEY,
            resource_name="api_key",
            required=True,
        ),
    ]


@pytest.fixture
def sample_steps():
    """Create sample onboarding steps."""
    return [
        OnboardingStep(
            step_id="step_1",
            name="Validate Data",
            description="Validate tenant data",
            action_type="validate",
            config={},
            required=True,
        ),
        OnboardingStep(
            step_id="step_2",
            name="Provision Resources",
            description="Provision tenant resources",
            action_type="provision",
            config={"resource_type": "database"},
            dependencies=["step_1"],
            required=True,
        ),
    ]


@pytest.fixture
def sample_config(sample_resources, sample_steps):
    """Create sample template configuration."""
    return TemplateConfig(
        resources=sample_resources,
        steps=sample_steps,
        settings={"required_fields": ["name", "domain", "admin_email"]},
        validations=[
            {"field": "name", "rule": "min_length", "value": 3, "message": "Name too short"}
        ],
    )


# --- Test Classes ---

class TestResourceConfig:
    """Test resource configuration."""
    
    def test_resource_config_creation(self):
        """Test creating resource config."""
        resource = ResourceConfig(
            resource_type=ResourceType.DATABASE,
            resource_name="tenant_db",
            config={"size": "small"},
            dependencies=[],
            required=True,
        )
        
        assert resource.resource_type == ResourceType.DATABASE
        assert resource.resource_name == "tenant_db"
        assert resource.config["size"] == "small"
        assert resource.required is True
    
    def test_resource_config_to_dict(self):
        """Test resource config serialization."""
        resource = ResourceConfig(
            resource_type=ResourceType.STORAGE,
            resource_name="storage",
            config={"capacity": "10GB"},
        )
        
        data = resource.to_dict()
        assert data["resource_type"] == "storage"
        assert data["resource_name"] == "storage"
        assert data["config"]["capacity"] == "10GB"


class TestOnboardingStep:
    """Test onboarding step."""
    
    def test_step_creation(self):
        """Test creating onboarding step."""
        step = OnboardingStep(
            step_id="step_1",
            name="Validate",
            description="Validate data",
            action_type="validate",
            config={},
            dependencies=[],
            required=True,
            timeout_seconds=300,
            retry_count=3,
        )
        
        assert step.step_id == "step_1"
        assert step.name == "Validate"
        assert step.action_type == "validate"
        assert step.timeout_seconds == 300
        assert step.retry_count == 3


class TestTemplateConfig:
    """Test template configuration."""
    
    def test_config_creation(self, sample_resources, sample_steps):
        """Test creating template config."""
        config = TemplateConfig(
            resources=sample_resources,
            steps=sample_steps,
            settings={"key": "value"},
        )
        
        assert len(config.resources) == 2
        assert len(config.steps) == 2
        assert config.settings["key"] == "value"


class TestOnboardingTemplate:
    """Test onboarding template model."""
    
    def test_template_creation(self, sample_config):
        """Test creating template."""
        template = OnboardingTemplate(
            template_id="tpl_001",
            name="Standard Tenant",
            description="Standard tenant setup",
            version="1.0.0",
            config=sample_config,
            status=TemplateStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        assert template.template_id == "tpl_001"
        assert template.name == "Standard Tenant"
        assert template.status == TemplateStatus.DRAFT


class TestOnboardingTemplateGenerator:
    """Test template generator functionality."""
    
    @pytest.mark.asyncio
    async def test_generator_initialization(self, async_engine):
        """Test generator initialization."""
        gen = OnboardingTemplateGenerator(async_engine)
        await gen.initialize()
        assert gen._templates == {}
    
    @pytest.mark.asyncio
    async def test_create_template(self, generator, sample_config):
        """Test creating a template."""
        template = await generator.create_template(
            name="Test Template",
            description="A test template",
            config=sample_config,
            created_by="user_001",
        )
        
        assert template.template_id.startswith("tpl_")
        assert template.name == "Test Template"
        assert template.status == TemplateStatus.DRAFT
        assert template.created_by == "user_001"
    
    @pytest.mark.asyncio
    async def test_get_template(self, generator, sample_config):
        """Test retrieving a template."""
        created = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        
        retrieved = await generator.get_template(created.template_id)
        
        assert retrieved is not None
        assert retrieved.template_id == created.template_id
        assert retrieved.name == "Test Template"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, generator):
        """Test retrieving non-existent template."""
        template = await generator.get_template("nonexistent")
        assert template is None
    
    @pytest.mark.asyncio
    async def test_list_templates(self, generator, sample_config):
        """Test listing templates."""
        # Create multiple templates
        for i in range(3):
            await generator.create_template(
                name=f"Template {i}",
                config=sample_config,
            )
        
        templates = await generator.list_templates()
        assert len(templates) >= 3
    
    @pytest.mark.asyncio
    async def test_activate_template(self, generator, sample_config):
        """Test activating a template."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        
        success = await generator.activate_template(template.template_id)
        assert success is True
        
        # Verify status
        updated = await generator.get_template(template.template_id)
        assert updated.status == TemplateStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_generate_onboarding(self, generator, sample_config):
        """Test generating tenant onboarding."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme Corp", "domain": "acme.com"},
        )
        
        assert onboarding is not None
        assert onboarding.onboarding_id.startswith("onb_")
        assert onboarding.tenant_name == "Acme Corp"
        assert onboarding.status == OnboardingStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_generate_onboarding_inactive_template(self, generator, sample_config):
        """Test generating onboarding from inactive template."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        # Don't activate
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme Corp"},
        )
        
        assert onboarding is None
    
    @pytest.mark.asyncio
    async def test_validate_tenant_data_valid(self, generator, sample_config):
        """Test validating valid tenant data."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        
        result = await generator.validate_tenant_data(
            template_id=template.template_id,
            tenant_data={
                "name": "Acme Corp",
                "domain": "acme.com",
                "admin_email": "admin@acme.com",
            },
        )
        
        assert result.is_valid is True
        assert len(result.issues) == 0
    
    @pytest.mark.asyncio
    async def test_validate_tenant_data_invalid(self, generator, sample_config):
        """Test validating invalid tenant data."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        
        result = await generator.validate_tenant_data(
            template_id=template.template_id,
            tenant_data={
                "name": "Ac",  # Too short
                "domain": "invalid_domain",
                "admin_email": "not_an_email",
            },
        )
        
        assert result.is_valid is False
        assert len(result.issues) > 0
    
    @pytest.mark.asyncio
    async def test_execute_onboarding(self, generator, sample_config):
        """Test executing onboarding."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme Corp", "domain": "acme.com"},
        )
        
        # Execute
        completed = await generator.execute_onboarding(onboarding.onboarding_id)
        
        assert completed.status in (OnboardingStatus.COMPLETED, OnboardingStatus.FAILED)
        assert completed.started_at is not None
        assert completed.progress_percentage == 100.0
    
    @pytest.mark.asyncio
    async def test_get_onboarding(self, generator, sample_config):
        """Test retrieving onboarding."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        created = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme Corp"},
        )
        
        retrieved = await generator.get_onboarding(created.onboarding_id)
        
        assert retrieved is not None
        assert retrieved.onboarding_id == created.onboarding_id
        assert retrieved.tenant_name == "Acme Corp"
    
    @pytest.mark.asyncio
    async def test_list_onboardings(self, generator, sample_config):
        """Test listing onboardings."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        # Create multiple onboardings
        for i in range(3):
            await generator.generate_onboarding(
                template_id=template.template_id,
                tenant_data={"name": f"Tenant {i}"},
            )
        
        onboardings = await generator.list_onboardings()
        assert len(onboardings) >= 3
    
    @pytest.mark.asyncio
    async def test_list_onboardings_by_status(self, generator, sample_config):
        """Test listing onboardings by status."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Test Tenant"},
        )
        
        pending = await generator.list_onboardings(status=OnboardingStatus.PENDING)
        assert len(pending) >= 1
    
    @pytest.mark.asyncio
    async def test_get_step_logs(self, generator, sample_config):
        """Test getting step logs."""
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme Corp", "domain": "acme.com"},
        )
        
        # Execute to generate logs
        await generator.execute_onboarding(onboarding.onboarding_id)
        
        logs = await generator.get_step_logs(onboarding.onboarding_id)
        
        assert len(logs) >= 1
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, generator, sample_config):
        """Test getting statistics."""
        # Create template and onboarding
        template = await generator.create_template(
            name="Test Template",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Test"},
        )
        
        stats = await generator.get_statistics()
        
        assert stats["total_templates"] >= 1
        assert stats["active_templates"] >= 1
        assert stats["total_onboardings"] >= 1
        assert "timestamp" in stats


class TestStepHandlers:
    """Test step handler functions."""
    
    @pytest.mark.asyncio
    async def test_validate_step(self, generator, sample_config):
        """Test validate step handler."""
        template = await generator.create_template(
            name="Test",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme", "domain": "acme.com"},
        )
        
        step = OnboardingStep(
            step_id="validate",
            name="Validate",
            action_type="validate",
            config={},
        )
        
        result = await generator._handle_validate_step(onboarding, step)
        
        assert result.success is True
        assert "is_valid" in result.output
    
    @pytest.mark.asyncio
    async def test_provision_step(self, generator, sample_config):
        """Test provision step handler."""
        template = await generator.create_template(
            name="Test",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme"},
        )
        
        step = OnboardingStep(
            step_id="provision",
            name="Provision",
            action_type="provision",
            config={"resource_type": "database"},
        )
        
        result = await generator._handle_provision_step(onboarding, step)
        
        assert result.success is True
        assert "resource_id" in result.output
    
    @pytest.mark.asyncio
    async def test_configure_step(self, generator, sample_config):
        """Test configure step handler."""
        template = await generator.create_template(
            name="Test",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme"},
        )
        
        step = OnboardingStep(
            step_id="configure",
            name="Configure",
            action_type="configure",
            config={"key": "setting", "value": "value"},
        )
        
        result = await generator._handle_configure_step(onboarding, step)
        
        assert result.success is True
        assert result.output["configured"] is True
    
    @pytest.mark.asyncio
    async def test_notify_step(self, generator, sample_config):
        """Test notify step handler."""
        template = await generator.create_template(
            name="Test",
            config=sample_config,
        )
        await generator.activate_template(template.template_id)
        
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Acme", "admin_email": "admin@acme.com"},
        )
        
        step = OnboardingStep(
            step_id="notify",
            name="Notify",
            action_type="notify",
            config={"type": "email"},
        )
        
        result = await generator._handle_notify_step(onboarding, step)
        
        assert result.success is True
        assert result.output["notification_sent"] is True


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, generator, sample_config):
        """Test validation with missing required fields."""
        template = await generator.create_template(
            name="Test",
            config=sample_config,
        )
        
        result = await generator.validate_tenant_data(
            template_id=template.template_id,
            tenant_data={"name": "Acme"},  # Missing domain and admin_email
        )
        
        assert result.is_valid is False
        assert any("domain" in str(issue) for issue in result.issues)
        assert any("admin_email" in str(issue) for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_circular_dependency_check(self, generator):
        """Test that circular dependencies are handled."""
        steps = [
            OnboardingStep(step_id="step_a", name="A", action_type="validate", config={}, dependencies=["step_b"]),
            OnboardingStep(step_id="step_b", name="B", action_type="validate", config={}, dependencies=["step_a"]),
        ]
        config = TemplateConfig(steps=steps, resources=[])
        
        template = await generator.create_template(
            name="Circular",
            config=config,
        )
        await generator.activate_template(template.template_id)
        
        # Execution should handle this gracefully
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Test"},
        )
        
        result = await generator.execute_onboarding(onboarding.onboarding_id)
        # May fail due to circular deps, but shouldn't crash
        assert result.status in (OnboardingStatus.COMPLETED, OnboardingStatus.FAILED)
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_onboarding(self, generator):
        """Test executing non-existent onboarding."""
        with pytest.raises(ValueError):
            await generator.execute_onboarding("nonexistent")


class TestIntegration:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_onboarding_workflow(self, async_engine):
        """Test complete onboarding workflow."""
        generator = OnboardingTemplateGenerator(async_engine)
        
        # Create tables
        async with async_engine.begin() as conn:
            for table_sql in [
                """CREATE TABLE IF NOT EXISTS onboarding_templates (
                    id INTEGER PRIMARY KEY,
                    template_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    version TEXT DEFAULT '1.0.0',
                    config TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    parent_template_id TEXT
                )""",
                """CREATE TABLE IF NOT EXISTS tenant_onboardings (
                    id INTEGER PRIMARY KEY,
                    onboarding_id TEXT UNIQUE NOT NULL,
                    template_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    tenant_name TEXT NOT NULL,
                    tenant_data TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    progress_percentage FLOAT DEFAULT 0,
                    current_step TEXT,
                    results TEXT DEFAULT '{}',
                    errors TEXT DEFAULT '[]'
                )""",
                """CREATE TABLE IF NOT EXISTS onboarding_step_logs (
                    id INTEGER PRIMARY KEY,
                    log_id TEXT UNIQUE NOT NULL,
                    onboarding_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT DEFAULT '{}',
                    error_message TEXT,
                    execution_time_ms FLOAT,
                    retry_count INTEGER DEFAULT 0,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
            ]:
                await conn.execute(text(table_sql))
        
        await generator.initialize()
        
        # 1. Create template
        resources = [
            ResourceConfig(ResourceType.DATABASE, "db", required=True),
            ResourceConfig(ResourceType.API_KEY, "key", required=True),
        ]
        steps = [
            OnboardingStep("step_1", "Validate", "validate", {}),
            OnboardingStep("step_2", "Provision", "provision", {"resource_type": "database"}, ["step_1"]),
            OnboardingStep("step_3", "Notify", "notify", {"type": "email"}, ["step_2"]),
        ]
        config = TemplateConfig(
            resources=resources,
            steps=steps,
            settings={"required_fields": ["name", "domain"]},
        )
        
        template = await generator.create_template(
            name="Integration Test",
            config=config,
        )
        
        # 2. Activate template
        await generator.activate_template(template.template_id)
        
        # 3. Generate onboarding
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "Integration Corp", "domain": "integration.com"},
        )
        
        # 4. Execute onboarding
        completed = await generator.execute_onboarding(onboarding.onboarding_id)
        
        # 5. Verify results
        assert completed.status in (OnboardingStatus.COMPLETED, OnboardingStatus.FAILED)
        
        # 6. Get logs
        logs = await generator.get_step_logs(onboarding.onboarding_id)
        assert len(logs) >= 2
        
        # 7. Get stats
        stats = await generator.get_statistics()
        assert stats["total_templates"] >= 1
        assert stats["total_onboardings"] >= 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
