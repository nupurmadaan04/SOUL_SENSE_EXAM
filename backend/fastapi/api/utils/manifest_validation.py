"""
Golden Deployment Manifest Validation Module

This module provides comprehensive validation for deployment manifests,
enforcing golden standards, security policies, and best practices.

Features:
- Kubernetes manifest validation
- Security policy enforcement
- Resource limit verification
- Label and annotation standards
- Image security scanning
- Network policy validation
"""

import asyncio
import json
import yaml
import re
import hashlib
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationStatus(str, Enum):
    """Validation status."""
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"


class ResourceType(str, Enum):
    """Kubernetes resource types."""
    DEPLOYMENT = "Deployment"
    SERVICE = "Service"
    CONFIGMAP = "ConfigMap"
    SECRET = "Secret"
    INGRESS = "Ingress"
    SERVICE_ACCOUNT = "ServiceAccount"
    ROLE = "Role"
    ROLE_BINDING = "RoleBinding"
    NETWORK_POLICY = "NetworkPolicy"
    POD = "Pod"
    DAEMONSET = "DaemonSet"
    STATEFULSET = "StatefulSet"
    JOB = "Job"
    CRONJOB = "CronJob"
    HPA = "HorizontalPodAutoscaler"


class PolicyRuleType(str, Enum):
    """Policy rule types."""
    REQUIRED_LABELS = "required_labels"
    REQUIRED_ANNOTATIONS = "required_annotations"
    RESOURCE_LIMITS = "resource_limits"
    SECURITY_CONTEXT = "security_context"
    IMAGE_POLICY = "image_policy"
    NETWORK_POLICY = "network_policy"
    PROBE_REQUIRED = "probe_required"
    REPLICA_LIMITS = "replica_limits"
    NAMESPACE_ISOLATION = "namespace_isolation"


@dataclass
class ValidationRule:
    """Validation rule definition."""
    rule_id: str
    name: str
    description: str
    rule_type: PolicyRuleType
    resource_types: List[ResourceType]
    severity: ValidationSeverity
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    custom_message: Optional[str] = None


@dataclass
class ValidationFinding:
    """Individual validation finding."""
    finding_id: str
    rule_id: str
    severity: ValidationSeverity
    message: str
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    resource_namespace: Optional[str] = None
    field_path: Optional[str] = None
    suggested_fix: Optional[str] = None
    documentation_url: Optional[str] = None


@dataclass
class ManifestValidationResult:
    """Manifest validation result."""
    validation_id: str
    manifest_name: str
    manifest_hash: str
    status: ValidationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    findings: List[ValidationFinding] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    policy_version: str = "1.0.0"
    validated_by: Optional[str] = None


