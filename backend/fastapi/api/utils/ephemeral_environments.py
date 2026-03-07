"""
Ephemeral Preview Environments Module

This module provides ephemeral preview environment management for pull requests,
enabling automatic creation, deployment, and cleanup of temporary environments
for testing and review purposes.

Features:
- Automatic environment provisioning on PR creation
- Environment lifecycle management
- Resource allocation and cleanup
- DNS and SSL management
- Environment status monitoring
- Cost tracking and budget enforcement
"""

import asyncio
import uuid
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class EnvironmentStatus(str, Enum):
    """Environment lifecycle status."""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    DEPLOYING = "deploying"
    RUNNING = "running"
    SLEEPING = "sleeping"  # Hibernated for cost savings
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class EnvironmentSize(str, Enum):
    """Environment resource sizing."""
    SMALL = "small"      # 0.5 CPU, 512MB RAM
    MEDIUM = "medium"    # 1 CPU, 1GB RAM
    LARGE = "large"      # 2 CPU, 2GB RAM
    XLARGE = "xlarge"    # 4 CPU, 4GB RAM


class EnvironmentType(str, Enum):
    """Type of ephemeral environment."""
    PULL_REQUEST = "pull_request"
    FEATURE_BRANCH = "feature_branch"
    HOTFIX = "hotfix"
    EXPERIMENTAL = "experimental"


class AccessLevel(str, Enum):
    """Access control levels."""
    PUBLIC = "public"           # Accessible to anyone
    ORGANIZATION = "organization"  # Accessible to org members
    TEAM = "team"              # Accessible to specific team
    RESTRICTED = "restricted"   # Accessible to specific users


@dataclass
class ResourceAllocation:
    """Resource allocation for an environment."""
    cpu_cores: float
    memory_mb: int
    storage_gb: int
    bandwidth_mbps: int = 100
    
    @classmethod
    def from_size(cls, size: EnvironmentSize) -> "ResourceAllocation":
        """Get resource allocation for environment size."""
        allocations = {
            EnvironmentSize.SMALL: cls(cpu_cores=0.5, memory_mb=512, storage_gb=5),
            EnvironmentSize.MEDIUM: cls(cpu_cores=1.0, memory_mb=1024, storage_gb=10),
            EnvironmentSize.LARGE: cls(cpu_cores=2.0, memory_mb=2048, storage_gb=20),
            EnvironmentSize.XLARGE: cls(cpu_cores=4.0, memory_mb=4096, storage_gb=50),
        }
        return allocations.get(size, allocations[EnvironmentSize.MEDIUM])


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    # Container configuration
    image_repository: str
    image_tag: str
    container_port: int = 8080
    
    # Environment variables
    env_vars: Dict[str, str] = field(default_factory=dict)
    secrets: List[str] = field(default_factory=list)
    
    # Health checks
    health_check_path: str = "/health"
    readiness_timeout_seconds: int = 60
    
    # Scaling
    min_replicas: int = 1
    max_replicas: int = 1
    
    # Build configuration
    build_command: Optional[str] = None
    start_command: Optional[str] = None


@dataclass
class DomainConfig:
    """Domain and SSL configuration."""
    subdomain: str
    domain: str
    full_domain: str = ""
    
    # SSL
    ssl_enabled: bool = True
    ssl_certificate_id: Optional[str] = None
    ssl_issuer: str = "letsencrypt"
    
    def __post_init__(self):
        if not self.full_domain:
            self.full_domain = f"{self.subdomain}.{self.domain}"


@dataclass
class EnvironmentMetrics:
    """Environment usage metrics."""
    # Resource usage
    cpu_usage_percent: float = 0.0
    memory_usage_mb: int = 0
    storage_usage_gb: float = 0.0
    
    # Traffic
    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0.0
    
    # Timing
    total_uptime_minutes: int = 0
    last_activity_at: Optional[datetime] = None
    
    # Cost
    estimated_cost_usd: float = 0.0


