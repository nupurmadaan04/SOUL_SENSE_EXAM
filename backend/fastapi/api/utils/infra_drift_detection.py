"""
Infrastructure Drift Detection Module

This module provides infrastructure drift detection capabilities to identify
and report differences between Infrastructure as Code (IaC) definitions
and actual runtime state.

Features:
- IaC state comparison (Terraform, CloudFormation, etc.)
- Runtime state scanning
- Drift detection and reporting
- Automated remediation suggestions
- Drift alerting and notifications
"""

import asyncio
import json
import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class DriftStatus(str, Enum):
    """Drift detection status."""
    PENDING = "pending"
    SCANNING = "scanning"
    DETECTED = "detected"
    NO_DRIFT = "no_drift"
    REMEDIATING = "remediating"
    REMEDIATED = "remediated"
    FAILED = "failed"
    IGNORED = "ignored"


class DriftSeverity(str, Enum):
    """Drift severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IaCProvider(str, Enum):
    """IaC provider types."""
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    PULUMI = "pulumi"
    ANSIBLE = "ansible"
    CUSTOM = "custom"


class ResourceType(str, Enum):
    """Infrastructure resource types."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    DATABASE = "database"
    SECURITY = "security"
    IAM = "iam"
    LOAD_BALANCER = "load_balancer"
    CONTAINER = "container"
    SERVERLESS = "serverless"


@dataclass
class ResourceAttribute:
    """Resource attribute definition."""
    name: str
    iac_value: Any
    runtime_value: Any
    is_sensitive: bool = False
    is_identifier: bool = False


@dataclass
class DriftedResource:
    """Resource with detected drift."""
    resource_id: str
    resource_type: ResourceType
    resource_name: str
    provider: IaCProvider
    drift_status: DriftStatus
    severity: DriftSeverity
    
    # Change details
    added_attributes: List[ResourceAttribute] = field(default_factory=list)
    modified_attributes: List[ResourceAttribute] = field(default_factory=list)
    removed_attributes: List[ResourceAttribute] = field(default_factory=list)
    
    # Metadata
    iac_reference: Optional[str] = None
    runtime_reference: Optional[str] = None
    region: Optional[str] = None
    account_id: Optional[str] = None
    
    # Remediation
    remediation_available: bool = False
    remediation_script: Optional[str] = None
    manual_steps_required: bool = False


@dataclass
class DriftDetectionResult:
    """Drift detection scan result."""
    scan_id: str
    scan_name: str
    status: DriftStatus
    started_at: datetime
    
    # Scope
    provider: IaCProvider
    environment: str
    
    # Results
    drifted_resources: List[DriftedResource] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scan_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Optional fields
    completed_at: Optional[datetime] = None
    region: Optional[str] = None
    
    # Summary counts
    total_resources: int = 0
    scanned_resources: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # Statistics
    added_resources: int = 0
    modified_resources: int = 0
    removed_resources: int = 0


@dataclass
class IaCState:
    """IaC state snapshot."""
    state_id: str
    provider: IaCProvider
    environment: str
    state_data: Dict[str, Any]
    captured_at: datetime = field(default_factory=datetime.utcnow)
    state_version: str = "1.0"
    terraform_version: Optional[str] = None
    
    # Metadata
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    pipeline_run_id: Optional[str] = None


@dataclass
class RuntimeState:
    """Runtime state snapshot."""
    state_id: str
    provider: str  # AWS, Azure, GCP
    environment: str
    resources: Dict[str, Any]
    captured_at: datetime = field(default_factory=datetime.utcnow)
    scan_duration_seconds: Optional[float] = None
    api_calls_made: int = 0


@dataclass
class DriftAlert:
    """Drift detection alert."""
    alert_id: str
    scan_id: str
    severity: DriftSeverity
    resource_id: str
    message: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    notification_sent: bool = False


