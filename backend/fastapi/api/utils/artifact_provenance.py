"""
Artifact Provenance and Signature Verification Module

This module provides artifact provenance tracking and signature verification
capabilities for supply chain security. It ensures that deployed artifacts
are authentic, unmodified, and traceable to their source.

Features:
- Artifact registration and tracking
- Cryptographic signature generation and verification
- Provenance attestation (SLSA-inspired)
- Build metadata capture
- Verification policy enforcement
- Artifact chain of custody
"""

import asyncio
import hashlib
import json
import base64
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    """Types of artifacts that can be tracked."""
    CONTAINER_IMAGE = "container_image"
    BINARY = "binary"
    PACKAGE = "package"
    CONFIGURATION = "configuration"
    HELM_CHART = "helm_chart"
    TERRAFORM_MODULE = "terraform_module"
    SOURCE_CODE = "source_code"
    SBOM = "sbom"
    CUSTOM = "custom"


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms."""
    RSA_SHA256 = "rsa-sha256"
    ECDSA_P256 = "ecdsa-p256"
    ED25519 = "ed25519"


class VerificationStatus(str, Enum):
    """Signature verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    REVOKED = "revoked"
    NOT_SIGNED = "not_signed"


class ProvenanceLevel(str, Enum):
    """SLSA-inspired provenance levels."""
    LEVEL_0 = "level_0"  # No provenance
    LEVEL_1 = "level_1"  # Provenance exists, not authenticated
    LEVEL_2 = "level_2"  # Provenance authenticated, hosted build
    LEVEL_3 = "level_3"  # Hardened build environment


@dataclass
class BuildMetadata:
    """Build process metadata."""
    build_id: str
    builder_id: str
    build_type: str
    build_invocation_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Source information
    repository_url: Optional[str] = None
    repository_commit: Optional[str] = None
    repository_branch: Optional[str] = None
    repository_tag: Optional[str] = None
    
    # Build configuration
    build_config: Dict[str, Any] = field(default_factory=dict)
    build_params: Dict[str, Any] = field(default_factory=dict)
    
    # Environment
    build_environment: Dict[str, str] = field(default_factory=dict)
    builder_version: Optional[str] = None


@dataclass
class Signature:
    """Artifact signature."""
    signature_id: str
    algorithm: SignatureAlgorithm
    signature_value: str
    public_key_id: str
    signed_by: str
    content_hash: str
    
    # Optional fields
    signed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    public_key_pem: Optional[str] = None
    content_algorithm: str = "sha256"
    
    # Verification
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verified_at: Optional[datetime] = None
    verification_error: Optional[str] = None


@dataclass
class ProvenanceAttestation:
    """Provenance attestation for an artifact."""
    attestation_id: str
    artifact_id: str
    level: ProvenanceLevel
    
    # Build metadata
    build_metadata: BuildMetadata
    
    # Materials (inputs)
    materials: List[Dict[str, Any]] = field(default_factory=list)
    
    # Products (outputs)
    products: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    # Signature
    signature: Optional[Signature] = None
    
    # JSON serialization
    def to_json(self) -> str:
        """Convert to JSON representation."""
        data = {
            "_type": "https://in-toto.io/Statement/v0.1",
            "subject": [
                {
                    "name": self.artifact_id,
                    "digest": {"sha256": self.build_metadata.build_id}
                }
            ],
            "predicateType": "https://slsa.dev/provenance/v0.2",
            "predicate": {
                "builder": {
                    "id": self.build_metadata.builder_id
                },
                "buildType": self.build_metadata.build_type,
                "invocation": {
                    "configSource": {
                        "uri": self.build_metadata.repository_url,
                        "digest": {"sha256": self.build_metadata.repository_commit or ""},
                        "entryPoint": self.build_metadata.build_config.get("entry_point", "")
                    },
                    "parameters": self.build_metadata.build_params,
                    "environment": self.build_metadata.build_environment
                },
                "buildConfig": self.build_metadata.build_config,
                "metadata": {
                    "buildStartedOn": self.build_metadata.started_at.isoformat() if self.build_metadata.started_at else None,
                    "buildFinishedOn": self.build_metadata.completed_at.isoformat() if self.build_metadata.completed_at else None,
                    "completeness": {
                        "parameters": True,
                        "environment": True,
                        "materials": True
                    },
                    "reproducible": False
                },
                "materials": self.materials
            }
        }
        return json.dumps(data, indent=2, default=str)


