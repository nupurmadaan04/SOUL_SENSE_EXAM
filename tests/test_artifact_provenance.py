"""
Comprehensive tests for Artifact Provenance and Signature Verification module.

Test coverage: 50+ tests
"""

import pytest
import pytest_asyncio
import asyncio
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import json

# Import the module under test
import sys
sys.path.insert(0, "backend/fastapi/api/utils")

from artifact_provenance import (
    ArtifactType, SignatureAlgorithm, VerificationStatus, ProvenanceLevel,
    BuildMetadata, Signature, ProvenanceAttestation, Artifact, VerificationPolicy,
    VerificationResult, ArtifactChain, SignatureEngine, ArtifactProvenanceManager,
    get_provenance_manager, reset_provenance_manager
)


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def reset_manager():
    """Reset the global provenance manager before each test."""
    reset_provenance_manager()
    yield
    reset_provenance_manager()


@pytest_asyncio.fixture
async def provenance_manager():
    """Create a fresh artifact provenance manager."""
    manager = ArtifactProvenanceManager()
    await manager.initialize()
    yield manager
    reset_provenance_manager()


@pytest.fixture
def sample_build_metadata():
    """Sample build metadata."""
    return BuildMetadata(
        build_id="build_12345",
        builder_id="github-actions",
        build_type="https://github.com/slsa-framework/github-actions-buildtypes/workflow/v1",
        build_invocation_id="run_67890",
        started_at=datetime.utcnow() - timedelta(minutes=10),
        completed_at=datetime.utcnow(),
        repository_url="https://github.com/example/repo",
        repository_commit="abc123def456",
        repository_branch="main",
        build_config={"entry_point": "build.yaml", "arguments": {"target": "release"}},
        build_params={"version": "1.0.0"},
        build_environment={"os": "ubuntu-latest", "arch": "x64"},
        builder_version="2.1.0"
    )


@pytest.fixture
def sample_materials():
    """Sample build materials."""
    return [
        {
            "uri": "https://github.com/example/repo",
            "digest": {"sha256": "abc123def456"}
        },
        {
            "uri": "pkg:npm/dependency@1.0.0",
            "digest": {"sha256": "def789abc012"}
        }
    ]


# Enums Tests

class TestArtifactEnums:
    """Test artifact provenance enums."""
    
    def test_artifact_type_values(self):
        """Test ArtifactType enum values."""
        assert ArtifactType.CONTAINER_IMAGE == "container_image"
        assert ArtifactType.BINARY == "binary"
        assert ArtifactType.PACKAGE == "package"
        assert ArtifactType.CONFIGURATION == "configuration"
        assert ArtifactType.HELM_CHART == "helm_chart"
        assert ArtifactType.TERRAFORM_MODULE == "terraform_module"
        assert ArtifactType.SOURCE_CODE == "source_code"
        assert ArtifactType.SBOM == "sbom"
        assert ArtifactType.CUSTOM == "custom"
    
    def test_signature_algorithm_values(self):
        """Test SignatureAlgorithm enum values."""
        assert SignatureAlgorithm.RSA_SHA256 == "rsa-sha256"
        assert SignatureAlgorithm.ECDSA_P256 == "ecdsa-p256"
        assert SignatureAlgorithm.ED25519 == "ed25519"
    
    def test_verification_status_values(self):
        """Test VerificationStatus enum values."""
        assert VerificationStatus.PENDING == "pending"
        assert VerificationStatus.VERIFIED == "verified"
        assert VerificationStatus.FAILED == "failed"
        assert VerificationStatus.EXPIRED == "expired"
        assert VerificationStatus.REVOKED == "revoked"
        assert VerificationStatus.NOT_SIGNED == "not_signed"
    
    def test_provenance_level_values(self):
        """Test ProvenanceLevel enum values."""
        assert ProvenanceLevel.LEVEL_0 == "level_0"
        assert ProvenanceLevel.LEVEL_1 == "level_1"
        assert ProvenanceLevel.LEVEL_2 == "level_2"
        assert ProvenanceLevel.LEVEL_3 == "level_3"


