"""
Multi-Tenant Onboarding Template Generator (#1439)

Provides a comprehensive system for generating and managing onboarding templates
for multi-tenant environments. Enables rapid tenant provisioning with customizable
configurations, validation, and automated setup workflows.

Features:
- Template creation and versioning
- Tenant configuration validation
- Resource provisioning automation
- Onboarding workflow management
- Progress tracking and reporting
- Custom field support
- Template inheritance and composition

Example:
    from api.utils.onboarding_template_generator import OnboardingTemplateGenerator, TemplateConfig
    
    generator = OnboardingTemplateGenerator()
    await generator.initialize()
    
    # Create onboarding template
    template = await generator.create_template(
        name="Enterprise Tenant Setup",
        config=TemplateConfig(
            resources=["database", "storage", "api_keys"],
            settings={"tier": "enterprise", "quota": 10000},
            steps=["verify_domain", "create_admin", "configure_sso"]
        )
    )
    
    # Generate tenant onboarding
    onboarding = await generator.generate_onboarding(
        template_id=template.template_id,
        tenant_data={"name": "Acme Corp", "domain": "acme.com"}
    )
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
from uuid import uuid4

from sqlalchemy import text, Column, String, DateTime, Integer, Boolean, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import declarative_base

from ..services.db_service import AsyncSessionLocal, engine


logger = logging.getLogger("api.onboarding_template_generator")

Base = declarative_base()


class TemplateStatus(str, Enum):
    """Status of an onboarding template."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class OnboardingStatus(str, Enum):
    """Status of a tenant onboarding process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    PROVISIONING = "provisioning"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ResourceType(str, Enum):
    """Types of resources that can be provisioned."""
    DATABASE = "database"
    STORAGE = "storage"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    DOMAIN = "domain"
    EMAIL = "email"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ResourceConfig:
    """Configuration for a resource to provision."""
    resource_type: ResourceType
    resource_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    required: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type.value,
            "resource_name": self.resource_name,
            "config": self.config,
            "dependencies": self.dependencies,
            "required": self.required,
        }


@dataclass
class OnboardingStep:
    """A step in the onboarding process."""
    step_id: str
    name: str
    description: Optional[str]
    action_type: str  # "validate", "provision", "configure", "notify"
    config: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    required: bool = True
    timeout_seconds: int = 300
    retry_count: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "config": self.config,
            "dependencies": self.dependencies,
            "required": self.required,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
        }


@dataclass
class TemplateConfig:
    """Configuration for an onboarding template."""
    resources: List[ResourceConfig] = field(default_factory=list)
    steps: List[OnboardingStep] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    validations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resources": [r.to_dict() for r in self.resources],
            "steps": [s.to_dict() for s in self.steps],
            "settings": self.settings,
            "validations": self.validations,
            "metadata": self.metadata,
        }


@dataclass
class OnboardingTemplate:
    """An onboarding template for multi-tenant setup."""
    template_id: str
    name: str
    description: Optional[str]
    version: str
    config: TemplateConfig
    status: TemplateStatus
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    parent_template_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "parent_template_id": self.parent_template_id,
        }


@dataclass
class TenantOnboarding:
    """A tenant onboarding instance."""
    onboarding_id: str
    template_id: str
    tenant_id: str
    tenant_name: str
    tenant_data: Dict[str, Any]
    status: OnboardingStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    current_step: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "onboarding_id": self.onboarding_id,
            "template_id": self.template_id,
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "tenant_data": self.tenant_data,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress_percentage": round(self.progress_percentage, 2),
            "current_step": self.current_step,
            "results": self.results,
            "errors": self.errors,
        }


@dataclass
class ValidationResult:
    """Result of validating tenant data."""
    is_valid: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
        }


@dataclass
class StepExecutionResult:
    """Result of executing an onboarding step."""
    step_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "output": self.output,
            "error_message": self.error_message,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "retry_count": self.retry_count,
        }


class OnboardingTemplateGenerator:
    """
    Generator for multi-tenant onboarding templates.
    
    Manages the creation, validation, and execution of onboarding templates
    for provisioning new tenants in a multi-tenant environment.
    
    Example:
        generator = OnboardingTemplateGenerator()
        await generator.initialize()
        
        # Create template
        template = await generator.create_template(
            name="Standard Tenant",
            config=TemplateConfig(...)
        )
        
        # Generate onboarding
        onboarding = await generator.generate_onboarding(
            template_id=template.template_id,
            tenant_data={"name": "New Tenant", "domain": "example.com"}
        )
        
        # Execute onboarding
        await generator.execute_onboarding(onboarding.onboarding_id)
    """
    
    def __init__(self, engine: Optional[AsyncEngine] = None):
        self.engine = engine
        self._templates: Dict[str, OnboardingTemplate] = {}
        self._onboardings: Dict[str, TenantOnboarding] = {}
        self._step_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default step handlers."""
        self._step_handlers["validate"] = self._handle_validate_step
        self._step_handlers["provision"] = self._handle_provision_step
        self._step_handlers["configure"] = self._handle_configure_step
        self._step_handlers["notify"] = self._handle_notify_step
    
    async def initialize(self) -> None:
        """Initialize the template generator."""
        await self._ensure_tables()
        logger.info("OnboardingTemplateGenerator initialized")
    
    async def _ensure_tables(self) -> None:
        """Ensure onboarding tables exist."""
        if not self.engine:
            from ..services.db_service import engine as db_engine
            self.engine = db_engine
        
        async with self.engine.begin() as conn:
            # Templates table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS onboarding_templates (
                    id SERIAL PRIMARY KEY,
                    template_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    version VARCHAR(50) DEFAULT '1.0.0',
                    config JSONB NOT NULL,
                    status VARCHAR(50) DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    created_by VARCHAR(255),
                    parent_template_id VARCHAR(255)
                )
            """))
            
            # Tenant onboardings table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tenant_onboardings (
                    id SERIAL PRIMARY KEY,
                    onboarding_id VARCHAR(255) UNIQUE NOT NULL,
                    template_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255) NOT NULL,
                    tenant_name VARCHAR(255) NOT NULL,
                    tenant_data JSONB DEFAULT '{}',
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    progress_percentage FLOAT DEFAULT 0,
                    current_step VARCHAR(255),
                    results JSONB DEFAULT '{}',
                    errors JSONB DEFAULT '[]'
                )
            """))
            
            # Onboarding steps log table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS onboarding_step_logs (
                    id SERIAL PRIMARY KEY,
                    log_id VARCHAR(255) UNIQUE NOT NULL,
                    onboarding_id VARCHAR(255) NOT NULL,
                    step_id VARCHAR(255) NOT NULL,
                    step_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    output JSONB DEFAULT '{}',
                    error_message TEXT,
                    execution_time_ms FLOAT,
                    retry_count INTEGER DEFAULT 0,
                    executed_at TIMESTAMP DEFAULT NOW()
                )
            """))
            
            # Create indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_template_status 
                ON onboarding_templates(status, created_at DESC)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_onboarding_status 
                ON tenant_onboardings(status, created_at DESC)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_onboarding_template 
                ON tenant_onboardings(template_id, status)
            """))
            
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_step_logs_onboarding 
                ON onboarding_step_logs(onboarding_id, executed_at DESC)
            """))
        
        logger.info("Onboarding tables ensured")
    
    async def create_template(
        self,
        name: str,
        config: TemplateConfig,
        description: Optional[str] = None,
        version: str = "1.0.0",
        created_by: Optional[str] = None,
        parent_template_id: Optional[str] = None
    ) -> OnboardingTemplate:
        """
        Create a new onboarding template.
        
        Args:
            name: Template name
            config: Template configuration
            description: Optional description
            version: Template version
            created_by: User who created the template
            parent_template_id: Parent template for inheritance
            
        Returns:
            Created OnboardingTemplate
        """
        template_id = f"tpl_{uuid4().hex[:12]}"
        
        template = OnboardingTemplate(
            template_id=template_id,
            name=name,
            description=description,
            version=version,
            config=config,
            status=TemplateStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=created_by,
            parent_template_id=parent_template_id,
        )
        
        # Persist to database
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO onboarding_templates (
                        template_id, name, description, version,
                        config, status, created_at, updated_at, created_by, parent_template_id
                    ) VALUES (
                        :template_id, :name, :description, :version,
                        :config, :status, :created_at, :updated_at, :created_by, :parent_template_id
                    )
                """),
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "description": template.description,
                    "version": template.version,
                    "config": json.dumps(template.config.to_dict()),
                    "status": template.status.value,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at,
                    "created_by": template.created_by,
                    "parent_template_id": template.parent_template_id,
                }
            )
            await session.commit()
        
        self._templates[template_id] = template
        logger.info(f"Created template {template_id}: {name}")
        
        return template
    
    async def get_template(self, template_id: str) -> Optional[OnboardingTemplate]:
        """Get a template by ID."""
        if template_id in self._templates:
            return self._templates[template_id]
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM onboarding_templates WHERE template_id = :template_id"),
                {"template_id": template_id}
            )
            row = result.fetchone()
            
            if row:
                template = OnboardingTemplate(
                    template_id=row.template_id,
                    name=row.name,
                    description=row.description,
                    version=row.version,
                    config=TemplateConfig(**row.config),
                    status=TemplateStatus(row.status),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    created_by=row.created_by,
                    parent_template_id=row.parent_template_id,
                )
                self._templates[template_id] = template
                return template
        
        return None
    
    async def list_templates(
        self,
        status: Optional[TemplateStatus] = None,
        limit: int = 100
    ) -> List[OnboardingTemplate]:
        """List onboarding templates."""
        templates = []
        
        async with AsyncSessionLocal() as session:
            if status:
                result = await session.execute(
                    text("""
                        SELECT * FROM onboarding_templates
                        WHERE status = :status
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"status": status.value, "limit": limit}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM onboarding_templates
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            
            for row in result:
                template = OnboardingTemplate(
                    template_id=row.template_id,
                    name=row.name,
                    description=row.description,
                    version=row.version,
                    config=TemplateConfig(**row.config),
                    status=TemplateStatus(row.status),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    created_by=row.created_by,
                    parent_template_id=row.parent_template_id,
                )
                templates.append(template)
                self._templates[row.template_id] = template
        
        return templates
    
    async def activate_template(self, template_id: str) -> bool:
        """Activate a template for use."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    UPDATE onboarding_templates
                    SET status = 'active', updated_at = NOW()
                    WHERE template_id = :template_id
                    RETURNING id
                """),
                {"template_id": template_id}
            )
            await session.commit()
            
            if result.fetchone():
                if template_id in self._templates:
                    self._templates[template_id].status = TemplateStatus.ACTIVE
                logger.info(f"Activated template {template_id}")
                return True
        
        return False
    
    async def generate_onboarding(
        self,
        template_id: str,
        tenant_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Optional[TenantOnboarding]:
        """
        Generate a tenant onboarding from a template.
        
        Args:
            template_id: Template ID
            tenant_data: Tenant configuration data
            tenant_id: Optional tenant ID (generated if not provided)
            
        Returns:
            TenantOnboarding or None if template not found
        """
        template = await self.get_template(template_id)
        if not template:
            return None
        
        if template.status != TemplateStatus.ACTIVE:
            logger.warning(f"Template {template_id} is not active")
            return None
        
        onboarding_id = f"onb_{uuid4().hex[:12]}"
        tenant_id = tenant_id or f"tnt_{uuid4().hex[:12]}"
        tenant_name = tenant_data.get("name", f"Tenant {tenant_id}")
        
        onboarding = TenantOnboarding(
            onboarding_id=onboarding_id,
            template_id=template_id,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            tenant_data=tenant_data,
            status=OnboardingStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        
        # Persist to database
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO tenant_onboardings (
                        onboarding_id, template_id, tenant_id, tenant_name,
                        tenant_data, status, created_at
                    ) VALUES (
                        :onboarding_id, :template_id, :tenant_id, :tenant_name,
                        :tenant_data, :status, :created_at
                    )
                """),
                {
                    "onboarding_id": onboarding.onboarding_id,
                    "template_id": onboarding.template_id,
                    "tenant_id": onboarding.tenant_id,
                    "tenant_name": onboarding.tenant_name,
                    "tenant_data": json.dumps(onboarding.tenant_data),
                    "status": onboarding.status.value,
                    "created_at": onboarding.created_at,
                }
            )
            await session.commit()
        
        self._onboardings[onboarding_id] = onboarding
        logger.info(f"Generated onboarding {onboarding_id} for tenant {tenant_id}")
        
        return onboarding
    
    async def validate_tenant_data(
        self,
        template_id: str,
        tenant_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate tenant data against template requirements.
        
        Args:
            template_id: Template ID
            tenant_data: Tenant data to validate
            
        Returns:
            ValidationResult with issues if any
        """
        template = await self.get_template(template_id)
        if not template:
            return ValidationResult(
                is_valid=False,
                issues=[{"severity": "error", "message": "Template not found"}]
            )
        
        issues = []
        
        # Check required fields
        required_fields = template.config.settings.get("required_fields", [])
        for field in required_fields:
            if field not in tenant_data or not tenant_data[field]:
                issues.append({
                    "severity": "error",
                    "field": field,
                    "message": f"Required field '{field}' is missing or empty"
                })
        
        # Validate domain format
        if "domain" in tenant_data:
            domain = tenant_data["domain"]
            if not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z0-9][-a-zA-Z0-9.]*$', domain):
                issues.append({
                    "severity": "error",
                    "field": "domain",
                    "message": f"Invalid domain format: {domain}"
                })
        
        # Validate email
        if "admin_email" in tenant_data:
            email = tenant_data["admin_email"]
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                issues.append({
                    "severity": "error",
                    "field": "admin_email",
                    "message": f"Invalid email format: {email}"
                })
        
        # Custom validations from template
        for validation in template.config.validations:
            field = validation.get("field")
            rule = validation.get("rule")
            message = validation.get("message", f"Validation failed for {field}")
            
            if field in tenant_data:
                value = tenant_data[field]
                if rule == "min_length" and len(str(value)) < validation.get("value", 0):
                    issues.append({"severity": "error", "field": field, "message": message})
                elif rule == "max_length" and len(str(value)) > validation.get("value", 100):
                    issues.append({"severity": "error", "field": field, "message": message})
                elif rule == "pattern" and not re.match(validation.get("value", ""), str(value)):
                    issues.append({"severity": "error", "field": field, "message": message})
        
        return ValidationResult(
            is_valid=len([i for i in issues if i["severity"] == "error"]) == 0,
            issues=issues
        )
    
    async def execute_onboarding(self, onboarding_id: str) -> TenantOnboarding:
        """
        Execute the onboarding process.
        
        Args:
            onboarding_id: Onboarding ID
            
        Returns:
            Updated TenantOnboarding
        """
        onboarding = await self.get_onboarding(onboarding_id)
        if not onboarding:
            raise ValueError(f"Onboarding {onboarding_id} not found")
        
        template = await self.get_template(onboarding.template_id)
        if not template:
            raise ValueError(f"Template {onboarding.template_id} not found")
        
        # Update status
        onboarding.status = OnboardingStatus.IN_PROGRESS
        onboarding.started_at = datetime.utcnow()
        await self._update_onboarding_status(onboarding)
        
        # Execute steps
        steps = template.config.steps
        completed_steps = 0
        total_steps = len(steps)
        
        for step in steps:
            # Check dependencies
            deps_satisfied = all(
                await self._is_step_completed(onboarding_id, dep)
                for dep in step.dependencies
            )
            
            if not deps_satisfied:
                logger.warning(f"Dependencies not satisfied for step {step.step_id}")
                continue
            
            # Update current step
            onboarding.current_step = step.step_id
            await self._update_onboarding_status(onboarding)
            
            # Execute step
            result = await self._execute_step(onboarding, step)
            
            # Log step execution
            await self._log_step_execution(onboarding_id, step, result)
            
            if result.success:
                completed_steps += 1
                onboarding.results[step.step_id] = result.output
            else:
                if step.required:
                    onboarding.status = OnboardingStatus.FAILED
                    onboarding.errors.append(f"Step {step.name} failed: {result.error_message}")
                    await self._update_onboarding_status(onboarding)
                    return onboarding
                else:
                    logger.warning(f"Optional step {step.step_id} failed, continuing")
            
            # Update progress
            onboarding.progress_percentage = (completed_steps / total_steps) * 100
            await self._update_onboarding_status(onboarding)
        
        # Mark as completed
        onboarding.status = OnboardingStatus.COMPLETED
        onboarding.completed_at = datetime.utcnow()
        onboarding.progress_percentage = 100.0
        await self._update_onboarding_status(onboarding)
        
        logger.info(f"Completed onboarding {onboarding_id}")
        return onboarding
    
    async def _execute_step(
        self,
        onboarding: TenantOnboarding,
        step: OnboardingStep
    ) -> StepExecutionResult:
        """Execute a single onboarding step."""
        import time
        
        start_time = time.time()
        handler = self._step_handlers.get(step.action_type)
        
        if not handler:
            return StepExecutionResult(
                step_id=step.step_id,
                success=False,
                error_message=f"No handler for action type: {step.action_type}",
                execution_time_ms=0,
            )
        
        # Execute with retries
        for attempt in range(step.retry_count + 1):
            try:
                result = await handler(onboarding, step)
                result.execution_time_ms = (time.time() - start_time) * 1000
                result.retry_count = attempt
                
                if result.success or attempt == step.retry_count:
                    return result
                
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                if attempt == step.retry_count:
                    return StepExecutionResult(
                        step_id=step.step_id,
                        success=False,
                        error_message=str(e),
                        execution_time_ms=(time.time() - start_time) * 1000,
                        retry_count=attempt,
                    )
                await asyncio.sleep(2 ** attempt)
        
        return StepExecutionResult(
            step_id=step.step_id,
            success=False,
            error_message="Max retries exceeded",
            execution_time_ms=(time.time() - start_time) * 1000,
            retry_count=step.retry_count,
        )
    
    async def _handle_validate_step(
        self,
        onboarding: TenantOnboarding,
        step: OnboardingStep
    ) -> StepExecutionResult:
        """Handle validation step."""
        validation_result = await self.validate_tenant_data(
            onboarding.template_id,
            onboarding.tenant_data
        )
        
        return StepExecutionResult(
            step_id=step.step_id,
            success=validation_result.is_valid,
            output=validation_result.to_dict(),
            error_message=None if validation_result.is_valid else "Validation failed",
        )
    
    async def _handle_provision_step(
        self,
        onboarding: TenantOnboarding,
        step: OnboardingStep
    ) -> StepExecutionResult:
        """Handle provisioning step."""
        resource_type = step.config.get("resource_type", "custom")
        
        # Simulate resource provisioning
        await asyncio.sleep(0.5)
        
        # Generate resource identifiers
        resource_id = f"res_{uuid4().hex[:12]}"
        
        return StepExecutionResult(
            step_id=step.step_id,
            success=True,
            output={
                "resource_id": resource_id,
                "resource_type": resource_type,
                "tenant_id": onboarding.tenant_id,
                "status": "provisioned",
            },
        )
    
    async def _handle_configure_step(
        self,
        onboarding: TenantOnboarding,
        step: OnboardingStep
    ) -> StepExecutionResult:
        """Handle configuration step."""
        config_key = step.config.get("key")
        config_value = step.config.get("value")
        
        # Simulate configuration
        await asyncio.sleep(0.3)
        
        return StepExecutionResult(
            step_id=step.step_id,
            success=True,
            output={
                "configured": True,
                "key": config_key,
                "value": config_value,
            },
        )
    
    async def _handle_notify_step(
        self,
        onboarding: TenantOnboarding,
        step: OnboardingStep
    ) -> StepExecutionResult:
        """Handle notification step."""
        notification_type = step.config.get("type", "email")
        recipient = step.config.get("recipient", onboarding.tenant_data.get("admin_email"))
        
        # Simulate sending notification
        logger.info(f"Sending {notification_type} notification to {recipient}")
        
        return StepExecutionResult(
            step_id=step.step_id,
            success=True,
            output={
                "notification_sent": True,
                "type": notification_type,
                "recipient": recipient,
            },
        )
    
    async def _is_step_completed(self, onboarding_id: str, step_id: str) -> bool:
        """Check if a step has been completed."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM onboarding_step_logs
                    WHERE onboarding_id = :onboarding_id
                    AND step_id = :step_id
                    AND status = 'success'
                """),
                {"onboarding_id": onboarding_id, "step_id": step_id}
            )
            return result.scalar() > 0
    
    async def _log_step_execution(
        self,
        onboarding_id: str,
        step: OnboardingStep,
        result: StepExecutionResult
    ) -> None:
        """Log step execution."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO onboarding_step_logs (
                        log_id, onboarding_id, step_id, step_name, status,
                        output, error_message, execution_time_ms, retry_count
                    ) VALUES (
                        :log_id, :onboarding_id, :step_id, :step_name, :status,
                        :output, :error_message, :execution_time_ms, :retry_count
                    )
                """),
                {
                    "log_id": f"log_{uuid4().hex[:12]}",
                    "onboarding_id": onboarding_id,
                    "step_id": step.step_id,
                    "step_name": step.name,
                    "status": "success" if result.success else "failed",
                    "output": json.dumps(result.output),
                    "error_message": result.error_message,
                    "execution_time_ms": result.execution_time_ms,
                    "retry_count": result.retry_count,
                }
            )
            await session.commit()
    
    async def _update_onboarding_status(self, onboarding: TenantOnboarding) -> None:
        """Update onboarding status in database."""
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE tenant_onboardings
                    SET status = :status,
                        progress_percentage = :progress,
                        current_step = :current_step,
                        results = :results,
                        errors = :errors,
                        started_at = :started_at,
                        completed_at = :completed_at
                    WHERE onboarding_id = :onboarding_id
                """),
                {
                    "onboarding_id": onboarding.onboarding_id,
                    "status": onboarding.status.value,
                    "progress": onboarding.progress_percentage,
                    "current_step": onboarding.current_step,
                    "results": json.dumps(onboarding.results),
                    "errors": json.dumps(onboarding.errors),
                    "started_at": onboarding.started_at,
                    "completed_at": onboarding.completed_at,
                }
            )
            await session.commit()
    
    async def get_onboarding(self, onboarding_id: str) -> Optional[TenantOnboarding]:
        """Get an onboarding by ID."""
        if onboarding_id in self._onboardings:
            return self._onboardings[onboarding_id]
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT * FROM tenant_onboardings WHERE onboarding_id = :onboarding_id"),
                {"onboarding_id": onboarding_id}
            )
            row = result.fetchone()
            
            if row:
                onboarding = TenantOnboarding(
                    onboarding_id=row.onboarding_id,
                    template_id=row.template_id,
                    tenant_id=row.tenant_id,
                    tenant_name=row.tenant_name,
                    tenant_data=row.tenant_data,
                    status=OnboardingStatus(row.status),
                    created_at=row.created_at,
                    started_at=row.started_at,
                    completed_at=row.completed_at,
                    progress_percentage=row.progress_percentage,
                    current_step=row.current_step,
                    results=row.results,
                    errors=row.errors,
                )
                self._onboardings[onboarding_id] = onboarding
                return onboarding
        
        return None
    
    async def list_onboardings(
        self,
        status: Optional[OnboardingStatus] = None,
        template_id: Optional[str] = None,
        limit: int = 100
    ) -> List[TenantOnboarding]:
        """List tenant onboardings."""
        onboardings = []
        
        async with AsyncSessionLocal() as session:
            if status and template_id:
                result = await session.execute(
                    text("""
                        SELECT * FROM tenant_onboardings
                        WHERE status = :status AND template_id = :template_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"status": status.value, "template_id": template_id, "limit": limit}
                )
            elif status:
                result = await session.execute(
                    text("""
                        SELECT * FROM tenant_onboardings
                        WHERE status = :status
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"status": status.value, "limit": limit}
                )
            elif template_id:
                result = await session.execute(
                    text("""
                        SELECT * FROM tenant_onboardings
                        WHERE template_id = :template_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"template_id": template_id, "limit": limit}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM tenant_onboardings
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            
            for row in result:
                onboarding = TenantOnboarding(
                    onboarding_id=row.onboarding_id,
                    template_id=row.template_id,
                    tenant_id=row.tenant_id,
                    tenant_name=row.tenant_name,
                    tenant_data=row.tenant_data,
                    status=OnboardingStatus(row.status),
                    created_at=row.created_at,
                    started_at=row.started_at,
                    completed_at=row.completed_at,
                    progress_percentage=row.progress_percentage,
                    current_step=row.current_step,
                    results=row.results,
                    errors=row.errors,
                )
                onboardings.append(onboarding)
                self._onboardings[row.onboarding_id] = onboarding
        
        return onboardings
    
    async def get_step_logs(self, onboarding_id: str) -> List[Dict[str, Any]]:
        """Get step execution logs for an onboarding."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT * FROM onboarding_step_logs
                    WHERE onboarding_id = :onboarding_id
                    ORDER BY executed_at ASC
                """),
                {"onboarding_id": onboarding_id}
            )
            
            logs = []
            for row in result:
                logs.append({
                    "log_id": row.log_id,
                    "step_id": row.step_id,
                    "step_name": row.step_name,
                    "status": row.status,
                    "execution_time_ms": row.execution_time_ms,
                    "retry_count": row.retry_count,
                    "executed_at": row.executed_at.isoformat(),
                })
            
            return logs
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics."""
        async with AsyncSessionLocal() as session:
            # Total templates
            result = await session.execute(
                text("SELECT COUNT(*) FROM onboarding_templates")
            )
            total_templates = result.scalar()
            
            # Active templates
            result = await session.execute(
                text("SELECT COUNT(*) FROM onboarding_templates WHERE status = 'active'")
            )
            active_templates = result.scalar()
            
            # Total onboardings
            result = await session.execute(
                text("SELECT COUNT(*) FROM tenant_onboardings")
            )
            total_onboardings = result.scalar()
            
            # By status
            result = await session.execute(
                text("""
                    SELECT status, COUNT(*) as count
                    FROM tenant_onboardings
                    GROUP BY status
                """)
            )
            status_counts = {r.status: r.count for r in result}
            
            # Recent completions (24h)
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM tenant_onboardings
                    WHERE status = 'completed'
                    AND completed_at > NOW() - INTERVAL '24 hours'
                """)
            )
            recent_completions = result.scalar()
            
            return {
                "total_templates": total_templates,
                "active_templates": active_templates,
                "total_onboardings": total_onboardings,
                "status_breakdown": status_counts,
                "recent_completions_24h": recent_completions,
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global instance
_template_generator: Optional[OnboardingTemplateGenerator] = None


async def get_template_generator(
    engine: Optional[AsyncEngine] = None
) -> OnboardingTemplateGenerator:
    """Get or create the global template generator."""
    global _template_generator
    
    if _template_generator is None:
        _template_generator = OnboardingTemplateGenerator(engine)
        await _template_generator.initialize()
    
    return _template_generator