@dataclass
class Artifact:
    """Artifact representation."""
    artifact_id: str
    name: str
    version: str
    artifact_type: ArtifactType
    
    # Content identification
    digest: str
    digest_algorithm: str = "sha256"
    size_bytes: int = 0
    
    # Storage
    storage_location: Optional[str] = None
    storage_provider: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Provenance
    provenance: Optional[ProvenanceAttestation] = None
    signatures: List[Signature] = field(default_factory=list)
    
    # Verification
    verification_status: VerificationStatus = VerificationStatus.PENDING
    last_verified_at: Optional[datetime] = None
    
    # Lifecycle
    is_deployed: bool = False
    deployment_count: int = 0
    last_deployed_at: Optional[datetime] = None


@dataclass
class VerificationPolicy:
    """Policy for artifact verification."""
    policy_id: str
    name: str
    description: str = ""
    
    # Requirements
    require_signature: bool = True
    require_provenance: bool = True
    minimum_provenance_level: ProvenanceLevel = ProvenanceLevel.LEVEL_1
    allowed_signature_algorithms: List[SignatureAlgorithm] = field(
        default_factory=lambda: [
            SignatureAlgorithm.RSA_SHA256,
            SignatureAlgorithm.ECDSA_P256,
            SignatureAlgorithm.ED25519
        ]
    )
    
    # Trust
    trusted_public_keys: List[str] = field(default_factory=list)
    trusted_builders: List[str] = field(default_factory=list)
    
    # Expiration
    signature_max_age_days: int = 365
    
    # Enforcement
    enforcement_mode: str = "enforce"  # enforce, warn, audit


@dataclass
class VerificationResult:
    """Result of artifact verification."""
    result_id: str
    artifact_id: str
    policy_id: str
    
    # Status
    status: VerificationStatus
    verified_at: datetime = field(default_factory=datetime.utcnow)
    verified_by: str = ""
    
    # Details
    signature_valid: bool = False
    signature_message: str = ""
    provenance_valid: bool = False
    provenance_message: str = ""
    policy_compliant: bool = False
    policy_violations: List[str] = field(default_factory=list)
    
    # Errors
    errors: List[str] = field(default_factory=list)