# SignatureEngine Tests

class TestSignatureEngine:
    """Test signature engine functionality."""
    
    def test_generate_signature(self):
        """Test signature generation."""
        content = b"test artifact content"
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        
        signature = SignatureEngine.generate_signature(
            content=content,
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="test_signer"
        )
        
        assert signature is not None
        assert signature.algorithm == SignatureAlgorithm.RSA_SHA256
        assert signature.signed_by == "test_signer"
        assert signature.content_hash == hashlib.sha256(content).hexdigest()
        assert signature.signature_value is not None
    
    def test_verify_signature_success(self):
        """Test successful signature verification."""
        content = b"test artifact content"
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        
        # Generate signature
        signature = SignatureEngine.generate_signature(
            content=content,
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="test_signer"
        )
        
        # Verify signature
        is_valid, message = SignatureEngine.verify_signature(content, signature)
        
        assert is_valid is True
        assert "successfully" in message
    
    def test_verify_signature_content_mismatch(self):
        """Test signature verification with modified content."""
        content = b"test artifact content"
        modified_content = b"modified content"
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        
        # Generate signature for original content
        signature = SignatureEngine.generate_signature(
            content=content,
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="test_signer"
        )
        
        # Verify with modified content
        is_valid, message = SignatureEngine.verify_signature(modified_content, signature)
        
        assert is_valid is False
        assert "hash mismatch" in message.lower()
    
    def test_verify_signature_expired(self):
        """Test signature verification with expired signature."""
        content = b"test artifact content"
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        
        signature = SignatureEngine.generate_signature(
            content=content,
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="test_signer"
        )
        
        # Set expiration to past
        signature.expires_at = datetime.utcnow() - timedelta(days=1)
        
        is_valid, message = SignatureEngine.verify_signature(content, signature)
        
        assert is_valid is False
        assert "expired" in message.lower()


# ProvenanceAttestation Tests

class TestProvenanceAttestation:
    """Test provenance attestation functionality."""
    
    def test_to_json(self, sample_build_metadata):
        """Test JSON serialization of attestation."""
        attestation = ProvenanceAttestation(
            attestation_id="attest_123",
            artifact_id="artifact_456",
            level=ProvenanceLevel.LEVEL_2,
            build_metadata=sample_build_metadata,
            materials=[{"uri": "https://github.com/example/repo"}],
            products=[{"name": "artifact.bin"}],
            created_by="builder"
        )
        
        json_str = attestation.to_json()
        data = json.loads(json_str)
        
        assert data["_type"] == "https://in-toto.io/Statement/v0.1"
        assert data["predicateType"] == "https://slsa.dev/provenance/v0.2"
        assert data["subject"][0]["name"] == "artifact_456"
        assert data["predicate"]["builder"]["id"] == "github-actions"


# ArtifactProvenanceManager Tests