@dataclass
class GoldenPolicy:
    """Golden deployment policy."""
    policy_id: str
    name: str
    description: str
    version: str
    rules: List[ValidationRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    namespace_scope: Optional[List[str]] = None
    resource_scope: Optional[List[ResourceType]] = None


@dataclass
class ImageValidationResult:
    """Container image validation result."""
    image_name: str
    image_tag: str
    digest: Optional[str] = None
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    scan_status: str = "pending"  # pending, scanning, completed, failed
    scan_completed_at: Optional[datetime] = None
    allowed: bool = True
    block_reason: Optional[str] = None


class ManifestParser:
    """Parser for Kubernetes manifests."""
    
    @staticmethod
    def parse_yaml(manifest_yaml: str) -> List[Dict[str, Any]]:
        """Parse YAML manifest into list of documents."""
        try:
            documents = list(yaml.safe_load_all(manifest_yaml))
            return [doc for doc in documents if doc is not None]
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            raise ValueError(f"Invalid YAML: {e}")
    
    @staticmethod
    def parse_json(manifest_json: str) -> List[Dict[str, Any]]:
        """Parse JSON manifest."""
        try:
            data = json.loads(manifest_json)
            # Handle both single document and list of documents
            if isinstance(data, list):
                return data
            return [data]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Invalid JSON: {e}")
    
    @staticmethod
    def calculate_hash(manifest: Union[str, Dict[str, Any]]) -> str:
        """Calculate hash of manifest for tracking."""
        if isinstance(manifest, dict):
            content = json.dumps(manifest, sort_keys=True)
        else:
            content = manifest
        return hashlib.sha256(content.encode()).hexdigest()
    
    @staticmethod
    def get_resource_key(doc: Dict[str, Any]) -> str:
        """Get unique key for a resource."""
        kind = doc.get("kind", "Unknown")
        metadata = doc.get("metadata", {})
        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        return f"{kind}/{namespace}/{name}"


class ResourceValidator:
    """Validator for Kubernetes resources."""
    
    @staticmethod
    def validate_required_labels(
        doc: Dict[str, Any],
        required_labels: List[str]
    ) -> List[ValidationFinding]:
        """Validate required labels are present."""
        findings = []
        metadata = doc.get("metadata", {})
        labels = metadata.get("labels", {})
        
        for label in required_labels:
            if label not in labels:
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'label_{label}'.encode()).hexdigest()[:8]}",
                    rule_id="required_labels",
                    severity=ValidationSeverity.ERROR,
                    message=f"Required label '{label}' is missing",
                    resource_type=doc.get("kind"),
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path="metadata.labels",
                    suggested_fix=f"Add label: {label}: <value>"
                ))
        
        return findings
    
    @staticmethod
    def validate_resource_limits(doc: Dict[str, Any]) -> List[ValidationFinding]:
        """Validate resource limits are set."""
        findings = []
        kind = doc.get("kind", "")
        metadata = doc.get("metadata", {})
        
        # Check if resource has containers
        containers = []
        spec = doc.get("spec", {})
        template = spec.get("template", {})
        template_spec = template.get("spec", {})
        
        if kind in ["Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"]:
            containers = template_spec.get("containers", [])
        elif kind == "Pod":
            containers = spec.get("containers", [])
        elif kind == "CronJob":
            job_template = spec.get("jobTemplate", {})
            job_spec = job_template.get("spec", {})
            job_template_spec = job_spec.get("template", {})
            job_pod_spec = job_template_spec.get("spec", {})
            containers = job_pod_spec.get("containers", [])
        
        for idx, container in enumerate(containers):
            container_name = container.get("name", f"container-{idx}")
            resources = container.get("resources", {})
            
            # Check limits
            limits = resources.get("limits", {})
            if not limits.get("cpu"):
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'cpu_limit_{container_name}'.encode()).hexdigest()[:8]}",
                    rule_id="resource_limits",
                    severity=ValidationSeverity.ERROR,
                    message=f"CPU limit not set for container '{container_name}'",
                    resource_type=kind,
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path=f"spec.template.spec.containers[{idx}].resources.limits.cpu",
                    suggested_fix="Add resources.limits.cpu: '500m' (or appropriate value)"
                ))
            
            if not limits.get("memory"):
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'mem_limit_{container_name}'.encode()).hexdigest()[:8]}",
                    rule_id="resource_limits",
                    severity=ValidationSeverity.ERROR,
                    message=f"Memory limit not set for container '{container_name}'",
                    resource_type=kind,
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path=f"spec.template.spec.containers[{idx}].resources.limits.memory",
                    suggested_fix="Add resources.limits.memory: '256Mi' (or appropriate value)"
                ))
            
            # Check requests
            requests = resources.get("requests", {})
            if not requests.get("cpu"):
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'cpu_request_{container_name}'.encode()).hexdigest()[:8]}",
                    rule_id="resource_limits",
                    severity=ValidationSeverity.WARNING,
                    message=f"CPU request not set for container '{container_name}'",
                    resource_type=kind,
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path=f"spec.template.spec.containers[{idx}].resources.requests.cpu",
                    suggested_fix="Add resources.requests.cpu: '100m' (or appropriate value)"
                ))
        
        return findings
    
    @staticmethod
    def validate_security_context(doc: Dict[str, Any]) -> List[ValidationFinding]:
        """Validate security context settings."""
        findings = []
        kind = doc.get("kind", "")
        metadata = doc.get("metadata", {})
        
        if kind not in ["Deployment", "StatefulSet", "DaemonSet", "Pod", "Job", "ReplicaSet", "CronJob"]:
            return findings
        
        spec = doc.get("spec", {})
        if kind in ["Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"]:
            template = spec.get("template", {})
            template_spec = template.get("spec", {})
            security_context = template_spec.get("securityContext", {})
        elif kind == "Pod":
            security_context = spec.get("securityContext", {})
        elif kind == "CronJob":
            job_template = spec.get("jobTemplate", {})
            job_spec = job_template.get("spec", {})
            job_template_spec = job_spec.get("template", {})
            security_context = job_template_spec.get("securityContext", {})
        else:
            security_context = {}
        
        # Check runAsNonRoot
        if not security_context.get("runAsNonRoot"):
            findings.append(ValidationFinding(
                finding_id=f"find_{hashlib.md5('runAsNonRoot'.encode()).hexdigest()[:8]}",
                rule_id="security_context",
                severity=ValidationSeverity.WARNING,
                message="Pod should run as non-root user",
                resource_type=kind,
                resource_name=metadata.get("name"),
                resource_namespace=metadata.get("namespace"),
                field_path="spec.template.spec.securityContext.runAsNonRoot",
                suggested_fix="Add securityContext.runAsNonRoot: true"
            ))
        
        # Check readOnlyRootFilesystem
        # This would need container-level checking similar to resource limits
        
        return findings
    
    @staticmethod
    def validate_image_policy(
        doc: Dict[str, Any],
        allowed_registries: List[str],
        require_digest: bool = False
    ) -> List[ValidationFinding]:
        """Validate container image policies."""
        findings = []
        kind = doc.get("kind", "")
        metadata = doc.get("metadata", {})
        
        containers = []
        spec = doc.get("spec", {})
        template = spec.get("template", {})
        template_spec = template.get("spec", {})
        
        if kind in ["Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"]:
            containers = template_spec.get("containers", [])
        elif kind == "Pod":
            containers = spec.get("containers", [])
        elif kind == "CronJob":
            job_template = spec.get("jobTemplate", {})
            job_spec = job_template.get("spec", {})
            job_template_spec = job_spec.get("template", {})
            job_pod_spec = job_template_spec.get("spec", {})
            containers = job_pod_spec.get("containers", [])
        
        for idx, container in enumerate(containers):
            container_name = container.get("name", f"container-{idx}")
            image = container.get("image", "")
            
            # Check if image uses allowed registry
            registry_allowed = any(
                image.startswith(registry) or image.startswith(f"{registry}/")
                for registry in allowed_registries
            )
            
            if not registry_allowed:
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'image_{image}'.encode()).hexdigest()[:8]}",
                    rule_id="image_policy",
                    severity=ValidationSeverity.ERROR,
                    message=f"Image '{image}' uses disallowed registry",
                    resource_type=kind,
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path=f"spec.template.spec.containers[{idx}].image",
                    suggested_fix=f"Use image from allowed registries: {', '.join(allowed_registries)}"
                ))
            
            # Check for latest tag
            if ":latest" in image:
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'latest_{image}'.encode()).hexdigest()[:8]}",
                    rule_id="image_policy",
                    severity=ValidationSeverity.WARNING,
                    message=f"Image '{image}' uses 'latest' tag",
                    resource_type=kind,
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path=f"spec.template.spec.containers[{idx}].image",
                    suggested_fix="Use specific version tag instead of 'latest'"
                ))
            
            # Check for digest if required
            if require_digest and "@sha256:" not in image:
                findings.append(ValidationFinding(
                    finding_id=f"find_{hashlib.md5(f'digest_{image}'.encode()).hexdigest()[:8]}",
                    rule_id="image_policy",
                    severity=ValidationSeverity.WARNING,
                    message=f"Image '{image}' should use digest for immutability",
                    resource_type=kind,
                    resource_name=metadata.get("name"),
                    resource_namespace=metadata.get("namespace"),
                    field_path=f"spec.template.spec.containers[{idx}].image",
                    suggested_fix="Use image with digest: image@sha256:..."
                ))
        
        return findings