@dataclass
class ArtifactChain:
    """Chain of custody for an artifact."""
    chain_id: str
    artifact_id: str
    
    # Events
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Current state
    current_location: Optional[str] = None
    current_status: str = "created"
    
    def add_event(self, event_type: str, location: str, actor: str, details: Dict[str, Any] = None):
        """Add an event to the chain of custody."""
        event = {
            "event_type": event_type,
            "location": location,
            "actor": actor,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.events.append(event)
        self.current_location = location
        self.current_status = event_type


class SignatureEngine:
    """
    Cryptographic signature engine.
    
    Note: In production, this would integrate with proper crypto libraries
    like cryptography, pycryptodome, or cloud KMS services.
    """
    
    @staticmethod
    def generate_signature(
        content: bytes,
        private_key_pem: str,
        algorithm: SignatureAlgorithm,
        signer_id: str
    ) -> Signature:
        """Generate a signature for content."""
        # Calculate content hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Generate signature (simulated)
        # In production, use proper crypto library
        signature_data = f"{content_hash}:{signer_id}:{datetime.utcnow().isoformat()}"
        signature_value = base64.b64encode(
            hashlib.sha256(signature_data.encode()).digest()
        ).decode()
        
        return Signature(
            signature_id=f"sig_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hash(content_hash) % 10000:04d}",
            algorithm=algorithm,
            signature_value=signature_value,
            public_key_id=f"key_{signer_id}",
            signed_by=signer_id,
            signed_at=datetime.utcnow(),
            content_hash=content_hash,
            content_algorithm="sha256"
        )
    
    @staticmethod
    def verify_signature(content: bytes, signature: Signature) -> Tuple[bool, str]:
        """Verify a signature against content."""
        # Calculate content hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if content hash matches
        if content_hash != signature.content_hash:
            return False, "Content hash mismatch - artifact has been modified"
        
        # Verify signature (simulated)
        # In production, use proper crypto library
        signature_data = f"{content_hash}:{signature.signed_by}:{signature.signed_at.isoformat()}"
        expected_signature = base64.b64encode(
            hashlib.sha256(signature_data.encode()).digest()
        ).decode()
        
        if signature.signature_value != expected_signature:
            return False, "Signature verification failed - invalid signature"
        
        # Check expiration
        if signature.expires_at and signature.expires_at < datetime.utcnow():
            return False, "Signature has expired"
        
        return True, "Signature verified successfully"


class ArtifactProvenanceManager:
    """
    Central manager for artifact provenance and signature verification.
    
    Provides functionality for:
    - Artifact registration and tracking
    - Build metadata capture
    - Provenance attestation generation
    - Signature generation and verification
    - Verification policy enforcement
    - Chain of custody tracking
    """
    
    def __init__(self):
        self.artifacts: Dict[str, Artifact] = {}
        self.policies: Dict[str, VerificationPolicy] = {}
        self.verification_results: Dict[str, VerificationResult] = {}
        self.chains: Dict[str, ArtifactChain] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        self._signature_engine = SignatureEngine()
    
    async def initialize(self):
        """Initialize the artifact provenance manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default verification policy
            default_policy = VerificationPolicy(
                policy_id="default",
                name="Default Verification Policy",
                description="Default policy requiring signatures and provenance",
                require_signature=True,
                require_provenance=True,
                minimum_provenance_level=ProvenanceLevel.LEVEL_1
            )
            self.policies["default"] = default_policy
            
            self._initialized = True
            logger.info("ArtifactProvenanceManager initialized successfully")
    
    # Artifact Management
    
    async def register_artifact(
        self,
        name: str,
        version: str,
        artifact_type: ArtifactType,
        digest: str,
        size_bytes: int = 0,
        storage_location: Optional[str] = None,
        storage_provider: Optional[str] = None,
        created_by: str = "",
        labels: Optional[Dict[str, str]] = None
    ) -> Artifact:
        """Register a new artifact."""
        async with self._lock:
            artifact_id = f"artifact_{name}_{version}_{digest[:16]}"
            
            artifact = Artifact(
                artifact_id=artifact_id,
                name=name,
                version=version,
                artifact_type=artifact_type,
                digest=digest,
                size_bytes=size_bytes,
                storage_location=storage_location,
                storage_provider=storage_provider,
                created_by=created_by,
                labels=labels or {}
            )
            
            self.artifacts[artifact_id] = artifact
            
            # Create chain of custody
            chain = ArtifactChain(
                chain_id=f"chain_{artifact_id}",
                artifact_id=artifact_id
            )
            chain.add_event(
                event_type="registered",
                location=storage_location or "unknown",
                actor=created_by,
                details={"digest": digest, "size": size_bytes}
            )
            self.chains[artifact_id] = chain
            
            logger.info(f"Registered artifact: {artifact_id}")
            return artifact
    
    async def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID."""
        return self.artifacts.get(artifact_id)
    
    async def list_artifacts(
        self,
        artifact_type: Optional[ArtifactType] = None,
        verification_status: Optional[VerificationStatus] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> List[Artifact]:
        """List artifacts with optional filtering."""
        artifacts = list(self.artifacts.values())
        
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        
        if verification_status:
            artifacts = [a for a in artifacts if a.verification_status == verification_status]
        
        if labels:
            artifacts = [
                a for a in artifacts
                if all(a.labels.get(k) == v for k, v in labels.items())
            ]
        
        return sorted(artifacts, key=lambda a: a.created_at, reverse=True)
    
    async def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        async with self._lock:
            if artifact_id not in self.artifacts:
                return False
            
            del self.artifacts[artifact_id]
            if artifact_id in self.chains:
                del self.chains[artifact_id]
            
            logger.info(f"Deleted artifact: {artifact_id}")
            return True
    
    # Provenance Management
    
    async def create_provenance(
        self,
        artifact_id: str,
        build_metadata: BuildMetadata,
        level: ProvenanceLevel = ProvenanceLevel.LEVEL_1,
        materials: Optional[List[Dict[str, Any]]] = None,
        products: Optional[List[Dict[str, Any]]] = None,
        created_by: str = ""
    ) -> Optional[ProvenanceAttestation]:
        """Create provenance attestation for an artifact."""
        async with self._lock:
            artifact = self.artifacts.get(artifact_id)
            if not artifact:
                return None
            
            attestation = ProvenanceAttestation(
                attestation_id=f"attest_{artifact_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                artifact_id=artifact_id,
                level=level,
                build_metadata=build_metadata,
                materials=materials or [],
                products=products or [],
                created_by=created_by
            )
            
            artifact.provenance = attestation
            
            # Update chain of custody
            if artifact_id in self.chains:
                self.chains[artifact_id].add_event(
                    event_type="provenance_created",
                    location=artifact.storage_location or "unknown",
                    actor=created_by,
                    details={"level": level.value, "builder": build_metadata.builder_id}
                )
            
            logger.info(f"Created provenance attestation: {attestation.attestation_id}")
            return attestation
    
    async def get_provenance(self, artifact_id: str) -> Optional[ProvenanceAttestation]:
        """Get provenance attestation for an artifact."""
        artifact = self.artifacts.get(artifact_id)
        return artifact.provenance if artifact else None
    
    # Signature Management
    
    async def sign_artifact(
        self,
        artifact_id: str,
        private_key_pem: str,
        algorithm: SignatureAlgorithm,
        signer_id: str,
        expires_at: Optional[datetime] = None
    ) -> Optional[Signature]:
        """Sign an artifact."""
        async with self._lock:
            artifact = self.artifacts.get(artifact_id)
            if not artifact:
                return None
            
            # Create content to sign (artifact metadata)
            content = json.dumps({
                "artifact_id": artifact_id,
                "digest": artifact.digest,
                "digest_algorithm": artifact.digest_algorithm,
                "created_at": artifact.created_at.isoformat()
            }, sort_keys=True).encode()
            
            # Generate signature
            signature = self._signature_engine.generate_signature(
                content=content,
                private_key_pem=private_key_pem,
                algorithm=algorithm,
                signer_id=signer_id
            )
            
            signature.expires_at = expires_at
            signature.verification_status = VerificationStatus.VERIFIED
            
            artifact.signatures.append(signature)
            
            logger.info(f"Signed artifact {artifact_id} with signature {signature.signature_id}")
            return signature
    
    async def verify_artifact(
        self,
        artifact_id: str,
        policy_id: str = "default"
    ) -> Optional[VerificationResult]:
        """Verify an artifact against a policy."""
        async with self._lock:
            artifact = self.artifacts.get(artifact_id)
            policy = self.policies.get(policy_id)
            
            if not artifact:
                return None
            
            if not policy:
                return None
            
            result_id = f"verify_{artifact_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            result = VerificationResult(
                result_id=result_id,
                artifact_id=artifact_id,
                policy_id=policy_id,
                status=VerificationStatus.PENDING,
                verified_at=datetime.utcnow()
            )
            
            # Create content for verification
            content = json.dumps({
                "artifact_id": artifact_id,
                "digest": artifact.digest,
                "digest_algorithm": artifact.digest_algorithm,
                "created_at": artifact.created_at.isoformat()
            }, sort_keys=True).encode()
            
            # Verify signatures
            if policy.require_signature:
                if not artifact.signatures:
                    result.signature_valid = False
                    result.signature_message = "No signatures found"
                    result.policy_violations.append("Artifact is not signed")
                else:
                    # Verify at least one valid signature
                    valid_found = False
                    for sig in artifact.signatures:
                        is_valid, message = self._signature_engine.verify_signature(content, sig)
                        if is_valid:
                            valid_found = True
                            sig.verification_status = VerificationStatus.VERIFIED
                            sig.verified_at = datetime.utcnow()
                        else:
                            sig.verification_status = VerificationStatus.FAILED
                            sig.verification_error = message
                    
                    result.signature_valid = valid_found
                    result.signature_message = "Valid signature found" if valid_found else "No valid signatures"
                    
                    if not valid_found:
                        result.policy_violations.append("No valid signatures found")
            else:
                result.signature_valid = True
                result.signature_message = "Signature not required"
            
            # Verify provenance
            if policy.require_provenance:
                if not artifact.provenance:
                    result.provenance_valid = False
                    result.provenance_message = "No provenance attestation found"
                    result.policy_violations.append("Artifact has no provenance")
                else:
                    provenance = artifact.provenance
                    
                    # Check provenance level
                    level_ok = provenance.level.value >= policy.minimum_provenance_level.value
                    
                    if level_ok:
                        result.provenance_valid = True
                        result.provenance_message = f"Provenance meets minimum level {policy.minimum_provenance_level.value}"
                    else:
                        result.provenance_valid = False
                        result.provenance_message = f"Provenance level {provenance.level.value} below minimum {policy.minimum_provenance_level.value}"
                        result.policy_violations.append(f"Provenance level insufficient")
            else:
                result.provenance_valid = True
                result.provenance_message = "Provenance not required"
            
            # Determine final status
            result.policy_compliant = len(result.policy_violations) == 0
            
            if result.policy_compliant:
                result.status = VerificationStatus.VERIFIED
                artifact.verification_status = VerificationStatus.VERIFIED
            else:
                result.status = VerificationStatus.FAILED
                artifact.verification_status = VerificationStatus.FAILED
            
            artifact.last_verified_at = datetime.utcnow()
            
            self.verification_results[result_id] = result
            
            logger.info(f"Verification completed for {artifact_id}: {result.status.value}")
            return result
    
    # Policy Management
    
    async def create_policy(
        self,
        policy_id: str,
        name: str,
        description: str = "",
        require_signature: bool = True,
        require_provenance: bool = True,
        minimum_provenance_level: ProvenanceLevel = ProvenanceLevel.LEVEL_1,
        enforcement_mode: str = "enforce"
    ) -> VerificationPolicy:
        """Create a verification policy."""
        async with self._lock:
            policy = VerificationPolicy(
                policy_id=policy_id,
                name=name,
                description=description,
                require_signature=require_signature,
                require_provenance=require_provenance,
                minimum_provenance_level=minimum_provenance_level,
                enforcement_mode=enforcement_mode
            )
            
            self.policies[policy_id] = policy
            logger.info(f"Created verification policy: {policy_id}")
            return policy
    
    async def get_policy(self, policy_id: str) -> Optional[VerificationPolicy]:
        """Get verification policy by ID."""
        return self.policies.get(policy_id)
    
    async def list_policies(self) -> List[VerificationPolicy]:
        """List all verification policies."""
        return list(self.policies.values())
    
    # Chain of Custody
    
    async def get_chain_of_custody(self, artifact_id: str) -> Optional[ArtifactChain]:
        """Get chain of custody for an artifact."""
        return self.chains.get(artifact_id)
    
    async def record_deployment(
        self,
        artifact_id: str,
        deployment_location: str,
        deployed_by: str,
        deployment_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record an artifact deployment event."""
        async with self._lock:
            artifact = self.artifacts.get(artifact_id)
            chain = self.chains.get(artifact_id)
            
            if not artifact or not chain:
                return False
            
            artifact.is_deployed = True
            artifact.deployment_count += 1
            artifact.last_deployed_at = datetime.utcnow()
            
            chain.add_event(
                event_type="deployed",
                location=deployment_location,
                actor=deployed_by,
                details=deployment_details
            )
            
            logger.info(f"Recorded deployment of {artifact_id} to {deployment_location}")
            return True
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get artifact provenance statistics."""
        artifacts = list(self.artifacts.values())
        verifications = list(self.verification_results.values())
        
        return {
            "artifacts": {
                "total": len(artifacts),
                "by_type": {
                    at.value: len([a for a in artifacts if a.artifact_type == at])
                    for at in ArtifactType
                },
                "by_verification_status": {
                    vs.value: len([a for a in artifacts if a.verification_status == vs])
                    for vs in VerificationStatus
                },
                "deployed": len([a for a in artifacts if a.is_deployed]),
                "with_provenance": len([a for a in artifacts if a.provenance]),
                "with_signatures": len([a for a in artifacts if a.signatures])
            },
            "policies": {
                "total": len(self.policies)
            },
            "verifications": {
                "total": len(verifications),
                "passed": len([v for v in verifications if v.status == VerificationStatus.VERIFIED]),
                "failed": len([v for v in verifications if v.status == VerificationStatus.FAILED])
            }
        }


# Global manager instance
_provenance_manager: Optional[ArtifactProvenanceManager] = None


async def get_provenance_manager() -> ArtifactProvenanceManager:
    """Get or create the global provenance manager."""
    global _provenance_manager
    if _provenance_manager is None:
        _provenance_manager = ArtifactProvenanceManager()
        await _provenance_manager.initialize()
    return _provenance_manager


def reset_provenance_manager():
    """Reset the global provenance manager (for testing)."""
    global _provenance_manager
    _provenance_manager = None