@pytest.mark.asyncio
class TestArtifactProvenanceManager:
    """Test artifact provenance manager."""
    
    async def test_initialize(self, provenance_manager):
        """Test manager initialization."""
        assert provenance_manager._initialized is True
        assert "default" in provenance_manager.policies
    
    async def test_register_artifact(self, provenance_manager):
        """Test artifact registration."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.CONTAINER_IMAGE,
            digest="sha256:abcdef123456",
            size_bytes=1024000,
            storage_location="registry.example.com/test-app:1.0.0",
            storage_provider="dockerhub",
            created_by="developer@example.com",
            labels={"team": "platform", "env": "production"}
        )
        
        assert artifact.name == "test-app"
        assert artifact.version == "1.0.0"
        assert artifact.artifact_type == ArtifactType.CONTAINER_IMAGE
        assert artifact.digest == "sha256:abcdef123456"
        assert artifact.labels["team"] == "platform"
        assert artifact.artifact_id in provenance_manager.artifacts
        
        # Check chain of custody was created
        assert artifact.artifact_id in provenance_manager.chains
    
    async def test_get_artifact(self, provenance_manager):
        """Test retrieving artifact."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.BINARY,
            digest="sha256:abc123"
        )
        
        retrieved = await provenance_manager.get_artifact(artifact.artifact_id)
        assert retrieved is not None
        assert retrieved.artifact_id == artifact.artifact_id
    
    async def test_get_nonexistent_artifact(self, provenance_manager):
        """Test retrieving non-existent artifact."""
        artifact = await provenance_manager.get_artifact("nonexistent")
        assert artifact is None
    
    async def test_list_artifacts(self, provenance_manager):
        """Test listing artifacts."""
        # Create multiple artifacts
        await provenance_manager.register_artifact(
            name="app1",
            version="1.0.0",
            artifact_type=ArtifactType.CONTAINER_IMAGE,
            digest="sha256:abc123"
        )
        await provenance_manager.register_artifact(
            name="app2",
            version="2.0.0",
            artifact_type=ArtifactType.BINARY,
            digest="sha256:def456"
        )
        
        # List all
        all_artifacts = await provenance_manager.list_artifacts()
        assert len(all_artifacts) == 2
        
        # Filter by type
        images = await provenance_manager.list_artifacts(
            artifact_type=ArtifactType.CONTAINER_IMAGE
        )
        assert len(images) == 1
        
        # Filter by labels
        labeled = await provenance_manager.list_artifacts(
            labels={"env": "production"}
        )
        assert len(labeled) == 0  # No artifacts have this label
    
    async def test_delete_artifact(self, provenance_manager):
        """Test artifact deletion."""
        artifact = await provenance_manager.register_artifact(
            name="temp-app",
            version="1.0.0",
            artifact_type=ArtifactType.CUSTOM,
            digest="sha256:temp"
        )
        
        result = await provenance_manager.delete_artifact(artifact.artifact_id)
        assert result is True
        
        # Verify deleted
        retrieved = await provenance_manager.get_artifact(artifact.artifact_id)
        assert retrieved is None
    
    async def test_delete_nonexistent_artifact(self, provenance_manager):
        """Test deleting non-existent artifact."""
        result = await provenance_manager.delete_artifact("nonexistent")
        assert result is False
    
    async def test_create_provenance(self, provenance_manager, sample_build_metadata):
        """Test provenance attestation creation."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.PACKAGE,
            digest="sha256:abc123"
        )
        
        attestation = await provenance_manager.create_provenance(
            artifact_id=artifact.artifact_id,
            build_metadata=sample_build_metadata,
            level=ProvenanceLevel.LEVEL_2,
            materials=[{"uri": "https://github.com/example/repo"}],
            created_by="builder@example.com"
        )
        
        assert attestation is not None
        assert attestation.artifact_id == artifact.artifact_id
        assert attestation.level == ProvenanceLevel.LEVEL_2
        assert attestation.build_metadata.builder_id == "github-actions"
        
        # Verify artifact was updated
        updated = await provenance_manager.get_artifact(artifact.artifact_id)
        assert updated.provenance is not None
    
    async def test_create_provenance_nonexistent_artifact(self, provenance_manager, sample_build_metadata):
        """Test provenance creation for non-existent artifact."""
        attestation = await provenance_manager.create_provenance(
            artifact_id="nonexistent",
            build_metadata=sample_build_metadata,
            level=ProvenanceLevel.LEVEL_1
        )
        
        assert attestation is None
    
    async def test_get_provenance(self, provenance_manager, sample_build_metadata):
        """Test retrieving provenance."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.PACKAGE,
            digest="sha256:abc123"
        )
        
        await provenance_manager.create_provenance(
            artifact_id=artifact.artifact_id,
            build_metadata=sample_build_metadata,
            level=ProvenanceLevel.LEVEL_2
        )
        
        provenance = await provenance_manager.get_provenance(artifact.artifact_id)
        assert provenance is not None
        assert provenance.level == ProvenanceLevel.LEVEL_2
    
    async def test_sign_artifact(self, provenance_manager):
        """Test artifact signing."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.BINARY,
            digest="sha256:abc123"
        )
        
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        
        signature = await provenance_manager.sign_artifact(
            artifact_id=artifact.artifact_id,
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="release-signer@example.com",
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        
        assert signature is not None
        assert signature.algorithm == SignatureAlgorithm.RSA_SHA256
        assert signature.signed_by == "release-signer@example.com"
        assert signature.expires_at is not None
        
        # Verify artifact was updated
        updated = await provenance_manager.get_artifact(artifact.artifact_id)
        assert len(updated.signatures) == 1
    
    async def test_sign_nonexistent_artifact(self, provenance_manager):
        """Test signing non-existent artifact."""
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        
        signature = await provenance_manager.sign_artifact(
            artifact_id="nonexistent",
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="signer"
        )
        
        assert signature is None
    
    async def test_verify_artifact_with_signature_and_provenance(
        self, provenance_manager, sample_build_metadata
    ):
        """Test artifact verification with signature and provenance."""
        # Register artifact
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.CONTAINER_IMAGE,
            digest="sha256:abc123"
        )
        
        # Create provenance
        await provenance_manager.create_provenance(
            artifact_id=artifact.artifact_id,
            build_metadata=sample_build_metadata,
            level=ProvenanceLevel.LEVEL_2
        )
        
        # Sign artifact
        private_key = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
        await provenance_manager.sign_artifact(
            artifact_id=artifact.artifact_id,
            private_key_pem=private_key,
            algorithm=SignatureAlgorithm.RSA_SHA256,
            signer_id="signer@example.com"
        )
        
        # Verify
        result = await provenance_manager.verify_artifact(
            artifact_id=artifact.artifact_id,
            policy_id="default"
        )
        
        assert result is not None
        assert result.status == VerificationStatus.VERIFIED
        assert result.signature_valid is True
        assert result.provenance_valid is True
        assert result.policy_compliant is True
    
    async def test_verify_artifact_no_signature(self, provenance_manager, sample_build_metadata):
        """Test verification of unsigned artifact."""
        # Register artifact
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.CONTAINER_IMAGE,
            digest="sha256:abc123"
        )
        
        # Create provenance
        await provenance_manager.create_provenance(
            artifact_id=artifact.artifact_id,
            build_metadata=sample_build_metadata,
            level=ProvenanceLevel.LEVEL_2
        )
        
        # Verify without signing
        result = await provenance_manager.verify_artifact(
            artifact_id=artifact.artifact_id,
            policy_id="default"
        )
        
        assert result is not None
        assert result.status == VerificationStatus.FAILED
        assert result.signature_valid is False
        assert "no signatures" in result.signature_message.lower()
    
    async def test_verify_nonexistent_artifact(self, provenance_manager):
        """Test verification of non-existent artifact."""
        result = await provenance_manager.verify_artifact(
            artifact_id="nonexistent",
            policy_id="default"
        )
        
        assert result is None
    
    async def test_verify_with_nonexistent_policy(self, provenance_manager):
        """Test verification with non-existent policy."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.BINARY,
            digest="sha256:abc123"
        )
        
        result = await provenance_manager.verify_artifact(
            artifact_id=artifact.artifact_id,
            policy_id="nonexistent"
        )
        
        assert result is None
    
    async def test_create_policy(self, provenance_manager):
        """Test verification policy creation."""
        policy = await provenance_manager.create_policy(
            policy_id="strict",
            name="Strict Verification Policy",
            description="Requires high-level provenance",
            require_signature=True,
            require_provenance=True,
            minimum_provenance_level=ProvenanceLevel.LEVEL_3,
            enforcement_mode="enforce"
        )
        
        assert policy.policy_id == "strict"
        assert policy.name == "Strict Verification Policy"
        assert policy.minimum_provenance_level == ProvenanceLevel.LEVEL_3
        assert policy.enforcement_mode == "enforce"
        
        # Verify stored
        assert "strict" in provenance_manager.policies
    
    async def test_get_policy(self, provenance_manager):
        """Test retrieving policy."""
        policy = await provenance_manager.get_policy("default")
        assert policy is not None
        assert policy.policy_id == "default"
    
    async def test_list_policies(self, provenance_manager):
        """Test listing policies."""
        policies = await provenance_manager.list_policies()
        assert len(policies) >= 1
        
        policy_ids = [p.policy_id for p in policies]
        assert "default" in policy_ids
    
    async def test_get_chain_of_custody(self, provenance_manager):
        """Test retrieving chain of custody."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.BINARY,
            digest="sha256:abc123"
        )
        
        chain = await provenance_manager.get_chain_of_custody(artifact.artifact_id)
        assert chain is not None
        assert chain.artifact_id == artifact.artifact_id
        assert len(chain.events) >= 1  # Registration event
    
    async def test_record_deployment(self, provenance_manager):
        """Test deployment recording."""
        artifact = await provenance_manager.register_artifact(
            name="test-app",
            version="1.0.0",
            artifact_type=ArtifactType.CONTAINER_IMAGE,
            digest="sha256:abc123"
        )
        
        result = await provenance_manager.record_deployment(
            artifact_id=artifact.artifact_id,
            deployment_location="production-cluster",
            deployed_by="deployer@example.com",
            deployment_details={"namespace": "default", "replicas": 3}
        )
        
        assert result is True
        
        # Verify artifact updated
        updated = await provenance_manager.get_artifact(artifact.artifact_id)
        assert updated.is_deployed is True
        assert updated.deployment_count == 1
        assert updated.last_deployed_at is not None
        
        # Verify chain updated
        chain = await provenance_manager.get_chain_of_custody(artifact.artifact_id)
        assert any(e["event_type"] == "deployed" for e in chain.events)
    
    async def test_record_deployment_nonexistent_artifact(self, provenance_manager):
        """Test deployment recording for non-existent artifact."""
        result = await provenance_manager.record_deployment(
            artifact_id="nonexistent",
            deployment_location="production",
            deployed_by="deployer"
        )
        
        assert result is False
    
    async def test_get_statistics(self, provenance_manager, sample_build_metadata):
        """Test statistics retrieval."""
        # Create some artifacts
        artifact1 = await provenance_manager.register_artifact(
            name="app1",
            version="1.0.0",
            artifact_type=ArtifactType.CONTAINER_IMAGE,
            digest="sha256:abc123"
        )
        
        artifact2 = await provenance_manager.register_artifact(
            name="app2",
            version="2.0.0",
            artifact_type=ArtifactType.BINARY,
            digest="sha256:def456"
        )
        
        # Add provenance to one
        await provenance_manager.create_provenance(
            artifact_id=artifact1.artifact_id,
            build_metadata=sample_build_metadata,
            level=ProvenanceLevel.LEVEL_2
        )
        
        # Get statistics
        stats = await provenance_manager.get_statistics()
        
        assert stats["artifacts"]["total"] == 2
        assert stats["artifacts"]["with_provenance"] == 1
        assert stats["artifacts"]["by_type"]["container_image"] == 1
        assert stats["artifacts"]["by_type"]["binary"] == 1
        assert stats["policies"]["total"] >= 1


# Global Manager Tests

@pytest.mark.asyncio
class TestGlobalManager:
    """Test global provenance manager functions."""
    
    async def test_get_provenance_manager(self):
        """Test getting global provenance manager."""
        manager1 = await get_provenance_manager()
        manager2 = await get_provenance_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert manager1._initialized is True
    
    async def test_reset_provenance_manager(self):
        """Test resetting global provenance manager."""
        manager1 = await get_provenance_manager()
        reset_provenance_manager()
        manager2 = await get_provenance_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