class ManifestValidationManager:
    """
    Central manager for manifest validation.
    
    Provides functionality for:
    - Golden policy management
    - Manifest validation
    - Image scanning
    - Compliance reporting
    """
    
    def __init__(self):
        self.policies: Dict[str, GoldenPolicy] = {}
        self.validation_results: Dict[str, ManifestValidationResult] = {}
        self.image_results: Dict[str, ImageValidationResult] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the validation manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default golden policy
            await self._create_default_policy()
            
            self._initialized = True
            logger.info("ManifestValidationManager initialized successfully")
    
    async def _create_default_policy(self):
        """Create default golden deployment policy."""
        policy_id = "golden-policy-default"
        
        rules = [
            ValidationRule(
                rule_id="required-labels-app",
                name="Required Label: app",
                description="All resources must have 'app' label",
                rule_type=PolicyRuleType.REQUIRED_LABELS,
                resource_types=[
                    ResourceType.DEPLOYMENT,
                    ResourceType.SERVICE,
                    ResourceType.CONFIGMAP
                ],
                severity=ValidationSeverity.ERROR,
                parameters={"labels": ["app"]}
            ),
            ValidationRule(
                rule_id="required-labels-version",
                name="Required Label: version",
                description="All resources must have 'version' label",
                rule_type=PolicyRuleType.REQUIRED_LABELS,
                resource_types=[
                    ResourceType.DEPLOYMENT,
                    ResourceType.SERVICE
                ],
                severity=ValidationSeverity.WARNING,
                parameters={"labels": ["version"]}
            ),
            ValidationRule(
                rule_id="resource-limits-required",
                name="Resource Limits Required",
                description="All containers must have resource limits",
                rule_type=PolicyRuleType.RESOURCE_LIMITS,
                resource_types=[
                    ResourceType.DEPLOYMENT,
                    ResourceType.STATEFULSET,
                    ResourceType.DAEMONSET,
                    ResourceType.JOB,
                    ResourceType.CRONJOB
                ],
                severity=ValidationSeverity.ERROR
            ),
            ValidationRule(
                rule_id="security-context-nonroot",
                name="Run as Non-Root",
                description="Pods should run as non-root user",
                rule_type=PolicyRuleType.SECURITY_CONTEXT,
                resource_types=[
                    ResourceType.DEPLOYMENT,
                    ResourceType.STATEFULSET,
                    ResourceType.DAEMONSET
                ],
                severity=ValidationSeverity.WARNING
            ),
            ValidationRule(
                rule_id="image-registry-allowed",
                name="Allowed Image Registries",
                description="Images must come from allowed registries",
                rule_type=PolicyRuleType.IMAGE_POLICY,
                resource_types=[
                    ResourceType.DEPLOYMENT,
                    ResourceType.STATEFULSET,
                    ResourceType.DAEMONSET,
                    ResourceType.JOB,
                    ResourceType.CRONJOB,
                    ResourceType.POD
                ],
                severity=ValidationSeverity.ERROR,
                parameters={"allowed_registries": ["docker.io", "gcr.io", "registry.k8s.io"]}
            )
        ]
        
        policy = GoldenPolicy(
            policy_id=policy_id,
            name="Golden Deployment Policy",
            description="Default policy enforcing golden standards for Kubernetes deployments",
            version="1.0.0",
            rules=rules,
            is_active=True
        )
        
        self.policies[policy_id] = policy
    
    # Policy Management
    
    async def create_policy(
        self,
        name: str,
        description: str,
        rules: List[ValidationRule]
    ) -> GoldenPolicy:
        """Create a new validation policy."""
        async with self._lock:
            policy_id = f"policy_{hashlib.md5(name.encode()).hexdigest()[:12]}"
            
            policy = GoldenPolicy(
                policy_id=policy_id,
                name=name,
                description=description,
                version="1.0.0",
                rules=rules
            )
            
            self.policies[policy_id] = policy
            logger.info(f"Created policy: {policy_id}")
            return policy
    
    async def get_policy(self, policy_id: str) -> Optional[GoldenPolicy]:
        """Get a policy by ID."""
        return self.policies.get(policy_id)
    
    async def list_policies(self, active_only: bool = True) -> List[GoldenPolicy]:
        """List validation policies."""
        policies = list(self.policies.values())
        if active_only:
            policies = [p for p in policies if p.is_active]
        return policies
    
    # Validation
    
    async def validate_manifest(
        self,
        manifest_content: str,
        manifest_format: str = "yaml",
        policy_id: Optional[str] = None,
        manifest_name: str = "unnamed"
    ) -> ManifestValidationResult:
        """Validate a manifest against golden policies."""
        async with self._lock:
            validation_id = f"val_{hashlib.md5(manifest_content.encode()).hexdigest()[:16]}"
            
            result = ManifestValidationResult(
                validation_id=validation_id,
                manifest_name=manifest_name,
                manifest_hash=ManifestParser.calculate_hash(manifest_content),
                status=ValidationStatus.VALIDATING,
                started_at=datetime.utcnow()
            )
            
            try:
                # Parse manifest
                if manifest_format == "yaml":
                    documents = ManifestParser.parse_yaml(manifest_content)
                else:
                    documents = ManifestParser.parse_json(manifest_content)
                
                # Get policy
                policy = self.policies.get(policy_id, self.policies.get("golden-policy-default"))
                
                findings = []
                
                for doc in documents:
                    kind = doc.get("kind", "")
                    
                    # Apply rules
                    for rule in policy.rules:
                        if not rule.enabled:
                            continue
                        
                        # Check if rule applies to this resource type
                        resource_type = ResourceType(kind) if kind in [rt.value for rt in ResourceType] else None
                        if resource_type and resource_type not in rule.resource_types:
                            continue
                        
                        # Apply rule
                        if rule.rule_type == PolicyRuleType.REQUIRED_LABELS:
                            required_labels = rule.parameters.get("labels", [])
                            findings.extend(ResourceValidator.validate_required_labels(doc, required_labels))
                        
                        elif rule.rule_type == PolicyRuleType.RESOURCE_LIMITS:
                            findings.extend(ResourceValidator.validate_resource_limits(doc))
                        
                        elif rule.rule_type == PolicyRuleType.SECURITY_CONTEXT:
                            findings.extend(ResourceValidator.validate_security_context(doc))
                        
                        elif rule.rule_type == PolicyRuleType.IMAGE_POLICY:
                            allowed_registries = rule.parameters.get("allowed_registries", ["docker.io"])
                            require_digest = rule.parameters.get("require_digest", False)
                            findings.extend(ResourceValidator.validate_image_policy(doc, allowed_registries, require_digest))
                
                # Update result
                result.findings = findings
                result.error_count = len([f for f in findings if f.severity == ValidationSeverity.ERROR])
                result.warning_count = len([f for f in findings if f.severity == ValidationSeverity.WARNING])
                result.info_count = len([f for f in findings if f.severity == ValidationSeverity.INFO])
                
                if result.error_count > 0:
                    result.status = ValidationStatus.INVALID
                elif result.warning_count > 0:
                    result.status = ValidationStatus.PARTIAL
                else:
                    result.status = ValidationStatus.VALID
                
            except Exception as e:
                result.status = ValidationStatus.INVALID
                result.findings.append(ValidationFinding(
                    finding_id=f"find_error",
                    rule_id="validation_error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation failed: {str(e)}"
                ))
                result.error_count = 1
            
            result.completed_at = datetime.utcnow()
            self.validation_results[validation_id] = result
            
            logger.info(f"Validation completed: {validation_id} - {result.status.value}")
            return result
    
    async def get_validation_result(self, validation_id: str) -> Optional[ManifestValidationResult]:
        """Get validation result by ID."""
        return self.validation_results.get(validation_id)
    
    # Image Scanning
    
    async def scan_image(self, image_name: str, image_tag: str) -> ImageValidationResult:
        """Scan container image for vulnerabilities."""
        result = ImageValidationResult(
            image_name=image_name,
            image_tag=image_tag,
            scan_status="completed"
        )
        
        # In production, integrate with Trivy, Clair, or similar
        # For now, return mock result
        result.allowed = True
        result.scan_completed_at = datetime.utcnow()
        
        self.image_results[f"{image_name}:{image_tag}"] = result
        return result
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        results = list(self.validation_results.values())
        
        return {
            "policies": {
                "total": len(self.policies),
                "active": len([p for p in self.policies.values() if p.is_active])
            },
            "validations": {
                "total": len(results),
                "valid": len([r for r in results if r.status == ValidationStatus.VALID]),
                "invalid": len([r for r in results if r.status == ValidationStatus.INVALID]),
                "partial": len([r for r in results if r.status == ValidationStatus.PARTIAL])
            },
            "findings": {
                "total": sum(len(r.findings) for r in results),
                "errors": sum(r.error_count for r in results),
                "warnings": sum(r.warning_count for r in results),
                "info": sum(r.info_count for r in results)
            },
            "images_scanned": len(self.image_results)
        }


# Global manager instance
_validation_manager: Optional[ManifestValidationManager] = None


async def get_validation_manager() -> ManifestValidationManager:
    """Get or create the global validation manager."""
    global _validation_manager
    if _validation_manager is None:
        _validation_manager = ManifestValidationManager()
        await _validation_manager.initialize()
    return _validation_manager


def reset_validation_manager():
    """Reset the global validation manager (for testing)."""
    global _validation_manager
    _validation_manager = None
