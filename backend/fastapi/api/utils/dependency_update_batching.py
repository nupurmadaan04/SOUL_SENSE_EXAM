"""
Dependency Update Batching with Risk Tiers Module

This module provides intelligent dependency update management with risk-based
tier classification, batching strategies, and safe rollout controls.

Features:
- Dependency update tracking and management
- Risk tier classification (critical, high, medium, low)
- Batching strategies (security, feature, patch, all)
- Update scheduling and approval workflows
- Rollback capabilities
- Compatibility checking
"""

import asyncio
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    """Type of dependency update."""
    SECURITY = "security"      # Security patch
    BUGFIX = "bugfix"          # Bug fix
    FEATURE = "feature"        # New feature
    PERFORMANCE = "performance"  # Performance improvement
    BREAKING = "breaking"      # Breaking change
    DEPRECATED = "deprecated"  # Deprecation notice


class RiskTier(str, Enum):
    """Risk tier for dependency updates."""
    CRITICAL = "critical"      # Immediate action required
    HIGH = "high"              # Update within 1 week
    MEDIUM = "medium"          # Update within 1 month
    LOW = "low"                # Update when convenient
    INFO = "info"              # Informational only


class UpdateStatus(str, Enum):
    """Status of dependency update."""
    PENDING = "pending"        # Awaiting processing
    ANALYZING = "analyzing"    # Under risk analysis
    APPROVED = "approved"      # Approved for deployment
    REJECTED = "rejected"      # Rejected
    SCHEDULED = "scheduled"    # Scheduled for deployment
    DEPLOYING = "deploying"    # Currently deploying
    DEPLOYED = "deployed"      # Successfully deployed
    ROLLED_BACK = "rolled_back"  # Rolled back
    FAILED = "failed"          # Deployment failed


class BatchingStrategy(str, Enum):
    """Strategy for batching updates."""
    SECURITY_ONLY = "security_only"      # Security updates only
    PATCH_ONLY = "patch_only"            # Patch updates only
    MINOR_ONLY = "minor_only"            # Minor updates only
    ALL_EXCEPT_MAJOR = "all_except_major"  # All except major
    ALL = "all"                          # All updates
    CUSTOM = "custom"                    # Custom criteria


class CompatibilityStatus(str, Enum):
    """Compatibility check status."""
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"
    REQUIRES_TESTING = "requires_testing"


@dataclass
class Dependency:
    """Dependency definition."""
    name: str
    current_version: str
    ecosystem: str  # npm, pypi, maven, etc.
    
    # Metadata
    direct_dependency: bool = True  # True if direct, False if transitive
    usage_scope: str = "production"  # production, development, test
    
    # Vulnerabilities
    known_vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    
    # License
    license_type: str = ""
    license_compliant: bool = True


@dataclass
class AvailableUpdate:
    """Available update for a dependency."""
    update_id: str
    dependency: Dependency
    new_version: str
    update_type: UpdateType
    
    # Risk assessment
    risk_tier: RiskTier
    risk_score: float  # 0.0 to 10.0
    
    # Change analysis
    changelog_summary: str = ""
    breaking_changes: List[str] = field(default_factory=list)
    security_fixes: List[str] = field(default_factory=list)
    
    # Compatibility
    compatibility_status: CompatibilityStatus = CompatibilityStatus.UNKNOWN
    test_coverage: float = 0.0  # Percentage of code covered by tests
    
    # Metadata
    published_at: Optional[datetime] = None
    discovered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UpdateBatch:
    """Batch of dependency updates."""
    batch_id: str
    name: str
    strategy: BatchingStrategy
    
    # Updates in batch
    updates: List[AvailableUpdate] = field(default_factory=list)
    
    # Optional fields
    description: str = ""
    
    # Risk summary
    highest_risk_tier: RiskTier = RiskTier.LOW
    total_risk_score: float = 0.0
    
    # Status
    status: UpdateStatus = UpdateStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    
    # Approval
    requires_approval: bool = True
    approved_by: str = ""
    approved_at: Optional[datetime] = None
    
    # Rollback
    can_rollback: bool = True
    rollback_available_until: Optional[datetime] = None


@dataclass
class DeploymentResult:
    """Result of update deployment."""
    deployment_id: str
    batch_id: str
    status: UpdateStatus
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Results per update
    successful_updates: List[str] = field(default_factory=list)
    failed_updates: List[str] = field(default_factory=list)
    skipped_updates: List[str] = field(default_factory=list)
    
    # Logs
    deployment_logs: List[str] = field(default_factory=list)
    error_message: str = ""
    
    # Rollback info
    rollback_commit: str = ""