@dataclass
class PreviewEnvironment:
    """Ephemeral preview environment."""
    environment_id: str
    name: str
    environment_type: EnvironmentType
    
    # Source
    repository_url: str
    branch_name: str
    commit_sha: str
    
    # Configuration (required)
    size: EnvironmentSize
    resources: ResourceAllocation
    deployment_config: DeploymentConfig
    domain_config: DomainConfig
    
    # Source optional
    pull_request_number: Optional[int] = None
    
    # Configuration optional
    access_level: AccessLevel = AccessLevel.ORGANIZATION
    
    # Status
    status: EnvironmentStatus = EnvironmentStatus.PENDING
    status_message: str = ""
    
    # Lifecycle
    created_at: datetime = field(default_factory=datetime.utcnow)
    ready_at: Optional[datetime] = None
    last_deployed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    destroyed_at: Optional[datetime] = None
    
    # Access
    url: str = ""
    admin_url: str = ""
    access_token: str = ""
    allowed_users: List[str] = field(default_factory=list)
    allowed_teams: List[str] = field(default_factory=list)
    
    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # Metrics
    metrics: EnvironmentMetrics = field(default_factory=EnvironmentMetrics)
    
    # Cleanup
    auto_destroy_on_pr_close: bool = True
    auto_destroy_after_inactive_minutes: int = 480  # 8 hours
    notified_expiry: bool = False


@dataclass
class EnvironmentTemplate:
    """Template for creating environments."""
    template_id: str
    name: str
    description: str = ""
    
    # Default configuration
    default_size: EnvironmentSize = EnvironmentSize.MEDIUM
    default_access_level: AccessLevel = AccessLevel.ORGANIZATION
    default_ttl_hours: int = 24
    
    # Deployment defaults
    default_image_repository: str = ""
    default_container_port: int = 8080
    default_health_check_path: str = "/health"
    
    # Environment variables
    default_env_vars: Dict[str, str] = field(default_factory=dict)
    required_env_vars: List[str] = field(default_factory=list)
    
    # Domain
    domain_suffix: str = "preview.example.com"
    
    # Resources
    max_resources_per_env: ResourceAllocation = field(
        default_factory=lambda: ResourceAllocation(cpu_cores=4, memory_mb=4096, storage_gb=50)
    )


@dataclass
class EnvironmentBudget:
    """Budget for ephemeral environments."""
    budget_id: str
    name: str
    
    # Limits
    max_environments: int = 10
    max_concurrent_running: int = 5
    max_monthly_cost_usd: float = 1000.0
    max_ttl_hours: int = 72
    
    # Current usage
    current_environments: int = 0
    current_running: int = 0
    current_monthly_cost_usd: float = 0.0
    
    # Alerts
    alert_threshold_percent: float = 80.0
    alert_email: str = ""