class ResourceComparator:
    """Comparator for IaC and runtime resources."""
    
    # Attributes to ignore during comparison
    IGNORED_ATTRIBUTES = [
        "created_at",
        "updated_at",
        "last_modified",
        "etag",
        "version_id",
        "sequence_number"
    ]
    
    @classmethod
    def compare_resources(
        cls,
        iac_resource: Dict[str, Any],
        runtime_resource: Dict[str, Any],
        resource_type: ResourceType
    ) -> Tuple[List[ResourceAttribute], List[ResourceAttribute], List[ResourceAttribute]]:
        """Compare IaC and runtime resources."""
        added = []
        modified = []
        removed = []
        
        # Normalize both resources
        iac_normalized = cls._normalize_resource(iac_resource)
        runtime_normalized = cls._normalize_resource(runtime_resource)
        
        iac_keys = set(iac_normalized.keys())
        runtime_keys = set(runtime_normalized.keys())
        
        # Find added attributes (in runtime but not in IaC)
        for key in runtime_keys - iac_keys:
            if not cls._should_ignore_attribute(key):
                added.append(ResourceAttribute(
                    name=key,
                    iac_value=None,
                    runtime_value=runtime_normalized[key]
                ))
        
        # Find removed attributes (in IaC but not in runtime)
        for key in iac_keys - runtime_keys:
            if not cls._should_ignore_attribute(key):
                removed.append(ResourceAttribute(
                    name=key,
                    iac_value=iac_normalized[key],
                    runtime_value=None
                ))
        
        # Find modified attributes
        for key in iac_keys & runtime_keys:
            if cls._should_ignore_attribute(key):
                continue
            
            iac_val = iac_normalized[key]
            runtime_val = runtime_normalized[key]
            
            if not cls._values_equal(iac_val, runtime_val):
                modified.append(ResourceAttribute(
                    name=key,
                    iac_value=iac_val,
                    runtime_value=runtime_val
                ))
        
        return added, modified, removed
    
    @classmethod
    def _normalize_resource(cls, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize resource for comparison."""
        normalized = {}
        
        def flatten_dict(d: Dict, prefix: str = ""):
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    flatten_dict(value, full_key)
                elif isinstance(value, list):
                    # Sort lists for consistent comparison
                    normalized[full_key] = json.dumps(value, sort_keys=True)
                else:
                    normalized[full_key] = value
        
        flatten_dict(resource)
        return normalized
    
    @classmethod
    def _should_ignore_attribute(cls, attr_name: str) -> bool:
        """Check if attribute should be ignored."""
        return any(ignored in attr_name.lower() for ignored in cls.IGNORED_ATTRIBUTES)
    
    @classmethod
    def _values_equal(cls, val1: Any, val2: Any) -> bool:
        """Compare two values for equality."""
        # Handle numeric comparisons with tolerance
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return abs(val1 - val2) < 0.0001
        
        # Handle string comparisons (case-insensitive for some fields)
        if isinstance(val1, str) and isinstance(val2, str):
            return val1.lower() == val2.lower()
        
        return val1 == val2
    
    @classmethod
    def calculate_drift_severity(
        cls,
        added: List[ResourceAttribute],
        modified: List[ResourceAttribute],
        removed: List[ResourceAttribute],
        resource_type: ResourceType
    ) -> DriftSeverity:
        """Calculate drift severity based on changes."""
        # Critical: Security-related changes
        security_attrs = ["password", "secret", "key", "token", "certificate", "policy"]
        for attr in modified:
            if any(sa in attr.name.lower() for sa in security_attrs):
                return DriftSeverity.CRITICAL
        
        # High: Infrastructure-critical changes
        critical_attrs = ["instance_type", "size", "count", "version", "enabled"]
        critical_count = sum(
            1 for attr in modified
            if any(ca in attr.name.lower() for ca in critical_attrs)
        )
        if critical_count > 0:
            return DriftSeverity.HIGH
        
        # Medium: Multiple changes or significant additions
        total_changes = len(added) + len(modified) + len(removed)
        if total_changes >= 5:
            return DriftSeverity.MEDIUM
        
        # Low: Minor changes
        if total_changes > 0:
            return DriftSeverity.LOW
        
        return DriftSeverity.INFO


class DriftDetectionManager:
    """
    Central manager for infrastructure drift detection.
    
    Provides functionality for:
    - IaC state management
    - Runtime state scanning
    - Drift detection and comparison
    - Alert generation
    - Remediation tracking
    """
    
    def __init__(self):
        self.iac_states: Dict[str, IaCState] = {}
        self.runtime_states: Dict[str, RuntimeState] = {}
        self.scan_results: Dict[str, DriftDetectionResult] = {}
        self.alerts: Dict[str, DriftAlert] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the drift detection manager."""
        async with self._lock:
            if self._initialized:
                return
            
            self._initialized = True
            logger.info("DriftDetectionManager initialized successfully")
    
    # IaC State Management
    
    async def capture_iac_state(
        self,
        provider: IaCProvider,
        environment: str,
        state_data: Dict[str, Any],
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        pipeline_run_id: Optional[str] = None
    ) -> IaCState:
        """Capture IaC state snapshot."""
        async with self._lock:
            state_id = f"iac_{provider.value}_{environment}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            state = IaCState(
                state_id=state_id,
                provider=provider,
                environment=environment,
                state_data=state_data,
                git_commit=git_commit,
                git_branch=git_branch,
                pipeline_run_id=pipeline_run_id
            )
            
            self.iac_states[state_id] = state
            logger.info(f"Captured IaC state: {state_id}")
            return state
    
    async def get_iac_state(self, state_id: str) -> Optional[IaCState]:
        """Get IaC state by ID."""
        return self.iac_states.get(state_id)
    
    async def list_iac_states(
        self,
        provider: Optional[IaCProvider] = None,
        environment: Optional[str] = None
    ) -> List[IaCState]:
        """List IaC states with optional filtering."""
        states = list(self.iac_states.values())
        
        if provider:
            states = [s for s in states if s.provider == provider]
        if environment:
            states = [s for s in states if s.environment == environment]
        
        return sorted(states, key=lambda s: s.captured_at, reverse=True)
    
    # Runtime State Management
    
    async def capture_runtime_state(
        self,
        provider: str,
        environment: str,
        resources: Dict[str, Any],
        scan_duration_seconds: Optional[float] = None
    ) -> RuntimeState:
        """Capture runtime state snapshot."""
        async with self._lock:
            state_id = f"runtime_{provider}_{environment}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            state = RuntimeState(
                state_id=state_id,
                provider=provider,
                environment=environment,
                resources=resources,
                scan_duration_seconds=scan_duration_seconds
            )
            
            self.runtime_states[state_id] = state
            logger.info(f"Captured runtime state: {state_id}")
            return state
    
    # Drift Detection
    
    async def detect_drift(
        self,
        iac_state_id: str,
        runtime_state_id: str,
        scan_name: str,
        auto_remediate: bool = False
    ) -> Optional[DriftDetectionResult]:
        """Detect drift between IaC and runtime states."""
        async with self._lock:
            iac_state = self.iac_states.get(iac_state_id)
            runtime_state = self.runtime_states.get(runtime_state_id)
            
            if not iac_state or not runtime_state:
                return None
            
            import uuid
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            unique_suffix = str(uuid.uuid4())[:8]
            scan_id = f"scan_{timestamp}_{unique_suffix}"
            
            result = DriftDetectionResult(
                scan_id=scan_id,
                scan_name=scan_name,
                status=DriftStatus.SCANNING,
                started_at=datetime.utcnow(),
                provider=iac_state.provider,
                environment=iac_state.environment,
                region=runtime_state.resources.get("region")
            )
            
            self.scan_results[scan_id] = result
            
            try:
                # Compare resources
                iac_resources = self._extract_resources(iac_state.state_data)
                runtime_resources = runtime_state.resources
                
                result.total_resources = len(iac_resources)
                
                drifted_resources = []
                
                def _get_resource_type(type_str: str) -> ResourceType:
                    """Safely get ResourceType from string."""
                    try:
                        return ResourceType(type_str)
                    except ValueError:
                        # Map common cloud resource types to our categories
                        type_lower = type_str.lower()
                        if any(x in type_lower for x in ["instance", "vm", "server", "compute"]):
                            return ResourceType.COMPUTE
                        elif any(x in type_lower for x in ["db", "rds", "database", "sql"]):
                            return ResourceType.DATABASE
                        elif any(x in type_lower for x in ["s3", "bucket", "storage", "volume"]):
                            return ResourceType.STORAGE
                        elif any(x in type_lower for x in ["vpc", "subnet", "network", "security_group"]):
                            return ResourceType.NETWORK
                        elif any(x in type_lower for x in ["iam", "role", "policy", "user"]):
                            return ResourceType.IAM
                        elif any(x in type_lower for x in ["lb", "load_balancer"]):
                            return ResourceType.LOAD_BALANCER
                        else:
                            return ResourceType.COMPUTE
                
                # Check for modified resources
                for resource_id, iac_resource in iac_resources.items():
                    result.scanned_resources += 1
                    
                    if resource_id in runtime_resources:
                        runtime_resource = runtime_resources[resource_id]
                        resource_type = _get_resource_type(iac_resource.get("type", "compute"))
                        
                        # Compare
                        added, modified, removed = ResourceComparator.compare_resources(
                            iac_resource,
                            runtime_resource,
                            resource_type
                        )
                        
                        if added or modified or removed:
                            severity = ResourceComparator.calculate_drift_severity(
                                added, modified, removed,
                                resource_type
                            )
                            
                            drifted = DriftedResource(
                                resource_id=resource_id,
                                resource_type=resource_type,
                                resource_name=iac_resource.get("name", resource_id),
                                provider=iac_state.provider,
                                drift_status=DriftStatus.DETECTED,
                                severity=severity,
                                added_attributes=added,
                                modified_attributes=modified,
                                removed_attributes=removed
                            )
                            
                            drifted_resources.append(drifted)
                            
                            # Update counts
                            if severity == DriftSeverity.CRITICAL:
                                result.critical_count += 1
                            elif severity == DriftSeverity.HIGH:
                                result.high_count += 1
                            elif severity == DriftSeverity.MEDIUM:
                                result.medium_count += 1
                            else:
                                result.low_count += 1
                            
                            result.modified_resources += 1
                    else:
                        # Resource removed from runtime
                        result.removed_resources += 1
                
                # Check for added resources (in runtime but not in IaC)
                for resource_id, runtime_resource in runtime_resources.items():
                    if resource_id not in iac_resources and isinstance(runtime_resource, dict):
                        result.added_resources += 1
                
                result.drifted_resources = drifted_resources
                result.status = DriftStatus.DETECTED if drifted_resources else DriftStatus.NO_DRIFT
                result.completed_at = datetime.utcnow()
                
                # Generate alerts for critical/high drift
                for drifted in drifted_resources:
                    if drifted.severity in [DriftSeverity.CRITICAL, DriftSeverity.HIGH]:
                        await self._create_alert(scan_id, drifted)
                
                logger.info(f"Drift detection completed: {scan_id} - {result.status.value}")
                
            except Exception as e:
                result.status = DriftStatus.FAILED
                result.errors.append(str(e))
                logger.error(f"Drift detection failed: {e}")
            
            return result
    
    def _extract_resources(self, state_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract resources from IaC state data."""
        resources = {}
        
        # Handle Terraform state format with resources dict
        if "resources" in state_data:
            resources_data = state_data["resources"]
            if isinstance(resources_data, dict):
                # Resources is a dictionary keyed by resource ID
                for resource_id, resource in resources_data.items():
                    if isinstance(resource, dict):
                        resources[resource_id] = resource
            elif isinstance(resources_data, list):
                # Resources is a list
                for resource in resources_data:
                    if isinstance(resource, dict):
                        resource_id = resource.get("id", resource.get("name"))
                        if resource_id:
                            resources[resource_id] = resource
        
        # Handle flat resource map
        elif isinstance(state_data, dict):
            for key, value in state_data.items():
                if isinstance(value, dict):
                    resources[key] = value
        
        return resources
    
    async def get_scan_result(self, scan_id: str) -> Optional[DriftDetectionResult]:
        """Get drift detection result by ID."""
        return self.scan_results.get(scan_id)
    
    async def list_scan_results(
        self,
        environment: Optional[str] = None,
        status: Optional[DriftStatus] = None
    ) -> List[DriftDetectionResult]:
        """List scan results with optional filtering."""
        results = list(self.scan_results.values())
        
        if environment:
            results = [r for r in results if r.environment == environment]
        if status:
            results = [r for r in results if r.status == status]
        
        return sorted(results, key=lambda r: r.started_at, reverse=True)
    
    # Alert Management
    
    async def _create_alert(
        self,
        scan_id: str,
        drifted_resource: DriftedResource
    ) -> DriftAlert:
        """Create drift alert."""
        alert_id = f"alert_{scan_id}_{drifted_resource.resource_id}"
        
        alert = DriftAlert(
            alert_id=alert_id,
            scan_id=scan_id,
            severity=drifted_resource.severity,
            resource_id=drifted_resource.resource_id,
            message=f"Drift detected in {drifted_resource.resource_name}: {len(drifted_resource.modified_attributes)} modifications"
        )
        
        self.alerts[alert_id] = alert
        return alert
    
    async def get_alerts(
        self,
        scan_id: Optional[str] = None,
        acknowledged: Optional[bool] = None
    ) -> List[DriftAlert]:
        """Get alerts with optional filtering."""
        alerts = list(self.alerts.values())
        
        if scan_id:
            alerts = [a for a in alerts if a.scan_id == scan_id]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> Optional[DriftAlert]:
        """Acknowledge a drift alert."""
        alert = self.alerts.get(alert_id)
        if not alert:
            return None
        
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        
        return alert
    
    # Remediation
    
    async def generate_remediation(
        self,
        scan_id: str,
        resource_id: str
    ) -> Optional[str]:
        """Generate remediation script for drifted resource."""
        result = self.scan_results.get(scan_id)
        if not result:
            return None
        
        drifted = next(
            (d for d in result.drifted_resources if d.resource_id == resource_id),
            None
        )
        
        if not drifted:
            return None
        
        # Generate Terraform import/update commands
        script_lines = [f"# Remediation for {drifted.resource_name}", ""]
        
        for attr in drifted.modified_attributes:
            script_lines.append(f"# Update {attr.name}")
            script_lines.append(f"# Current: {attr.runtime_value}")
            script_lines.append(f"# Expected: {attr.iac_value}")
        
        script_lines.append("")
        script_lines.append("terraform apply -target=<resource_address>")
        
        return "\n".join(script_lines)
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get drift detection statistics."""
        scans = list(self.scan_results.values())
        alerts = list(self.alerts.values())
        
        return {
            "scans": {
                "total": len(scans),
                "detected": len([s for s in scans if s.status == DriftStatus.DETECTED]),
                "no_drift": len([s for s in scans if s.status == DriftStatus.NO_DRIFT]),
                "failed": len([s for s in scans if s.status == DriftStatus.FAILED])
            },
            "drift_summary": {
                "total_resources_scanned": sum(s.total_resources for s in scans),
                "total_drifted": sum(len(s.drifted_resources) for s in scans),
                "critical": sum(s.critical_count for s in scans),
                "high": sum(s.high_count for s in scans),
                "medium": sum(s.medium_count for s in scans),
                "low": sum(s.low_count for s in scans)
            },
            "alerts": {
                "total": len(alerts),
                "unacknowledged": len([a for a in alerts if not a.acknowledged]),
                "acknowledged": len([a for a in alerts if a.acknowledged])
            }
        }


# Global manager instance
_drift_manager: Optional[DriftDetectionManager] = None


async def get_drift_manager() -> DriftDetectionManager:
    """Get or create the global drift detection manager."""
    global _drift_manager
    if _drift_manager is None:
        _drift_manager = DriftDetectionManager()
        await _drift_manager.initialize()
    return _drift_manager


def reset_drift_manager():
    """Reset the global drift detection manager (for testing)."""
    global _drift_manager
    _drift_manager = None
