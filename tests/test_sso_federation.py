"""
Comprehensive tests for SSO Federation module.

Tests cover:
- Identity provider management
- Service provider configuration
- Federation partnerships
- SAML assertion processing
- Session management
- Audit logging
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend.fastapi.api.utils.sso_federation import (
    SSOFederationManager,
    SSOProtocol,
    IdPStatus,
    FederationStatus,
    AssertionStatus,
    IdentityProvider,
    ServiceProvider,
    FederationPartnership,
    SAMLAssertion,
    FederatedSession,
    SSOSessionManager,
    SAMLValidator,
    SSOMetadataParser,
    get_federation_manager,
    reset_federation_manager
)


# Fixtures

def get_manager_sync():
    """Get federation manager synchronously."""
    reset_federation_manager()
    return asyncio.run(get_federation_manager())


@pytest.fixture
def federation_manager():
    """Fixture for federation manager."""
    manager = get_manager_sync()
    yield manager
    reset_federation_manager()


@pytest.fixture
def sample_idp_data():
    """Sample IdP data for testing."""
    return {
        "name": "Test IdP",
        "description": "Test Identity Provider",
        "protocol": SSOProtocol.SAML2,
        "entity_id": "https://idp.example.com/entity"
    }


@pytest.fixture
def sample_sp_data():
    """Sample SP data for testing."""
    return {
        "name": "Test SP",
        "description": "Test Service Provider",
        "entity_id": "https://sp.example.com/entity",
        "acs_url": "https://sp.example.com/saml/acs"
    }


# Unit Tests

class TestSSOProtocols:
    """Test SSO protocol enums."""
    
    def test_protocol_values(self):
        """Test that all protocols have correct values."""
        assert SSOProtocol.SAML2.value == "saml2"
        assert SSOProtocol.OAUTH2.value == "oauth2"
        assert SSOProtocol.OIDC.value == "oidc"
        assert SSOProtocol.WS_FED.value == "ws_fed"
        assert SSOProtocol.CUSTOM.value == "custom"


class TestIdPStatus:
    """Test IdP status enums."""
    
    def test_status_values(self):
        """Test that all statuses have correct values."""
        assert IdPStatus.ACTIVE.value == "active"
        assert IdPStatus.INACTIVE.value == "inactive"
        assert IdPStatus.MAINTENANCE.value == "maintenance"


class TestFederationStatus:
    """Test federation status enums."""
    
    def test_status_values(self):
        """Test that all federation statuses have correct values."""
        assert FederationStatus.PENDING.value == "pending"
        assert FederationStatus.ACTIVE.value == "active"
        assert FederationStatus.SUSPENDED.value == "suspended"
        assert FederationStatus.REVOKED.value == "revoked"


class TestSAMLValidator:
    """Test SAML validation utilities."""
    
    def test_decode_saml_response(self):
        """Test decoding Base64 SAML response."""
        import base64
        original = "<saml>test</saml>"
        encoded = base64.b64encode(original.encode()).decode()
        
        decoded = SAMLValidator.decode_saml_response(encoded)
        assert decoded == original
    
    def test_validate_valid_assertion(self):
        """Test validating a valid SAML assertion."""
        assertion = SAMLAssertion(
            assertion_id="assert_123",
            issuer="https://idp.example.com",
            subject="user@example.com",
            audience="https://sp.example.com",
            issue_instant=datetime.utcnow(),
            not_before=datetime.utcnow() - timedelta(minutes=5),
            not_on_or_after=datetime.utcnow() + timedelta(hours=8),
            signature_valid=True
        )
        
        status = SAMLValidator.validate_assertion(
            assertion,
            expected_audience="https://sp.example.com",
            idp_certificate="mock_cert"
        )
        
        assert status == AssertionStatus.VALID
    
    def test_validate_expired_assertion(self):
        """Test validating an expired SAML assertion."""
        assertion = SAMLAssertion(
            assertion_id="assert_123",
            issuer="https://idp.example.com",
            subject="user@example.com",
            audience="https://sp.example.com",
            issue_instant=datetime.utcnow() - timedelta(hours=10),
            not_before=datetime.utcnow() - timedelta(hours=10),
            not_on_or_after=datetime.utcnow() - timedelta(hours=2),
            signature_valid=True
        )
        
        status = SAMLValidator.validate_assertion(
            assertion,
            expected_audience="https://sp.example.com",
            idp_certificate="mock_cert"
        )
        
        assert status == AssertionStatus.EXPIRED


class TestSSOMetadataParser:
    """Test SSO metadata parser."""
    
    def test_parse_saml_metadata(self):
        """Test parsing SAML 2.0 metadata XML."""
        metadata_xml = """<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://idp.example.com">
    <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://idp.example.com/sso"/>
        <md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://idp.example.com/slo"/>
        <md:KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>MIICiDCCAX...</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>
    </md:IDPSSODescriptor>
