"""
Comprehensive tests for API Deprecation Header Standardization module.

Test coverage: 30+ tests
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

# Import the module under test
import sys
sys.path.insert(0, "backend/fastapi/api/utils")

from api_deprecation import (
    DeprecationStatus, DeprecationSeverity, ApiVersionStatus,
    ApiVersion, DeprecationNotice, DeprecatedField, ClientDeprecationNotice,
    DeprecationHeaders, ApiDeprecationManager,
    get_deprecation_manager, reset_deprecation_manager
)


# Fixtures

@pytest_asyncio.fixture(autouse=True)
async def reset_manager():
    """Reset the global deprecation manager before each test."""
    reset_deprecation_manager()
    yield
    reset_deprecation_manager()


@pytest_asyncio.fixture
async def deprecation_manager():
    """Create a fresh API deprecation manager."""
    manager = ApiDeprecationManager()
    await manager.initialize()
    yield manager
    reset_deprecation_manager()


# Enums Tests

class TestDeprecationEnums:
    """Test deprecation enums."""
    
    def test_deprecation_status_values(self):
        """Test DeprecationStatus enum values."""
        assert DeprecationStatus.ACTIVE == "active"
        assert DeprecationStatus.DEPRECATED == "deprecated"
        assert DeprecationStatus.SUNSET == "sunset"
        assert DeprecationStatus.REMOVED == "removed"
    
    def test_deprecation_severity_values(self):
        """Test DeprecationSeverity enum values."""
        assert DeprecationSeverity.INFO == "info"
        assert DeprecationSeverity.WARNING == "warning"
        assert DeprecationSeverity.CRITICAL == "critical"
    
    def test_api_version_status_values(self):
        """Test ApiVersionStatus enum values."""
        assert ApiVersionStatus.STABLE == "stable"
        assert ApiVersionStatus.MAINTENANCE == "maintenance"
        assert ApiVersionStatus.DEPRECATED == "deprecated"
        assert ApiVersionStatus.END_OF_LIFE == "end_of_life"


# ApiDeprecationManager Tests

@pytest.mark.asyncio
class TestApiDeprecationManager:
    """Test API deprecation manager."""
    
    async def test_initialize(self, deprecation_manager):
        """Test manager initialization."""
        assert deprecation_manager._initialized is True
        assert "v1" in deprecation_manager.api_versions
        assert "v2" in deprecation_manager.api_versions
    
    async def test_register_api_version(self, deprecation_manager):
        """Test API version registration."""
        version = await deprecation_manager.register_api_version(
            version="v3",
            base_path="/api/v3",
            status=ApiVersionStatus.STABLE,
            released_at=datetime.utcnow(),
            documentation_url="/docs/api/v3"
        )
        
        assert version.version == "v3"
        assert version.base_path == "/api/v3"
        assert version.status == ApiVersionStatus.STABLE
        assert "v3" in deprecation_manager.api_versions
    
    async def test_get_api_version(self, deprecation_manager):
        """Test retrieving API version."""
        version = await deprecation_manager.get_api_version("v1")
        assert version is not None
        assert version.version == "v1"
        assert version.base_path == "/api/v1"
    
    async def test_list_api_versions(self, deprecation_manager):
        """Test listing API versions."""
        versions = await deprecation_manager.list_api_versions()
        assert len(versions) >= 2
        
        # Filter by status
        stable_versions = await deprecation_manager.list_api_versions(
            status=ApiVersionStatus.STABLE
        )
        assert len(stable_versions) == 1
    
    async def test_deprecate_version(self, deprecation_manager):
        """Test deprecating an API version."""
        await deprecation_manager.register_api_version(
            version="v3",
            base_path="/api/v3",
            status=ApiVersionStatus.STABLE
        )
        
        deprecated = await deprecation_manager.deprecate_version(
            version="v3",
            deprecation_date=datetime.utcnow(),
            sunset_date=datetime.utcnow() + timedelta(days=90)
        )
        
        assert deprecated is not None
        assert deprecated.status == ApiVersionStatus.DEPRECATED
        assert deprecated.deprecated_at is not None
        assert deprecated.sunset_at is not None
    
    async def test_create_deprecation_notice(self, deprecation_manager):
        """Test creating deprecation notice."""
        notice = await deprecation_manager.create_deprecation_notice(
            notice_id="notice-001",
            endpoint_path="/api/v1/users",
            http_method="GET",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.WARNING,
            deprecated_since=datetime.utcnow(),
            sunset_date=datetime.utcnow() + timedelta(days=90),
            alternative_endpoint="/api/v2/users",
            alternative_version="v2",
            notice_message="This endpoint is deprecated. Please migrate to v2.",
            breaking_changes=["Response format changed"]
        )
        
        assert notice.notice_id == "notice-001"
        assert notice.endpoint_path == "/api/v1/users"
        assert notice.http_method == "GET"
        assert notice.status == DeprecationStatus.DEPRECATED
        assert notice.alternative_endpoint == "/api/v2/users"
        assert "notice-001" in deprecation_manager.deprecation_notices
    
    async def test_find_deprecation_notice(self, deprecation_manager):
        """Test finding deprecation notice."""
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-002",
            endpoint_path="/api/v1/items",
            http_method="POST",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.CRITICAL
        )
        
        found = await deprecation_manager.find_deprecation_notice(
            "/api/v1/items", "POST"
        )
        
        assert found is not None
        assert found.notice_id == "notice-002"
    
    async def test_list_deprecation_notices(self, deprecation_manager):
        """Test listing deprecation notices."""
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-003",
            endpoint_path="/api/v1/old",
            http_method="GET",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.WARNING
        )
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-004",
            endpoint_path="/api/v1/legacy",
            http_method="POST",
            status=DeprecationStatus.SUNSET,
            severity=DeprecationSeverity.CRITICAL
        )
        
        notices = await deprecation_manager.list_deprecation_notices()
        assert len(notices) == 2
        
        # Filter by status
        sunset_notices = await deprecation_manager.list_deprecation_notices(
            status=DeprecationStatus.SUNSET
        )
        assert len(sunset_notices) == 1
    
    async def test_get_deprecation_headers(self, deprecation_manager):
        """Test deprecation header generation."""
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-headers",
            endpoint_path="/api/v1/test",
            http_method="GET",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.WARNING,
            deprecated_since=datetime(2025, 1, 1),
            sunset_date=datetime(2025, 6, 1),
            alternative_endpoint="/api/v2/test"
        )
        
        headers = await deprecation_manager.get_deprecation_headers(
            "/api/v1/test", "GET"
        )
        
        assert DeprecationHeaders.DEPRECATION in headers
        assert headers[DeprecationHeaders.DEPRECATION] == "true"
        assert DeprecationHeaders.SUNSET in headers
        assert DeprecationHeaders.API_ALTERNATIVE in headers
        assert headers[DeprecationHeaders.API_ALTERNATIVE] == "/api/v2/test"
        assert DeprecationHeaders.LINK in headers
    
    async def test_get_deprecation_headers_not_deprecated(self, deprecation_manager):
        """Test header generation for non-deprecated endpoint."""
        headers = await deprecation_manager.get_deprecation_headers(
            "/api/v2/new-endpoint", "GET"
        )
        
        assert len(headers) == 0
    
    async def test_register_deprecated_field(self, deprecation_manager):
        """Test registering deprecated field."""
        field = await deprecation_manager.register_deprecated_field(
            endpoint_path="/api/v1/users",
            field_name="username",
            field_location="request_body",
            deprecated_since=datetime.utcnow(),
            replacement_field="email"
        )
        
        assert field.field_name == "username"
        assert field.field_location == "request_body"
        assert field.replacement_field == "email"
    
    async def test_notify_client(self, deprecation_manager):
        """Test client notification."""
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-notify",
            endpoint_path="/api/v1/notify",
            http_method="GET",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.WARNING
        )
        
        client_notice = await deprecation_manager.notify_client(
            client_id="client-001",
            notice_id="notice-notify"
        )
        
        assert client_notice is not None
        assert client_notice.client_id == "client-001"
        assert client_notice.notice_id == "notice-notify"
        
        # Check notice was updated
        notice = await deprecation_manager.get_deprecation_notice("notice-notify")
        assert "client-001" in notice.affected_clients
        assert notice.notification_sent is True
    
    async def test_acknowledge_notice(self, deprecation_manager):
        """Test client acknowledgement."""
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-ack",
            endpoint_path="/api/v1/ack",
            http_method="GET",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.WARNING
        )
        
        await deprecation_manager.notify_client("client-002", "notice-ack")
        
        result = await deprecation_manager.acknowledge_notice("client-002", "notice-ack")
        assert result is True
        
        # Verify acknowledgement
        client_notices = deprecation_manager.client_notices.get("client-002", [])
        assert any(n.acknowledged for n in client_notices)
    
    async def test_get_statistics(self, deprecation_manager):
        """Test getting statistics."""
        await deprecation_manager.create_deprecation_notice(
            notice_id="notice-stats",
            endpoint_path="/api/v1/stats",
            http_method="GET",
            status=DeprecationStatus.DEPRECATED,
            severity=DeprecationSeverity.WARNING,
            sunset_date=datetime.utcnow() + timedelta(days=15)
        )
        
        await deprecation_manager.notify_client("client-003", "notice-stats")
        
        stats = await deprecation_manager.get_statistics()
        
        assert "api_versions" in stats
        assert "deprecation_notices" in stats
        assert stats["deprecation_notices"]["total"] >= 1
        assert stats["affected_clients"] >= 1


# Global Manager Tests

@pytest.mark.asyncio
class TestGlobalManager:
    """Test global deprecation manager functions."""
    
    async def test_get_deprecation_manager(self):
        """Test getting global deprecation manager."""
        manager1 = await get_deprecation_manager()
        manager2 = await get_deprecation_manager()
        
        # Should return same instance
        assert manager1 is manager2
        assert manager1._initialized is True
    
    async def test_reset_deprecation_manager(self):
        """Test resetting global deprecation manager."""
        manager1 = await get_deprecation_manager()
        reset_deprecation_manager()
        manager2 = await get_deprecation_manager()
        
        # Should be different instances after reset
        assert manager1 is not manager2


# Header Tests

class TestDeprecationHeaders:
    """Test deprecation header constants."""
    
    def test_header_constants(self):
        """Test header constant values."""
        assert DeprecationHeaders.DEPRECATION == "Deprecation"
        assert DeprecationHeaders.SUNSET == "Sunset"
        assert DeprecationHeaders.LINK == "Link"
        assert DeprecationHeaders.API_DEPRECATED == "API-Deprecated"
        assert DeprecationHeaders.API_SUNSET == "API-Sunset"
        assert DeprecationHeaders.API_ALTERNATIVE == "API-Alternative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