@dataclass
class RiskAssessmentRule:
    """Rule for assessing update risk."""
    rule_id: str
    name: str
    description: str = ""
    
    # Criteria
    min_cvss_score: Optional[float] = None
    max_version_change: Optional[str] = None  # major, minor, patch
    requires_manual_review: bool = False
    
    # Risk assignment
    risk_tier: RiskTier = RiskTier.MEDIUM
    risk_score_modifier: float = 0.0


@dataclass
class DependencyPolicy:
    """Policy for dependency updates."""
    policy_id: str
    name: str
    
    # Auto-update settings
    auto_merge_security_updates: bool = False
    auto_merge_patch_updates: bool = False
    auto_merge_minor_updates: bool = False
    
    # Approval requirements
    require_approval_for_breaking: bool = True
    require_approval_for_major: bool = True
    require_approval_for_high_risk: bool = True
    
    # Scheduling
    maintenance_window_start: str = "02:00"  # 24-hour format
    maintenance_window_end: str = "04:00"
    maintenance_window_days: List[str] = field(default_factory=lambda: ["Saturday", "Sunday"])
    
    # Exclusions
    excluded_packages: List[str] = field(default_factory=list)
    excluded_version_patterns: List[str] = field(default_factory=list)


class DependencyUpdateManager:
    """
    Central manager for dependency update batching with risk tiers.
    
    Provides functionality for:
    - Dependency tracking and monitoring
    - Risk assessment and tier classification
    - Update batching strategies
    - Deployment scheduling and approval
    - Rollback management
    """
    
    def __init__(self):
        self.dependencies: Dict[str, Dependency] = {}
        self.available_updates: Dict[str, AvailableUpdate] = {}
        self.batches: Dict[str, UpdateBatch] = {}
        self.deployment_results: Dict[str, DeploymentResult] = {}
        self.risk_rules: List[RiskAssessmentRule] = []
        self.policies: Dict[str, DependencyPolicy] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the dependency update manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default risk assessment rules
            await self._create_default_risk_rules()
            
            # Create default policy
            default_policy = DependencyPolicy(
                policy_id="default",
                name="Default Dependency Policy",
                auto_merge_security_updates=True,
                require_approval_for_breaking=True,
                require_approval_for_major=True
            )
            self.policies["default"] = default_policy
            
            self._initialized = True
            logger.info("DependencyUpdateManager initialized successfully")
    
    async def _create_default_risk_rules(self):
        """Create default risk assessment rules."""
        rules = [
            RiskAssessmentRule(
                rule_id="critical_security",
                name="Critical Security Vulnerability",
                description="Updates fixing critical security vulnerabilities",
                min_cvss_score=9.0,
                risk_tier=RiskTier.CRITICAL,
                risk_score_modifier=10.0
            ),
            RiskAssessmentRule(
                rule_id="high_security",
                name="High Security Vulnerability",
                description="Updates fixing high severity security vulnerabilities",
                min_cvss_score=7.0,
                risk_tier=RiskTier.HIGH,
                risk_score_modifier=7.0
            ),
            RiskAssessmentRule(
                rule_id="breaking_change",
                name="Breaking Change",
                description="Updates with breaking changes",
                max_version_change="major",
                risk_tier=RiskTier.HIGH,
                requires_manual_review=True,
                risk_score_modifier=6.0
            ),
            RiskAssessmentRule(
                rule_id="minor_update",
                name="Minor Update",
                description="Minor version updates with new features",
                max_version_change="minor",
                risk_tier=RiskTier.MEDIUM,
                risk_score_modifier=3.0
            ),
            RiskAssessmentRule(
                rule_id="patch_update",
                name="Patch Update",
                description="Patch updates (bug fixes)",
                max_version_change="patch",
                risk_tier=RiskTier.LOW,
                risk_score_modifier=1.0
            ),
        ]
        
        self.risk_rules = rules
    
    # Dependency Management
    
    async def register_dependency(
        self,
        name: str,
        current_version: str,
        ecosystem: str,
        direct_dependency: bool = True,
        usage_scope: str = "production"
    ) -> Dependency:
        """Register a dependency for tracking."""
        async with self._lock:
            dep = Dependency(
                name=name,
                current_version=current_version,
                ecosystem=ecosystem,
                direct_dependency=direct_dependency,
                usage_scope=usage_scope
            )
            
            self.dependencies[name] = dep
            logger.info(f"Registered dependency: {name}@{current_version}")
            return dep
    
    async def get_dependency(self, name: str) -> Optional[Dependency]:
        """Get dependency by name."""
        return self.dependencies.get(name)
    
    async def list_dependencies(
        self,
        ecosystem: Optional[str] = None,
        direct_only: bool = False
    ) -> List[Dependency]:
        """List dependencies with optional filtering."""
        deps = list(self.dependencies.values())
        
        if ecosystem:
            deps = [d for d in deps if d.ecosystem == ecosystem]
        
        if direct_only:
            deps = [d for d in deps if d.direct_dependency]
        
        return deps
    
    # Risk Assessment
    
    async def assess_update_risk(
        self,
        dependency: Dependency,
        new_version: str,
        update_type: UpdateType,
        changelog: str = "",
        vulnerabilities: Optional[List[Dict]] = None
    ) -> Tuple[RiskTier, float]:
        """Assess risk tier and score for an update."""
        base_score = 0.0
        highest_tier = RiskTier.LOW
        
        # Risk tier priority order for comparison
        tier_priority = {
            RiskTier.INFO: 0,
            RiskTier.LOW: 1,
            RiskTier.MEDIUM: 2,
            RiskTier.HIGH: 3,
            RiskTier.CRITICAL: 4
        }
        
        def get_higher_tier(tier1: RiskTier, tier2: RiskTier) -> RiskTier:
            return tier1 if tier_priority[tier1] >= tier_priority[tier2] else tier2
        
        # Check security vulnerabilities
        if vulnerabilities:
            for vuln in vulnerabilities:
                cvss_score = vuln.get("cvss_score", 0.0)
                if cvss_score >= 9.0:
                    return RiskTier.CRITICAL, 10.0
                elif cvss_score >= 7.0:
                    highest_tier = get_higher_tier(highest_tier, RiskTier.HIGH)
                    base_score = max(base_score, 7.0)
        
        # Check update type
        if update_type == UpdateType.SECURITY:
            highest_tier = get_higher_tier(highest_tier, RiskTier.HIGH)
            base_score += 5.0
        elif update_type == UpdateType.BREAKING:
            highest_tier = get_higher_tier(highest_tier, RiskTier.HIGH)
            base_score += 6.0
        elif update_type == UpdateType.FEATURE:
            highest_tier = get_higher_tier(highest_tier, RiskTier.MEDIUM)
            base_score += 3.0
        elif update_type == UpdateType.BUGFIX:
            base_score += 1.0
        
        # Check version change type
        version_diff = self._get_version_diff(dependency.current_version, new_version)
        if version_diff == "major":
            highest_tier = get_higher_tier(highest_tier, RiskTier.HIGH)
            base_score += 4.0
        elif version_diff == "minor":
            highest_tier = get_higher_tier(highest_tier, RiskTier.MEDIUM)
            base_score += 2.0
        elif version_diff == "patch":
            base_score += 0.5
        
        # Cap score at 10
        final_score = min(base_score, 10.0)
        
        return highest_tier, final_score
    
    def _get_version_diff(self, current: str, new: str) -> str:
        """Determine version change type."""
        try:
            # Remove 'v' prefix if present
            current_clean = current.lstrip('v')
            new_clean = new.lstrip('v')
            
            current_parts = [int(x) for x in re.split(r'[.-]', current_clean)[:3]]
            new_parts = [int(x) for x in re.split(r'[.-]', new_clean)[:3]]
            
            # Ensure both lists have at least 3 elements
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(new_parts) < 3:
                new_parts.append(0)
            
            if new_parts[0] > current_parts[0]:
                return "major"
            elif new_parts[1] > current_parts[1]:
                return "minor"
            elif new_parts[2] > current_parts[2]:
                return "patch"
        except (ValueError, IndexError, AttributeError):
            pass
        
        return "unknown"
    
    # Update Management
    
    async def register_available_update(
        self,
        dependency_name: str,
        new_version: str,
        update_type: UpdateType,
        changelog: str = "",
        vulnerabilities: Optional[List[Dict]] = None,
        published_at: Optional[datetime] = None
    ) -> Optional[AvailableUpdate]:
        """Register an available update for a dependency."""
        async with self._lock:
            dep = self.dependencies.get(dependency_name)
            if not dep:
                return None
            
            # Assess risk
            risk_tier, risk_score = await self.assess_update_risk(
                dep, new_version, update_type, changelog, vulnerabilities
            )
            
            update_id = f"update_{dependency_name}_{new_version}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            update = AvailableUpdate(
                update_id=update_id,
                dependency=dep,
                new_version=new_version,
                update_type=update_type,
                risk_tier=risk_tier,
                risk_score=risk_score,
                changelog_summary=changelog[:500] if changelog else "",
                security_fixes=[v.get("cve_id", "CVE-unknown") for v in (vulnerabilities or [])],
                published_at=published_at,
                discovered_at=datetime.utcnow()
            )
            
            self.available_updates[update_id] = update
            
            logger.info(f"Registered available update: {dependency_name}@{new_version} (Risk: {risk_tier.value})")
            return update
    
    async def get_available_update(self, update_id: str) -> Optional[AvailableUpdate]:
        """Get available update by ID."""
        return self.available_updates.get(update_id)
    
    async def list_available_updates(
        self,
        risk_tier: Optional[RiskTier] = None,
        update_type: Optional[UpdateType] = None
    ) -> List[AvailableUpdate]:
        """List available updates with optional filtering."""
        updates = list(self.available_updates.values())
        
        if risk_tier:
            updates = [u for u in updates if u.risk_tier == risk_tier]
        
        if update_type:
            updates = [u for u in updates if u.update_type == update_type]
        
        return sorted(updates, key=lambda u: u.risk_score, reverse=True)
    
    # Batching
    
    async def create_batch(
        self,
        name: str,
        description: str,
        strategy: BatchingStrategy,
        update_ids: List[str],
        policy_id: str = "default"
    ) -> Optional[UpdateBatch]:
        """Create a batch of updates."""
        async with self._lock:
            # Validate all updates exist
            updates = []
            for update_id in update_ids:
                update = self.available_updates.get(update_id)
                if update:
                    updates.append(update)
            
            if not updates:
                return None
            
            batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(self.batches):04d}"
            
            # Calculate batch risk
            highest_risk = max((u.risk_tier for u in updates), key=lambda r: list(RiskTier).index(r))
            total_risk = sum(u.risk_score for u in updates)
            
            # Get policy
            policy = self.policies.get(policy_id, self.policies["default"])
            
            batch = UpdateBatch(
                batch_id=batch_id,
                name=name,
                description=description,
                strategy=strategy,
                updates=updates,
                highest_risk_tier=highest_risk,
                total_risk_score=total_risk,
                requires_approval=highest_risk in [RiskTier.HIGH, RiskTier.CRITICAL] or 
                                  policy.require_approval_for_high_risk
            )
            
            self.batches[batch_id] = batch
            
            logger.info(f"Created update batch: {batch_id} with {len(updates)} updates")
            return batch
    
    async def get_batch(self, batch_id: str) -> Optional[UpdateBatch]:
        """Get batch by ID."""
        return self.batches.get(batch_id)
    
    async def list_batches(
        self,
        status: Optional[UpdateStatus] = None,
        strategy: Optional[BatchingStrategy] = None
    ) -> List[UpdateBatch]:
        """List batches with optional filtering."""
        batches = list(self.batches.values())
        
        if status:
            batches = [b for b in batches if b.status == status]
        
        if strategy:
            batches = [b for b in batches if b.strategy == strategy]
        
        return sorted(batches, key=lambda b: b.created_at, reverse=True)
    
    async def approve_batch(
        self,
        batch_id: str,
        approved_by: str
    ) -> Optional[UpdateBatch]:
        """Approve a batch for deployment."""
        async with self._lock:
            batch = self.batches.get(batch_id)
            if not batch:
                return None
            
            batch.status = UpdateStatus.APPROVED
            batch.approved_by = approved_by
            batch.approved_at = datetime.utcnow()
            
            logger.info(f"Batch {batch_id} approved by {approved_by}")
            return batch
    
    async def schedule_batch(
        self,
        batch_id: str,
        scheduled_at: datetime
    ) -> Optional[UpdateBatch]:
        """Schedule a batch for deployment."""
        async with self._lock:
            batch = self.batches.get(batch_id)
            if not batch:
                return None
            
            batch.status = UpdateStatus.SCHEDULED
            batch.scheduled_at = scheduled_at
            
            logger.info(f"Batch {batch_id} scheduled for {scheduled_at}")
            return batch
    
    # Deployment
    
    async def deploy_batch(
        self,
        batch_id: str,
        triggered_by: str = ""
    ) -> Optional[DeploymentResult]:
        """Deploy a batch of updates."""
        async with self._lock:
            batch = self.batches.get(batch_id)
            if not batch:
                return None
            
            if batch.status not in [UpdateStatus.APPROVED, UpdateStatus.SCHEDULED]:
                return None
            
            batch.status = UpdateStatus.DEPLOYING
            
            deployment_id = f"deploy_{batch_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            result = DeploymentResult(
                deployment_id=deployment_id,
                batch_id=batch_id,
                status=UpdateStatus.DEPLOYING
            )
            
            self.deployment_results[deployment_id] = result
            
            try:
                # Simulate deployment
                for update in batch.updates:
                    # Simulate update installation
                    await asyncio.sleep(0.1)
                    
                    # Mock success (in production would actually update)
                    result.successful_updates.append(update.update_id)
                    result.deployment_logs.append(f"Updated {update.dependency.name} to {update.new_version}")
                
                result.status = UpdateStatus.DEPLOYED
                batch.status = UpdateStatus.DEPLOYED
                batch.deployed_at = datetime.utcnow()
                batch.rollback_available_until = datetime.utcnow() + timedelta(hours=24)
                
                logger.info(f"Batch {batch_id} deployed successfully")
                
            except Exception as e:
                result.status = UpdateStatus.FAILED
                result.error_message = str(e)
                batch.status = UpdateStatus.FAILED
                logger.error(f"Batch {batch_id} deployment failed: {e}")
            
            result.completed_at = datetime.utcnow()
            return result
    
    async def rollback_batch(
        self,
        batch_id: str,
        triggered_by: str = ""
    ) -> Optional[DeploymentResult]:
        """Rollback a deployed batch."""
        async with self._lock:
            batch = self.batches.get(batch_id)
            if not batch:
                return None
            
            if batch.status != UpdateStatus.DEPLOYED:
                return None
            
            if not batch.can_rollback or (batch.rollback_available_until and 
                                          batch.rollback_available_until < datetime.utcnow()):
                return None
            
            deployment_id = f"rollback_{batch_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            result = DeploymentResult(
                deployment_id=deployment_id,
                batch_id=batch_id,
                status=UpdateStatus.DEPLOYING
            )
            
            try:
                # Simulate rollback
                for update in batch.updates:
                    await asyncio.sleep(0.1)
                    result.successful_updates.append(update.update_id)
                    result.deployment_logs.append(f"Rolled back {update.dependency.name} to {update.dependency.current_version}")
                
                result.status = UpdateStatus.ROLLED_BACK
                batch.status = UpdateStatus.ROLLED_BACK
                
                logger.info(f"Batch {batch_id} rolled back by {triggered_by}")
                
            except Exception as e:
                result.status = UpdateStatus.FAILED
                result.error_message = str(e)
                logger.error(f"Batch {batch_id} rollback failed: {e}")
            
            result.completed_at = datetime.utcnow()
            self.deployment_results[deployment_id] = result
            return result
    
    async def get_deployment_result(self, deployment_id: str) -> Optional[DeploymentResult]:
        """Get deployment result by ID."""
        return self.deployment_results.get(deployment_id)
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get dependency update statistics."""
        updates = list(self.available_updates.values())
        batches = list(self.batches.values())
        deployments = list(self.deployment_results.values())
        
        return {
            "dependencies": {
                "total_tracked": len(self.dependencies),
                "by_ecosystem": {
                    eco: len([d for d in self.dependencies.values() if d.ecosystem == eco])
                    for eco in set(d.ecosystem for d in self.dependencies.values())
                }
            },
            "updates": {
                "total_available": len(updates),
                "by_risk_tier": {
                    tier.value: len([u for u in updates if u.risk_tier == tier])
                    for tier in RiskTier
                },
                "by_type": {
                    ut.value: len([u for u in updates if u.update_type == ut])
                    for ut in UpdateType
                }
            },
            "batches": {
                "total": len(batches),
                "by_status": {
                    status.value: len([b for b in batches if b.status == status])
                    for status in UpdateStatus
                }
            },
            "deployments": {
                "total": len(deployments),
                "successful": len([d for d in deployments if d.status == UpdateStatus.DEPLOYED]),
                "failed": len([d for d in deployments if d.status == UpdateStatus.FAILED]),
                "rolled_back": len([d for d in deployments if d.status == UpdateStatus.ROLLED_BACK])
            }
        }


# Global manager instance
_update_manager: Optional[DependencyUpdateManager] = None


async def get_update_manager() -> DependencyUpdateManager:
    """Get or create the global dependency update manager."""
    global _update_manager
    if _update_manager is None:
        _update_manager = DependencyUpdateManager()
        await _update_manager.initialize()
    return _update_manager


def reset_update_manager():
    """Reset the global dependency update manager (for testing)."""
    global _update_manager
    _update_manager = None