@dataclass
class EnvironmentEvent:
    """Event log entry for environment."""
    event_id: str
    environment_id: str
    event_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class EphemeralEnvironmentManager:
    """
    Central manager for ephemeral preview environments.
    
    Provides functionality for:
    - Environment provisioning and lifecycle management
    - Resource allocation and monitoring
    - Domain and SSL management
    - Cost tracking and budget enforcement
    - Automated cleanup and expiration
    """
    
    # Cost per hour for each environment size (USD)
    COST_PER_HOUR = {
        EnvironmentSize.SMALL: 0.05,
        EnvironmentSize.MEDIUM: 0.10,
        EnvironmentSize.LARGE: 0.20,
        EnvironmentSize.XLARGE: 0.40,
    }
    
    def __init__(self):
        self.environments: Dict[str, PreviewEnvironment] = {}
        self.templates: Dict[str, EnvironmentTemplate] = {}
        self.budgets: Dict[str, EnvironmentBudget] = {}
        self.events: List[EnvironmentEvent] = []
        self._lock = asyncio.Lock()
        self._initialized = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the ephemeral environment manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default template
            default_template = EnvironmentTemplate(
                template_id="default",
                name="Default Preview Template",
                description="Standard configuration for preview environments",
                default_size=EnvironmentSize.MEDIUM,
                default_ttl_hours=24
            )
            self.templates["default"] = default_template
            
            # Create default budget
            default_budget = EnvironmentBudget(
                budget_id="default",
                name="Default Environment Budget",
                max_environments=20,
                max_concurrent_running=10,
                max_monthly_cost_usd=500.0
            )
            self.budgets["default"] = default_budget
            
            self._initialized = True
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            logger.info("EphemeralEnvironmentManager initialized successfully")
    
    async def shutdown(self):
        """Shutdown the manager and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    # Template Management
    
    async def create_template(
        self,
        template_id: str,
        name: str,
        description: str = "",
        default_size: EnvironmentSize = EnvironmentSize.MEDIUM,
        default_ttl_hours: int = 24,
        domain_suffix: str = "preview.example.com"
    ) -> EnvironmentTemplate:
        """Create an environment template."""
        async with self._lock:
            template = EnvironmentTemplate(
                template_id=template_id,
                name=name,
                description=description,
                default_size=default_size,
                default_ttl_hours=default_ttl_hours,
                domain_suffix=domain_suffix
            )
            
            self.templates[template_id] = template
            logger.info(f"Created environment template: {template_id}")
            return template
    
    async def get_template(self, template_id: str) -> Optional[EnvironmentTemplate]:
        """Get environment template by ID."""
        return self.templates.get(template_id)
    
    async def list_templates(self) -> List[EnvironmentTemplate]:
        """List all environment templates."""
        return list(self.templates.values())
    
    # Environment Lifecycle
    
    async def create_environment(
        self,
        name: str,
        environment_type: EnvironmentType,
        repository_url: str,
        branch_name: str,
        commit_sha: str,
        deployment_config: DeploymentConfig,
        pull_request_number: Optional[int] = None,
        size: Optional[EnvironmentSize] = None,
        template_id: str = "default",
        access_level: Optional[AccessLevel] = None,
        ttl_hours: int = 24,
        created_by: str = ""
    ) -> Optional[PreviewEnvironment]:
        """Create a new ephemeral preview environment."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            # Check budget limits
            budget = self.budgets.get("default")
            if budget and budget.current_environments >= budget.max_environments:
                logger.warning("Environment creation failed: budget limit reached")
                return None
            
            # Use template defaults if not specified
            size = size or template.default_size
            access_level = access_level or template.default_access_level
            
            # Generate environment ID and subdomain
            environment_id = f"env_{uuid.uuid4().hex[:12]}"
            subdomain = self._generate_subdomain(name, branch_name, pull_request_number)
            
            # Create domain config
            domain_config = DomainConfig(
                subdomain=subdomain,
                domain=template.domain_suffix
            )
            
            # Calculate expiration
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            # Create environment
            env = PreviewEnvironment(
                environment_id=environment_id,
                name=name,
                environment_type=environment_type,
                repository_url=repository_url,
                branch_name=branch_name,
                commit_sha=commit_sha,
                pull_request_number=pull_request_number,
                size=size,
                resources=ResourceAllocation.from_size(size),
                deployment_config=deployment_config,
                domain_config=domain_config,
                access_level=access_level,
                expires_at=expires_at,
                url=f"https://{domain_config.full_domain}",
                access_token=str(uuid.uuid4()),
                labels={
                    "created_by": created_by,
                    "template": template_id,
                    "pr": str(pull_request_number) if pull_request_number else "none"
                }
            )
            
            self.environments[environment_id] = env
            
            # Update budget
            if budget:
                budget.current_environments += 1
            
            # Log event
            await self._log_event(
                environment_id=environment_id,
                event_type="created",
                message=f"Environment created for branch {branch_name}",
                actor=created_by
            )
            
            # Start provisioning
            asyncio.create_task(self._provision_environment(environment_id))
            
            logger.info(f"Created environment: {environment_id}")
            return env
    
    def _generate_subdomain(
        self,
        name: str,
        branch_name: str,
        pull_request_number: Optional[int] = None
    ) -> str:
        """Generate a subdomain for the environment."""
        # Sanitize name and branch
        clean_name = re.sub(r'[^a-z0-9-]', '-', name.lower())[:20]
        clean_branch = re.sub(r'[^a-z0-9-]', '-', branch_name.lower())[:20]
        
        if pull_request_number:
            return f"pr-{pull_request_number}-{clean_name}"
        else:
            return f"{clean_branch}-{clean_name}"
    
    async def _provision_environment(self, environment_id: str):
        """Provision the environment infrastructure."""
        env = self.environments.get(environment_id)
        if not env:
            return
        
        env.status = EnvironmentStatus.PROVISIONING
        env.status_message = "Provisioning infrastructure..."
        
        # Simulate provisioning delay
        await asyncio.sleep(1)
        
        # Update status
        env.status = EnvironmentStatus.READY
        env.status_message = "Infrastructure ready, awaiting deployment"
        env.ready_at = datetime.utcnow()
        
        await self._log_event(
            environment_id=environment_id,
            event_type="provisioned",
            message="Environment infrastructure provisioned"
        )
        
        # Auto-deploy if configured
        await self.deploy_environment(environment_id)
    
    async def deploy_environment(
        self,
        environment_id: str,
        deployed_by: str = ""
    ) -> bool:
        """Deploy application to environment."""
        env = self.environments.get(environment_id)
        if not env:
            return False
        
        if env.status not in [EnvironmentStatus.READY, EnvironmentStatus.RUNNING]:
            return False
        
        env.status = EnvironmentStatus.DEPLOYING
        env.status_message = "Deploying application..."
        
        # Simulate deployment
        await asyncio.sleep(1)
        
        env.status = EnvironmentStatus.RUNNING
        env.status_message = "Environment running and accessible"
        env.last_deployed_at = datetime.utcnow()
        
        # Update budget
        budget = self.budgets.get("default")
        if budget:
            budget.current_running += 1
        
        await self._log_event(
            environment_id=environment_id,
            event_type="deployed",
            message=f"Application deployed: {env.deployment_config.image_repository}:{env.deployment_config.image_tag}",
            actor=deployed_by
        )
        
        logger.info(f"Deployed environment: {environment_id}")
        return True
    
    async def destroy_environment(
        self,
        environment_id: str,
        destroyed_by: str = "",
        reason: str = ""
    ) -> bool:
        """Destroy an ephemeral environment."""
        async with self._lock:
            env = self.environments.get(environment_id)
            if not env:
                return False
            
            if env.status == EnvironmentStatus.DESTROYED:
                return True
            
            env.status = EnvironmentStatus.DESTROYING
            env.status_message = "Destroying environment..."
            
            # Simulate cleanup
            await asyncio.sleep(1)
            
            env.status = EnvironmentStatus.DESTROYED
            env.status_message = "Environment destroyed"
            env.destroyed_at = datetime.utcnow()
            
            # Update budget
            budget = self.budgets.get("default")
            if budget:
                budget.current_environments -= 1
                if env.status == EnvironmentStatus.RUNNING:
                    budget.current_running -= 1
            
            await self._log_event(
                environment_id=environment_id,
                event_type="destroyed",
                message=f"Environment destroyed: {reason}",
                actor=destroyed_by
            )
            
            logger.info(f"Destroyed environment: {environment_id}")
            return True
    
    async def get_environment(self, environment_id: str) -> Optional[PreviewEnvironment]:
        """Get environment by ID."""
        return self.environments.get(environment_id)
    
    async def list_environments(
        self,
        status: Optional[EnvironmentStatus] = None,
        environment_type: Optional[EnvironmentType] = None,
        branch_name: Optional[str] = None
    ) -> List[PreviewEnvironment]:
        """List environments with optional filtering."""
        environments = list(self.environments.values())
        
        if status:
            environments = [e for e in environments if e.status == status]
        
        if environment_type:
            environments = [e for e in environments if e.environment_type == environment_type]
        
        if branch_name:
            environments = [e for e in environments if e.branch_name == branch_name]
        
        return sorted(environments, key=lambda e: e.created_at, reverse=True)
    
    # Event Logging
    
    async def _log_event(
        self,
        environment_id: str,
        event_type: str,
        message: str,
        actor: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an environment event."""
        event = EnvironmentEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            environment_id=environment_id,
            event_type=event_type,
            message=message,
            actor=actor,
            metadata=metadata or {}
        )
        
        self.events.append(event)
    
    async def get_environment_events(
        self,
        environment_id: str,
        event_type: Optional[str] = None
    ) -> List[EnvironmentEvent]:
        """Get events for an environment."""
        events = [e for e in self.events if e.environment_id == environment_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)
    
    # Metrics and Monitoring
    
    async def update_metrics(
        self,
        environment_id: str,
        cpu_usage_percent: float = None,
        memory_usage_mb: int = None,
        request_count: int = None,
        error_count: int = None
    ) -> bool:
        """Update environment metrics."""
        env = self.environments.get(environment_id)
        if not env:
            return False
        
        metrics = env.metrics
        
        if cpu_usage_percent is not None:
            metrics.cpu_usage_percent = cpu_usage_percent
        
        if memory_usage_mb is not None:
            metrics.memory_usage_mb = memory_usage_mb
        
        if request_count is not None:
            metrics.request_count = request_count
        
        if error_count is not None:
            metrics.error_count = error_count
        
        metrics.last_activity_at = datetime.utcnow()
        
        return True
    
    async def get_metrics(self, environment_id: str) -> Optional[EnvironmentMetrics]:
        """Get environment metrics."""
        env = self.environments.get(environment_id)
        return env.metrics if env else None
    
    # Budget Management
    
    async def get_budget(self, budget_id: str = "default") -> Optional[EnvironmentBudget]:
        """Get budget by ID."""
        return self.budgets.get(budget_id)
    
    async def update_budget_usage(self):
        """Update current budget usage based on active environments."""
        budget = self.budgets.get("default")
        if not budget:
            return
        
        total_cost = 0.0
        running_count = 0
        
        for env in self.environments.values():
            if env.status == EnvironmentStatus.RUNNING:
                running_count += 1
                # Calculate cost based on uptime
                uptime_hours = (datetime.utcnow() - (env.ready_at or env.created_at)).total_seconds() / 3600
                total_cost += uptime_hours * self.COST_PER_HOUR.get(env.size, 0.10)
        
        budget.current_running = running_count
        budget.current_monthly_cost_usd = total_cost
    
    # Cleanup Loop
    
    async def _cleanup_loop(self):
        """Background task for environment cleanup."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                now = datetime.utcnow()
                
                for env in list(self.environments.values()):
                    # Skip already destroyed environments
                    if env.status in [EnvironmentStatus.DESTROYED, EnvironmentStatus.DESTROYING]:
                        continue
                    
                    # Check expiration
                    if env.expires_at and env.expires_at <= now:
                        logger.info(f"Environment {env.environment_id} expired, destroying...")
                        await self.destroy_environment(
                            env.environment_id,
                            reason="TTL expired"
                        )
                        continue
                    
                    # Check inactivity
                    if env.status == EnvironmentStatus.RUNNING and env.auto_destroy_after_inactive_minutes:
                        last_activity = env.metrics.last_activity_at or env.last_deployed_at
                        if last_activity:
                            inactive_minutes = (now - last_activity).total_seconds() / 60
                            if inactive_minutes >= env.auto_destroy_after_inactive_minutes:
                                logger.info(f"Environment {env.environment_id} inactive, destroying...")
                                await self.destroy_environment(
                                    env.environment_id,
                                    reason="Inactive timeout"
                                )
                
                # Update budget
                await self.update_budget_usage()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    # PR Integration
    
    async def handle_pr_event(
        self,
        action: str,
        pull_request_number: int,
        branch_name: str,
        commit_sha: str,
        repository_url: str,
        sender: str = ""
    ) -> Optional[PreviewEnvironment]:
        """Handle pull request events."""
        if action == "opened" or action == "synchronize":
            # Check if environment already exists for this PR
            existing = None
            for env in self.environments.values():
                if env.pull_request_number == pull_request_number and env.status != EnvironmentStatus.DESTROYED:
                    existing = env
                    break
            
            if existing:
                # Update existing environment with new commit
                existing.commit_sha = commit_sha
                existing.status = EnvironmentStatus.DEPLOYING
                existing.status_message = "Updating to new commit..."
                asyncio.create_task(self.deploy_environment(existing.environment_id, sender))
                return existing
            else:
                # Create new environment
                deployment_config = DeploymentConfig(
                    image_repository=f"{repository_url}/{branch_name}",
                    image_tag=commit_sha[:8]
                )
                
                return await self.create_environment(
                    name=f"pr-{pull_request_number}",
                    environment_type=EnvironmentType.PULL_REQUEST,
                    repository_url=repository_url,
                    branch_name=branch_name,
                    commit_sha=commit_sha,
                    deployment_config=deployment_config,
                    pull_request_number=pull_request_number,
                    created_by=sender
                )
        
        elif action == "closed":
            # Destroy environments for this PR
            for env in list(self.environments.values()):
                if env.pull_request_number == pull_request_number:
                    if env.auto_destroy_on_pr_close:
                        await self.destroy_environment(
                            env.environment_id,
                            destroyed_by=sender,
                            reason="Pull request closed"
                        )
            return None
        
        return None
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get environment statistics."""
        environments = list(self.environments.values())
        running = [e for e in environments if e.status == EnvironmentStatus.RUNNING]
        
        # Calculate costs
        total_cost = sum(
            ((e.destroyed_at or datetime.utcnow()) - e.created_at).total_seconds() / 3600 *
            self.COST_PER_HOUR.get(e.size, 0.10)
            for e in environments
        )
        
        return {
            "environments": {
                "total": len(environments),
                "running": len(running),
                "by_status": {
                    status.value: len([e for e in environments if e.status == status])
                    for status in EnvironmentStatus
                },
                "by_type": {
                    et.value: len([e for e in environments if e.environment_type == et])
                    for et in EnvironmentType
                },
                "by_size": {
                    size.value: len([e for e in environments if e.size == size])
                    for size in EnvironmentSize
                }
            },
            "resources": {
                "total_cpu_cores": sum(e.resources.cpu_cores for e in running),
                "total_memory_mb": sum(e.resources.memory_mb for e in running),
                "total_storage_gb": sum(e.resources.storage_gb for e in running)
            },
            "cost": {
                "total_usd": round(total_cost, 2),
                "running_per_hour": round(
                    sum(self.COST_PER_HOUR.get(e.size, 0.10) for e in running), 2
                )
            }
        }


# Global manager instance
_ephemeral_manager: Optional[EphemeralEnvironmentManager] = None


async def get_ephemeral_manager() -> EphemeralEnvironmentManager:
    """Get or create the global ephemeral environment manager."""
    global _ephemeral_manager
    if _ephemeral_manager is None:
        _ephemeral_manager = EphemeralEnvironmentManager()
        await _ephemeral_manager.initialize()
    return _ephemeral_manager


def reset_ephemeral_manager():
    """Reset the global ephemeral environment manager (for testing)."""
    global _ephemeral_manager
    _ephemeral_manager = None