</md:EntityDescriptor>"""
        
        parsed = SSOMetadataParser.parse_saml_metadata(metadata_xml)
        
        assert parsed["entity_id"] == "https://idp.example.com"
        assert parsed["sso_url"] == "https://idp.example.com/sso"
        assert parsed["slo_url"] == "https://idp.example.com/slo"
        assert parsed["certificate"] == "MIICiDCCAX..."


class TestSSOSessionManager:
    """Test SSO session manager."""
    
    def test_create_session(self):
        """Test creating a session."""
        manager = SSOSessionManager()
        
        session = manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def"
        )
        
        assert session.session_id is not None
        assert session.user_id == "user_123"
        assert session.is_active is True
    
    def test_validate_session(self):
        """Test validating a session."""
        manager = SSOSessionManager()
        
        session = manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def"
        )
        
        assert manager.validate_session(session.session_id) is True
    
    def test_validate_expired_session(self):
        """Test validating an expired session."""
        manager = SSOSessionManager()
        
        session = manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def",
            session_duration_hours=-1  # Already expired
        )
        
        assert manager.validate_session(session.session_id) is False
    
    def test_access_session(self):
        """Test recording access to a session."""
        manager = SSOSessionManager()
        
        session = manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def"
        )
        
        result = manager.access_session(session.session_id, "product_a")
        assert result is True
        assert "product_a" in session.products_accessed
        assert session.access_count == 1
    
    def test_terminate_session(self):
        """Test terminating a session."""
        manager = SSOSessionManager()
        
        session = manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def"
        )
        
        result = manager.terminate_session(session.session_id)
        assert result is True
        assert session.is_active is False


class TestFederationManagerInitialization:
    """Test federation manager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, federation_manager):
        """Test that manager initializes correctly."""
        assert federation_manager._initialized is True
        assert "sp_default" in federation_manager.sps  # Default SP created


class TestIdPManagement:
    """Test identity provider management."""
    
    @pytest.mark.asyncio
    async def test_create_idp(self, federation_manager, sample_idp_data):
        """Test creating an IdP."""
        idp = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        assert idp.idp_id is not None
        assert idp.name == sample_idp_data["name"]
        assert idp.status == IdPStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_get_idp(self, federation_manager, sample_idp_data):
        """Test retrieving an IdP."""
        created = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        retrieved = await federation_manager.get_idp(created.idp_id)
        assert retrieved is not None
        assert retrieved.idp_id == created.idp_id
    
    @pytest.mark.asyncio
    async def test_update_idp(self, federation_manager, sample_idp_data):
        """Test updating an IdP."""
        created = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        updated = await federation_manager.update_idp(
            created.idp_id,
            {"name": "Updated IdP Name", "status": IdPStatus.MAINTENANCE}
        )
        
        assert updated is not None
        assert updated.name == "Updated IdP Name"
        assert updated.status == IdPStatus.MAINTENANCE
    
    @pytest.mark.asyncio
    async def test_delete_idp(self, federation_manager, sample_idp_data):
        """Test deleting an IdP."""
        created = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        success = await federation_manager.delete_idp(created.idp_id)
        assert success is True
        
        # Verify deletion
        idp = await federation_manager.get_idp(created.idp_id)
        assert idp is None
    
    @pytest.mark.asyncio
    async def test_list_idps(self, federation_manager):
        """Test listing IdPs."""
        # Create multiple IdPs
        await federation_manager.create_idp(
            name="IdP 1", description="Test", protocol=SSOProtocol.SAML2,
            entity_id="https://idp1.example.com"
        )
        await federation_manager.create_idp(
            name="IdP 2", description="Test", protocol=SSOProtocol.OIDC,
            entity_id="https://idp2.example.com"
        )
        
        all_idps = await federation_manager.list_idps()
        assert len(all_idps) >= 2
        
        # Filter by protocol
        saml_idps = await federation_manager.list_idps(protocol=SSOProtocol.SAML2)
        assert all(i.protocol == SSOProtocol.SAML2 for i in saml_idps)


class TestSPManagement:
    """Test service provider management."""
    
    @pytest.mark.asyncio
    async def test_create_sp(self, federation_manager, sample_sp_data):
        """Test creating an SP."""
        sp = await federation_manager.create_sp(
            name=sample_sp_data["name"],
            description=sample_sp_data["description"],
            entity_id=sample_sp_data["entity_id"],
            acs_url=sample_sp_data["acs_url"]
        )
        
        assert sp.sp_id is not None
        assert sp.name == sample_sp_data["name"]
        assert sp.acs_url == sample_sp_data["acs_url"]


