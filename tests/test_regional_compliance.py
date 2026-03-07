"""
Comprehensive tests for Regional Compliance Profile Packs module.

Tests cover:
- Unit tests for compliance profiles, consent, RTD, exports
- Integration tests for full workflows
- Security and edge case tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend.fastapi.api.utils.regional_compliance import (
    RegionalComplianceManager,
    ComplianceRegion,
    ComplianceAction,
    DataCategory,
    ConsentStatus,
    ComplianceProfile,
    ComplianceRequirement,
    ConsentRecord,
    DataRetentionPolicy,
    RTDRequest,
    DataExportRequest,
    ComplianceAuditLog,
    ComplianceProfilePack,
    get_compliance_manager,
    reset_compliance_manager
)


# Fixtures

def get_manager_sync():
    """Get compliance manager synchronously."""
    reset_compliance_manager()
    return asyncio.run(get_compliance_manager())


@pytest.fixture
def compliance_manager():
    """Fixture for compliance manager."""
    manager = get_manager_sync()
    yield manager
    reset_compliance_manager()


@pytest.fixture
def sample_profile_data():
    """Sample profile data for testing."""
    return {
        "name": "Test GDPR Profile",
        "description": "Test profile for GDPR",
        "region": ComplianceRegion.EU,
        "jurisdiction": "European Union"
    }


# Unit Tests

class TestComplianceRegions:
    """Test compliance region enums."""
    
    def test_region_values(self):
        """Test that all regions have correct values."""
        assert ComplianceRegion.EU.value == "eu"
        assert ComplianceRegion.USA_CALIFORNIA.value == "usa_california"
        assert ComplianceRegion.BRAZIL.value == "brazil"
        assert ComplianceRegion.CANADA.value == "canada"
    
    def test_region_list(self):
        """Test that all expected regions exist."""
        regions = [r.value for r in ComplianceRegion]
        assert "eu" in regions
        assert "usa_california" in regions
        assert "brazil" in regions
        assert "global" in regions


class TestDataCategories:
    """Test data category enums."""
    
    def test_category_values(self):
        """Test that all categories have correct values."""
        assert DataCategory.IDENTIFIERS.value == "identifiers"
        assert DataCategory.HEALTH.value == "health"
        assert DataCategory.SENSITIVE.value == "sensitive"
    
    def test_all_categories(self):
        """Test that all expected categories exist."""
        categories = [c.value for c in DataCategory]
        assert "identifiers" in categories
        assert "biometric" in categories
        assert "financial" in categories
        assert "behavioral" in categories


class TestComplianceActions:
    """Test compliance action enums."""
    
    def test_action_values(self):
        """Test that all actions have correct values."""
        assert ComplianceAction.DATA_COLLECTION.value == "data_collection"
        assert ComplianceAction.DATA_DELETION.value == "data_deletion"
        assert ComplianceAction.ACCESS_REQUEST.value == "access_request"


class TestComplianceProfilePack:
    """Test predefined compliance packs."""
    
    def test_list_packs(self):
        """Test listing available packs."""
        packs = ComplianceProfilePack.list_packs()
        assert "gdpr" in packs
        assert "ccpa" in packs
        assert "lgpd" in packs
        assert "pipeda" in packs
    
    def test_get_gdpr_pack(self):
        """Test getting GDPR pack."""
        pack = ComplianceProfilePack.get_pack("gdpr")
        assert pack is not None
        assert pack["name"] == "GDPR (EU)"
        assert pack["region"] == ComplianceRegion.EU
        assert len(pack["requirements"]) > 0
    
    def test_get_ccpa_pack(self):
        """Test getting CCPA pack."""
        pack = ComplianceProfilePack.get_pack("ccpa")
        assert pack is not None
        assert pack["region"] == ComplianceRegion.USA_CALIFORNIA
    
    def test_get_nonexistent_pack(self):
        """Test getting non-existent pack returns None."""
        pack = ComplianceProfilePack.get_pack("nonexistent")
        assert pack is None


class TestComplianceManagerInitialization:
    """Test compliance manager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, compliance_manager):
        """Test that manager initializes correctly."""
        assert compliance_manager._initialized is True
        assert len(compliance_manager.profiles) > 0  # Default profiles loaded
    
    @pytest.mark.asyncio
    async def test_default_profiles_loaded(self, compliance_manager):
        """Test that default compliance profiles are loaded."""
        profiles = await compliance_manager.list_profiles()
        assert len(profiles) >= 4  # GDPR, CCPA, LGPD, PIPEDA
        
        regions = [p.region for p in profiles]
        assert ComplianceRegion.EU in regions
        assert ComplianceRegion.USA_CALIFORNIA in regions


class TestProfileManagement:
    """Test compliance profile CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_profile(self, compliance_manager, sample_profile_data):
        """Test creating a compliance profile."""
        profile = await compliance_manager.create_profile(
            name=sample_profile_data["name"],
            description=sample_profile_data["description"],
            region=sample_profile_data["region"],
            jurisdiction=sample_profile_data["jurisdiction"]
        )
        
        assert profile.profile_id is not None
        assert profile.name == sample_profile_data["name"]
        assert profile.region == sample_profile_data["region"]
        assert profile.active is True
    
    @pytest.mark.asyncio
    async def test_get_profile(self, compliance_manager, sample_profile_data):
        """Test retrieving a profile by ID."""
        created = await compliance_manager.create_profile(
            name=sample_profile_data["name"],
            description=sample_profile_data["description"],
            region=sample_profile_data["region"],
            jurisdiction=sample_profile_data["jurisdiction"]
        )
        
        retrieved = await compliance_manager.get_profile(created.profile_id)
        assert retrieved is not None
        assert retrieved.profile_id == created.profile_id
        assert retrieved.name == created.name
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_profile(self, compliance_manager):
        """Test retrieving non-existent profile returns None."""
        profile = await compliance_manager.get_profile("nonexistent_id")
        assert profile is None
    
    @pytest.mark.asyncio
    async def test_list_profiles(self, compliance_manager):
        """Test listing all profiles."""
        profiles = await compliance_manager.list_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) > 0
    
    @pytest.mark.asyncio
    async def test_list_active_profiles_only(self, compliance_manager):
        """Test listing only active profiles."""
        # Create an inactive profile
        profile = await compliance_manager.create_profile(
            name="Inactive Profile",
            description="Test",
            region=ComplianceRegion.GLOBAL,
            jurisdiction="Global"
        )
        await compliance_manager.deactivate_profile(profile.profile_id)
        
        active_profiles = await compliance_manager.list_profiles(active_only=True)
        inactive_profiles = [p for p in active_profiles if p.profile_id == profile.profile_id]
        assert len(inactive_profiles) == 0
    
    @pytest.mark.asyncio
    async def test_get_profiles_by_region(self, compliance_manager):
        """Test getting profiles filtered by region."""
        eu_profiles = await compliance_manager.get_profiles_by_region(ComplianceRegion.EU)
        assert len(eu_profiles) > 0
        
        for profile in eu_profiles:
            assert profile.region == ComplianceRegion.EU
    
    @pytest.mark.asyncio
    async def test_update_profile(self, compliance_manager, sample_profile_data):
        """Test updating a profile."""
        created = await compliance_manager.create_profile(
            name=sample_profile_data["name"],
            description=sample_profile_data["description"],
            region=sample_profile_data["region"],
            jurisdiction=sample_profile_data["jurisdiction"]
        )
        
        updated = await compliance_manager.update_profile(
            created.profile_id,
            {"name": "Updated Name", "description": "Updated Description"}
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated Description"
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_profile(self, compliance_manager):
        """Test updating non-existent profile returns None."""
        result = await compliance_manager.update_profile(
            "nonexistent_id",
            {"name": "New Name"}
        )
        assert result is None
    
    @pytest.mark.asyncio
    async def test_deactivate_profile(self, compliance_manager, sample_profile_data):
        """Test deactivating a profile."""
        created = await compliance_manager.create_profile(
            name=sample_profile_data["name"],
            description=sample_profile_data["description"],
            region=sample_profile_data["region"],
            jurisdiction=sample_profile_data["jurisdiction"]
        )
        
        success = await compliance_manager.deactivate_profile(created.profile_id)
        assert success is True
        
        profile = await compliance_manager.get_profile(created.profile_id)
        assert profile.active is False
    
    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_profile(self, compliance_manager):
        """Test deactivating non-existent profile returns False."""
        success = await compliance_manager.deactivate_profile("nonexistent_id")
        assert success is False


class TestConsentManagement:
    """Test consent management functionality."""
    
    @pytest.mark.asyncio
    async def test_record_consent(self, compliance_manager):
        """Test recording user consent."""
        consent = await compliance_manager.record_consent(
            user_id="user_123",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing", "analytics"],
            consent_mechanism="checkbox",
            ip_address="192.168.1.1"
        )
        
        assert consent.consent_id is not None
        assert consent.user_id == "user_123"
        assert consent.status == ConsentStatus.GRANTED
        assert consent.granted_at is not None
    
    @pytest.mark.asyncio
    async def test_record_consent_with_expiry(self, compliance_manager):
        """Test recording consent with expiration."""
        consent = await compliance_manager.record_consent(
            user_id="user_123",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"],
            expires_days=30
        )
        
        assert consent.expires_at is not None
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        assert abs((consent.expires_at - expected_expiry).total_seconds()) < 60
    
    @pytest.mark.asyncio
    async def test_withdraw_consent(self, compliance_manager):
        """Test withdrawing consent."""
        consent = await compliance_manager.record_consent(
            user_id="user_123",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"]
        )
        
        withdrawn = await compliance_manager.withdraw_consent(
            consent.consent_id,
            reason="User requested withdrawal"
        )
        
        assert withdrawn is not None
        assert withdrawn.status == ConsentStatus.WITHDRAWN
        assert withdrawn.withdrawn_at is not None
        assert withdrawn.metadata.get("withdrawal_reason") == "User requested withdrawal"
    
    @pytest.mark.asyncio
    async def test_withdraw_nonexistent_consent(self, compliance_manager):
        """Test withdrawing non-existent consent returns None."""
        result = await compliance_manager.withdraw_consent("nonexistent_id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_consents(self, compliance_manager):
        """Test getting all consents for a user."""
        # Record multiple consents
        await compliance_manager.record_consent(
            user_id="user_multi",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"]
        )
        await compliance_manager.record_consent(
            user_id="user_multi",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.BEHAVIORAL],
            purposes=["analytics"]
        )
        
        consents = await compliance_manager.get_user_consents("user_multi")
        assert len(consents) == 2
    
    @pytest.mark.asyncio
    async def test_get_user_consents_active_only(self, compliance_manager):
        """Test getting only active consents for a user."""
        import asyncio
        unique_user = f"user_active_test_{datetime.utcnow().timestamp()}"
        
        consent = await compliance_manager.record_consent(
            user_id=unique_user,
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"]
        )
        
        # Withdraw one consent
        await compliance_manager.withdraw_consent(consent.consent_id)
        
        # Small delay to ensure different timestamp
        await asyncio.sleep(0.01)
        
        # Record another consent
        await compliance_manager.record_consent(
            user_id=unique_user,
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.BEHAVIORAL],
            purposes=["analytics"]
        )
        
        active_consents = await compliance_manager.get_user_consents(unique_user, active_only=True)
        assert len(active_consents) == 1
        assert all(c.status == ConsentStatus.GRANTED for c in active_consents)
    
    @pytest.mark.asyncio
    async def test_check_consent_positive(self, compliance_manager):
        """Test checking consent when user has given consent."""
        await compliance_manager.record_consent(
            user_id="user_consent_check",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS, DataCategory.BEHAVIORAL],
            purposes=["marketing", "analytics"]
        )
        
        has_consent = await compliance_manager.check_consent(
            user_id="user_consent_check",
            data_categories=[DataCategory.IDENTIFIERS],
            purpose="marketing"
        )
        
        assert has_consent is True
    
    @pytest.mark.asyncio
    async def test_check_consent_negative(self, compliance_manager):
        """Test checking consent when user has not given consent."""
        has_consent = await compliance_manager.check_consent(
            user_id="user_no_consent",
            data_categories=[DataCategory.IDENTIFIERS],
            purpose="marketing"
        )
        
        assert has_consent is False
    
    @pytest.mark.asyncio
    async def test_check_consent_wrong_purpose(self, compliance_manager):
        """Test checking consent for wrong purpose."""
        await compliance_manager.record_consent(
            user_id="user_wrong_purpose",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"]
        )
        
        has_consent = await compliance_manager.check_consent(
            user_id="user_wrong_purpose",
            data_categories=[DataCategory.IDENTIFIERS],
            purpose="analytics"  # Different from recorded purpose
        )
        
        assert has_consent is False


class TestRTDRequests:
    """Test Right to Deletion request management."""
    
    @pytest.mark.asyncio
    async def test_create_rtd_request(self, compliance_manager):
        """Test creating an RTD request."""
        request = await compliance_manager.create_rtd_request(
            user_id="user_rtd",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            deletion_scope="all"
        )
        
        assert request.request_id is not None
        assert request.user_id == "user_rtd"
        assert request.status == "pending"
        assert request.completion_deadline is not None
    
    @pytest.mark.asyncio
    async def test_get_rtd_request(self, compliance_manager):
        """Test retrieving an RTD request."""
        created = await compliance_manager.create_rtd_request(
            user_id="user_rtd_get",
            region=ComplianceRegion.EU
        )
        
        retrieved = await compliance_manager.get_rtd_request(created.request_id)
        assert retrieved is not None
        assert retrieved.request_id == created.request_id
    
    @pytest.mark.asyncio
    async def test_update_rtd_status(self, compliance_manager):
        """Test updating RTD request status."""
        created = await compliance_manager.create_rtd_request(
            user_id="user_rtd_update",
            region=ComplianceRegion.EU
        )
        
        updated = await compliance_manager.update_rtd_status(
            created.request_id,
            "in_progress",
            "Processing started"
        )
        
        assert updated is not None
        assert updated.status == "in_progress"
        assert len(updated.audit_trail) > 1
    
    @pytest.mark.asyncio
    async def test_update_rtd_to_completed(self, compliance_manager):
        """Test completing an RTD request."""
        created = await compliance_manager.create_rtd_request(
            user_id="user_rtd_complete",
            region=ComplianceRegion.EU
        )
        
        updated = await compliance_manager.update_rtd_status(
            created.request_id,
            "completed",
            "Deletion completed"
        )
        
        assert updated.status == "completed"
        assert updated.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_rtd(self, compliance_manager):
        """Test updating non-existent RTD request returns None."""
        result = await compliance_manager.update_rtd_status("nonexistent_id", "completed")
        assert result is None


class TestExportRequests:
    """Test data export request management."""
    
    @pytest.mark.asyncio
    async def test_create_export_request(self, compliance_manager):
        """Test creating a data export request."""
        request = await compliance_manager.create_export_request(
            user_id="user_export",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            format="json"
        )
        
        assert request.request_id is not None
        assert request.user_id == "user_export"
        assert request.status == "pending"
        assert request.format == "json"
        assert request.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_complete_export_request(self, compliance_manager):
        """Test completing an export request."""
        created = await compliance_manager.create_export_request(
            user_id="user_export_complete",
            region=ComplianceRegion.EU
        )
        
        completed = await compliance_manager.complete_export_request(
            created.request_id,
            download_url="https://example.com/export.zip",
            file_size_bytes=1024,
            checksum="abc123"
        )
        
        assert completed is not None
        assert completed.status == "ready"
        assert completed.download_url == "https://example.com/export.zip"
        assert completed.file_size_bytes == 1024
        assert completed.checksum == "abc123"
        assert completed.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_complete_nonexistent_export(self, compliance_manager):
        """Test completing non-existent export request returns None."""
        result = await compliance_manager.complete_export_request(
            "nonexistent_id",
            "https://example.com/export.zip",
            1024,
            "abc123"
        )
        assert result is None


class TestComplianceAuditing:
    """Test compliance audit logging."""
    
    @pytest.mark.asyncio
    async def test_log_compliance_action(self, compliance_manager):
        """Test logging a compliance action."""
        log = await compliance_manager.log_compliance_action(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_COLLECTION,
            user_id="user_audit",
            data_subject_id="subject_123",
            data_categories=[DataCategory.IDENTIFIERS],
            legal_basis="consent",
            processing_purpose="marketing",
            risk_level="medium"
        )
        
        assert log.log_id is not None
        assert log.region == ComplianceRegion.EU
        assert log.action == ComplianceAction.DATA_COLLECTION
        assert log.checksum is not None
    
    @pytest.mark.asyncio
    async def test_get_audit_logs(self, compliance_manager):
        """Test retrieving audit logs."""
        # Create some logs
        await compliance_manager.log_compliance_action(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_COLLECTION,
            user_id="user_logs"
        )
        await compliance_manager.log_compliance_action(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_PROCESSING,
            user_id="user_logs"
        )
        
        logs = await compliance_manager.get_audit_logs(user_id="user_logs")
        assert len(logs) == 2
    
    @pytest.mark.asyncio
    async def test_get_audit_logs_with_filters(self, compliance_manager):
        """Test retrieving filtered audit logs."""
        await compliance_manager.log_compliance_action(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_COLLECTION
        )
        await compliance_manager.log_compliance_action(
            region=ComplianceRegion.USA,
            action=ComplianceAction.DATA_COLLECTION
        )
        
        eu_logs = await compliance_manager.get_audit_logs(region=ComplianceRegion.EU)
        assert all(log.region == ComplianceRegion.EU for log in eu_logs)


class TestComplianceValidation:
    """Test compliance validation functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_processing_compliant(self, compliance_manager):
        """Test validating a compliant processing action."""
        result = await compliance_manager.validate_processing(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_COLLECTION,
            data_categories=[DataCategory.IDENTIFIERS]
        )
        
        assert result["compliant"] is True
        assert len(result["violations"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_processing_missing_consent(self, compliance_manager):
        """Test validating processing that requires consent."""
        # Note: In EU, sensitive data processing requires consent
        result = await compliance_manager.validate_processing(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_PROCESSING,
            data_categories=[DataCategory.SENSITIVE],
            user_id="user_no_consent_yet",
            purpose="marketing"
        )
        
        # This should detect missing consent
        assert result["compliant"] is False
        assert len(result["violations"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_data_residency(self, compliance_manager):
        """Test validating data residency."""
        # EU data should be in EU zones
        is_valid = await compliance_manager.validate_data_residency(
            region=ComplianceRegion.EU,
            current_zone="eu-west-1"
        )
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_get_allowed_residency_zones(self, compliance_manager):
        """Test getting allowed residency zones for a region."""
        zones = await compliance_manager.get_allowed_residency_zones(ComplianceRegion.EU)
        assert len(zones) > 0
        assert "eu-west-1" in zones or "global" in zones


class TestStatistics:
    """Test statistics generation."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, compliance_manager):
        """Test getting compliance statistics."""
        stats = await compliance_manager.get_statistics()
        
        assert "profiles" in stats
        assert "consents" in stats
        assert "rtd_requests" in stats
        assert "export_requests" in stats
        assert "audit_logs" in stats
        
        assert "total" in stats["profiles"]
        assert "active" in stats["profiles"]


class TestDataResidencyZones:
    """Test data residency zone functionality."""
    
    @pytest.mark.asyncio
    async def test_eu_residency_zones(self, compliance_manager):
        """Test EU residency zones."""
        zones = compliance_manager._get_residency_zones(ComplianceRegion.EU)
        assert "eu-west-1" in zones
        assert "eu-central-1" in zones
    
    @pytest.mark.asyncio
    async def test_usa_residency_zones(self, compliance_manager):
        """Test USA residency zones."""
        zones = compliance_manager._get_residency_zones(ComplianceRegion.USA)
        assert "us-east-1" in zones
        assert "us-west-1" in zones


# Integration Tests

class TestIntegrationWorkflows:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_consent_workflow(self, compliance_manager):
        """Test complete consent workflow from recording to withdrawal."""
        # Record consent
        consent = await compliance_manager.record_consent(
            user_id="user_integration",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"]
        )
        
        # Verify consent exists
        assert await compliance_manager.get_consent(consent.consent_id) is not None
        
        # Check consent
        has_consent = await compliance_manager.check_consent(
            user_id="user_integration",
            data_categories=[DataCategory.IDENTIFIERS],
            purpose="marketing"
        )
        assert has_consent is True
        
        # Withdraw consent
        await compliance_manager.withdraw_consent(consent.consent_id)
        
        # Verify consent withdrawn
        has_consent = await compliance_manager.check_consent(
            user_id="user_integration",
            data_categories=[DataCategory.IDENTIFIERS],
            purpose="marketing"
        )
        assert has_consent is False
    
    @pytest.mark.asyncio
    async def test_full_rtd_workflow(self, compliance_manager):
        """Test complete RTD workflow from creation to completion."""
        # Create RTD request
        request = await compliance_manager.create_rtd_request(
            user_id="user_rtd_integration",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            deletion_scope="all"
        )
        
        # Verify pending
        assert request.status == "pending"
        
        # Update to in_progress
        await compliance_manager.update_rtd_status(request.request_id, "in_progress")
        
        # Verify in_progress
        updated = await compliance_manager.get_rtd_request(request.request_id)
        assert updated.status == "in_progress"
        
        # Complete
        await compliance_manager.update_rtd_status(request.request_id, "completed")
        
        # Verify completed
        completed = await compliance_manager.get_rtd_request(request.request_id)
        assert completed.status == "completed"
        assert completed.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_full_export_workflow(self, compliance_manager):
        """Test complete export workflow."""
        # Create export request
        request = await compliance_manager.create_export_request(
            user_id="user_export_integration",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            format="json"
        )
        
        # Verify pending
        assert request.status == "pending"
        
        # Complete export
        await compliance_manager.complete_export_request(
            request.request_id,
            download_url="https://example.com/export.zip",
            file_size_bytes=2048,
            checksum="def456"
        )
        
        # Verify completed
        completed = await compliance_manager.get_export_request(request.request_id)
        assert completed.status == "ready"
        assert completed.download_url is not None


# Edge Case Tests

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_consent_updates(self, compliance_manager):
        """Test handling concurrent consent updates."""
        consent = await compliance_manager.record_consent(
            user_id="user_concurrent",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"]
        )
        
        # Simulate concurrent withdrawal attempts
        tasks = [
            compliance_manager.withdraw_consent(consent.consent_id, f"reason_{i}")
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least one should succeed
        successful = [r for r in results if r is not None and not isinstance(r, Exception)]
        assert len(successful) >= 1
    
    @pytest.mark.asyncio
    async def test_expired_consent_detection(self, compliance_manager):
        """Test detection of expired consent."""
        # Create consent that expires immediately
        consent = await compliance_manager.record_consent(
            user_id="user_expired",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"],
            expires_days=-1  # Already expired
        )
        
        # Manually set expiry to past
        consent.expires_at = datetime.utcnow() - timedelta(days=1)
        
        # Check consent should fail (expired)
        has_consent = await compliance_manager.check_consent(
            user_id="user_expired",
            data_categories=[DataCategory.IDENTIFIERS],
            purpose="marketing"
        )
        assert has_consent is False
    
    @pytest.mark.asyncio
    async def test_empty_data_categories(self, compliance_manager):
        """Test handling empty data categories."""
        request = await compliance_manager.create_rtd_request(
            user_id="user_empty",
            region=ComplianceRegion.EU,
            data_categories=[],  # Empty
            deletion_scope="all"
        )
        
        assert request is not None
        assert len(request.data_categories) == 0
    
    @pytest.mark.asyncio
    async def test_very_long_purpose_string(self, compliance_manager):
        """Test handling very long purpose string."""
        long_purpose = "a" * 1000
        
        consent = await compliance_manager.record_consent(
            user_id="user_long_purpose",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=[long_purpose]
        )
        
        assert consent is not None
        assert long_purpose in consent.purposes


# Performance Tests

class TestPerformance:
    """Performance-related tests."""
    
    @pytest.mark.asyncio
    async def test_bulk_consent_creation(self, compliance_manager):
        """Test creating many consent records."""
        start_time = datetime.utcnow()
        
        for i in range(100):
            await compliance_manager.record_consent(
                user_id=f"user_bulk_{i}",
                region=ComplianceRegion.EU,
                data_categories=[DataCategory.IDENTIFIERS],
                purposes=["marketing"]
            )
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete in reasonable time
        assert duration < 10  # Less than 10 seconds for 100 records
        assert len(compliance_manager.consent_records) >= 100
    
    @pytest.mark.asyncio
    async def test_audit_log_query_performance(self, compliance_manager):
        """Test audit log query performance with many logs."""
        # Create many audit logs
        for i in range(1000):
            await compliance_manager.log_compliance_action(
                region=ComplianceRegion.EU,
                action=ComplianceAction.DATA_COLLECTION,
                user_id=f"user_{i % 100}"
            )
        
        # Query should still be fast
        start_time = datetime.utcnow()
        logs = await compliance_manager.get_audit_logs(limit=100)
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        assert duration < 1  # Less than 1 second
        assert len(logs) == 100


# Security Tests

class TestSecurity:
    """Security-related tests."""
    
    @pytest.mark.asyncio
    async def test_audit_log_checksums(self, compliance_manager):
        """Test that audit logs have valid checksums."""
        log = await compliance_manager.log_compliance_action(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_COLLECTION,
            user_id="user_checksum"
        )
        
        assert log.checksum is not None
        assert len(log.checksum) == 64  # SHA256 hex length
    
    @pytest.mark.asyncio
    async def test_consent_ip_logging(self, compliance_manager):
        """Test that consent records can store IP address."""
        consent = await compliance_manager.record_consent(
            user_id="user_ip",
            region=ComplianceRegion.EU,
            data_categories=[DataCategory.IDENTIFIERS],
            purposes=["marketing"],
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0"
        )
        
        assert consent.ip_address == "192.168.1.100"
        assert consent.user_agent == "Mozilla/5.0"
    
    @pytest.mark.asyncio
    async def test_sensitive_data_handling(self, compliance_manager):
        """Test handling of sensitive data categories."""
        # Processing sensitive data should require explicit consent
        result = await compliance_manager.validate_processing(
            region=ComplianceRegion.EU,
            action=ComplianceAction.DATA_PROCESSING,
            data_categories=[DataCategory.SENSITIVE],
            user_id="user_sensitive"
        )
        
        assert result["compliant"] is False  # No consent given
        assert len(result["recommendations"]) > 0


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