class TestPartnershipManagement:
    """Test federation partnership management."""
    
    @pytest.mark.asyncio
    async def test_create_partnership(self, federation_manager, sample_idp_data, sample_sp_data):
        """Test creating a partnership."""
        idp = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        sp = await federation_manager.create_sp(
            name=sample_sp_data["name"],
            description=sample_sp_data["description"],
            entity_id=sample_sp_data["entity_id"],
            acs_url=sample_sp_data["acs_url"]
        )
        
        partnership = await federation_manager.create_partnership(
            idp_id=idp.idp_id,
            sp_id=sp.sp_id
        )
        
        assert partnership is not None
        assert partnership.idp_id == idp.idp_id
        assert partnership.sp_id == sp.sp_id
        assert partnership.status == FederationStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_activate_partnership(self, federation_manager, sample_idp_data, sample_sp_data):
        """Test activating a partnership."""
        idp = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        sp = await federation_manager.create_sp(
            name=sample_sp_data["name"],
            description=sample_sp_data["description"],
            entity_id=sample_sp_data["entity_id"],
            acs_url=sample_sp_data["acs_url"]
        )
        
        partnership = await federation_manager.create_partnership(
            idp_id=idp.idp_id,
            sp_id=sp.sp_id
        )
        
        success = await federation_manager.activate_partnership(partnership.partnership_id)
        assert success is True
        
        updated = await federation_manager.get_partnership(partnership.partnership_id)
        assert updated.status == FederationStatus.ACTIVE
        assert updated.activated_at is not None
    
    @pytest.mark.asyncio
    async def test_suspend_partnership(self, federation_manager, sample_idp_data, sample_sp_data):
        """Test suspending a partnership."""
        idp = await federation_manager.create_idp(
            name=sample_idp_data["name"],
            description=sample_idp_data["description"],
            protocol=sample_idp_data["protocol"],
            entity_id=sample_idp_data["entity_id"]
        )
        
        sp = await federation_manager.create_sp(
            name=sample_sp_data["name"],
            description=sample_sp_data["description"],
            entity_id=sample_sp_data["entity_id"],
            acs_url=sample_sp_data["acs_url"]
        )
        
        partnership = await federation_manager.create_partnership(
            idp_id=idp.idp_id,
            sp_id=sp.sp_id
        )
        
        await federation_manager.activate_partnership(partnership.partnership_id)
        
        success = await federation_manager.suspend_partnership(
            partnership.partnership_id,
            "Maintenance required"
        )
        
        assert success is True
        
        updated = await federation_manager.get_partnership(partnership.partnership_id)
        assert updated.status == FederationStatus.SUSPENDED


class TestSessionManagement:
    """Test session management through federation manager."""
    
    @pytest.mark.asyncio
    async def test_validate_and_access_session(self, federation_manager):
        """Test validating and accessing a session."""
        # Create session directly
        session = federation_manager.session_manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def"
        )
        
        # Validate for product access
        valid, accessed_session = await federation_manager.validate_session(
            session.session_id,
            product="product_x"
        )
        
        assert valid is True
        assert accessed_session is not None
        assert "product_x" in accessed_session.products_accessed
    
    @pytest.mark.asyncio
    async def test_terminate_session(self, federation_manager):
        """Test terminating a session."""
        session = federation_manager.session_manager.create_session(
            user_id="user_123",
            idp_id="idp_456",
            sp_id="sp_789",
            partnership_id="fp_abc",
            assertion_id="assert_def"
        )
        
        success = await federation_manager.terminate_session(session.session_id)
        assert success is True
        
        # Verify session is inactive
        assert session.is_active is False


class TestAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_log_event(self, federation_manager):
        """Test logging an event."""
        event = await federation_manager.log_event(
            event_type="authn_success",
            idp_id="idp_123",
            sp_id="sp_456",
            user_id="user_789",
            success=True,
            ip_address="192.168.1.1"
        )
        
        assert event.event_id is not None
        assert event.event_type == "authn_success"
        assert event.success is True
    
    @pytest.mark.asyncio
    async def test_get_events(self, federation_manager):
        """Test querying events."""
        await federation_manager.log_event(
            event_type="authn_success",
            user_id="user_test",
            success=True
        )
        await federation_manager.log_event(
            event_type="authn_failure",
            user_id="user_test",
            success=False
        )
        
        events = await federation_manager.get_events(user_id="user_test")
        assert len(events) == 2


class TestStatistics:
    """Test statistics generation."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, federation_manager):
        """Test getting federation statistics."""
        stats = await federation_manager.get_statistics()
        
        assert "identity_providers" in stats
        assert "service_providers" in stats
        assert "partnerships" in stats
        assert "sessions" in stats


class TestMetadataGeneration:
    """Test metadata generation."""
    
    @pytest.mark.asyncio
    async def test_generate_sp_metadata(self, federation_manager, sample_sp_data):
        """Test generating SP metadata."""
        sp = await federation_manager.create_sp(
            name=sample_sp_data["name"],
            description=sample_sp_data["description"],
            entity_id=sample_sp_data["entity_id"],
            acs_url=sample_sp_data["acs_url"],
            slo_url="https://sp.example.com/slo"
        )
        
        metadata = await federation_manager.generate_sp_metadata(sp.sp_id)
        assert metadata is not None
        assert sp.entity_id in metadata
        assert sp.acs_url in metadata


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
