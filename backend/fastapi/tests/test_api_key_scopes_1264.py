# test_api_key_scopes_1264.py
"""
Comprehensive tests for Fine-Grained API Key Scopes (#1264)

Tests cover:
- API key creation and validation
- Scope enforcement in middleware
- Route-level access control
- Migration and backward compatibility
- Security edge cases
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from unittest.mock import Mock, AsyncMock
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.api_key_service import ApiKeyService
from ..middleware.api_key_middleware import api_key_middleware, _get_required_scopes
from ..models import ApiKey, ApiKeyScope, User
from ..utils.timestamps import utc_now


class TestApiKeyService:
    """Test the API key service functionality."""

    @pytest.fixture
    async def api_key_service(self, db_session: AsyncSession):
        return ApiKeyService(db_session)

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user."""
        user = User(
            username="test_user",
            email="test@example.com",
            password_hash="hashed_password"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_create_api_key(self, api_key_service: ApiKeyService, test_user: User):
        """Test creating an API key with scopes."""
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Test Key",
            scopes=["read", "users:read"],
            expires_at=None
        )

        assert plain_key is not None
        assert len(plain_key) > 32  # Should be a long secure key
        assert key_record.user_id == test_user.id
        assert key_record.name == "Test Key"
        assert key_record.scopes == ["read", "users:read"]
        assert key_record.is_active is True
        assert key_record.expires_at is None

    @pytest.mark.asyncio
    async def test_verify_valid_api_key(self, api_key_service: ApiKeyService, test_user: User):
        """Test verifying a valid API key."""
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Test Key",
            scopes=["read"]
        )

        verified_key = await api_key_service.verify_api_key(plain_key)
        assert verified_key is not None
        assert verified_key.id == key_record.id
        assert verified_key.last_used_at is not None

    @pytest.mark.asyncio
    async def test_verify_invalid_api_key(self, api_key_service: ApiKeyService):
        """Test verifying an invalid API key."""
        verified_key = await api_key_service.verify_api_key("invalid_key")
        assert verified_key is None

    @pytest.mark.asyncio
    async def test_verify_expired_api_key(self, api_key_service: ApiKeyService, test_user: User):
        """Test verifying an expired API key."""
        expired_time = datetime.now(UTC) - timedelta(days=1)
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Expired Key",
            scopes=["read"],
            expires_at=expired_time
        )

        verified_key = await api_key_service.verify_api_key(plain_key)
        assert verified_key is None

    @pytest.mark.asyncio
    async def test_validate_scopes_success(self, api_key_service: ApiKeyService, test_user: User):
        """Test validating scopes with sufficient permissions."""
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Test Key",
            scopes=["read", "write", "users:read"]
        )

        has_scopes = await api_key_service.validate_scopes(key_record, ["read", "users:read"])
        assert has_scopes is True

    @pytest.mark.asyncio
    async def test_validate_scopes_insufficient(self, api_key_service: ApiKeyService, test_user: User):
        """Test validating scopes with insufficient permissions."""
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Test Key",
            scopes=["read"]
        )

        has_scopes = await api_key_service.validate_scopes(key_record, ["write"])
        assert has_scopes is False

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, api_key_service: ApiKeyService, test_user: User):
        """Test revoking an API key."""
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Test Key",
            scopes=["read"]
        )

        # Verify key is active
        verified_key = await api_key_service.verify_api_key(plain_key)
        assert verified_key is not None

        # Revoke the key
        success = await api_key_service.revoke_api_key(key_record.id, test_user.id)
        assert success is True

        # Verify key is no longer valid
        verified_key = await api_key_service.verify_api_key(plain_key)
        assert verified_key is None

    @pytest.mark.asyncio
    async def test_update_api_key_scopes(self, api_key_service: ApiKeyService, test_user: User):
        """Test updating API key scopes."""
        plain_key, key_record = await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Test Key",
            scopes=["read"]
        )

        # Update scopes
        success = await api_key_service.update_api_key_scopes(
            key_record.id,
            test_user.id,
            ["read", "write", "users:read"]
        )
        assert success is True

        # Verify scopes were updated
        keys = await api_key_service.get_user_api_keys(test_user.id)
        updated_key = next(k for k in keys if k.id == key_record.id)
        assert updated_key.scopes == ["read", "write", "users:read"]

    @pytest.mark.asyncio
    async def test_get_user_api_keys(self, api_key_service: ApiKeyService, test_user: User):
        """Test getting all API keys for a user."""
        # Create multiple keys
        await api_key_service.create_api_key(test_user.id, "Key 1", ["read"])
        await api_key_service.create_api_key(test_user.id, "Key 2", ["write"])
        await api_key_service.create_api_key(test_user.id, "Key 3", ["admin"])

        keys = await api_key_service.get_user_api_keys(test_user.id)
        assert len(keys) == 3
        assert all(key.user_id == test_user.id for key in keys)
        assert all(key.is_active for key in keys)


class TestApiKeyMiddleware:
    """Test the API key middleware functionality."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/users"
        request.method = "GET"
        request.headers = {}
        request.state = Mock()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create a mock call_next function."""
        return AsyncMock(return_value=Mock(status_code=200))

    def test_get_required_scopes_read_endpoint(self):
        """Test getting required scopes for a read endpoint."""
        scopes = _get_required_scopes("/api/v1/users", "GET")
        assert scopes == ["users:read"]

    def test_get_required_scopes_write_endpoint(self):
        """Test getting required scopes for a write endpoint."""
        scopes = _get_required_scopes("/api/v1/users", "POST")
        assert scopes == ["users:write"]

    def test_get_required_scopes_admin_endpoint(self):
        """Test getting required scopes for an admin endpoint."""
        scopes = _get_required_scopes("/api/v1/admin/users", "DELETE")
        assert scopes == ["admin"]

    def test_get_required_scopes_exempt_path(self):
        """Test that exempt paths don't require scopes."""
        from ..middleware.api_key_middleware import _EXEMPT_PATHS

        for path in _EXEMPT_PATHS:
            scopes = _get_required_scopes(path, "GET")
            assert scopes == []

    @pytest.mark.asyncio
    async def test_middleware_no_api_key_header(self, mock_request, mock_call_next):
        """Test middleware rejects requests without API key header."""
        mock_request.headers = {}  # No API key header

        with pytest.raises(HTTPException) as exc_info:
            await api_key_middleware(mock_request, mock_call_next)

        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_middleware_exempt_path(self, mock_request, mock_call_next):
        """Test middleware allows exempt paths without API key."""
        mock_request.url.path = "/health"

        response = await api_key_middleware(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once()


class TestApiKeyRoutes:
    """Test the API key management routes."""

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Create authorization headers."""
        return {"Authorization": f"Bearer {test_user_token}"}

    def test_create_api_key_success(self, client, auth_headers):
        """Test creating an API key successfully."""
        response = client.post(
            "/api/v1/api-keys",
            json={
                "name": "Test API Key",
                "scopes": ["read", "users:read"],
                "expires_in_days": 30
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "key_info" in data
        assert data["key_info"]["name"] == "Test API Key"
        assert data["key_info"]["scopes"] == ["read", "users:read"]

    def test_create_api_key_invalid_scopes(self, client, auth_headers):
        """Test creating an API key with invalid scopes."""
        response = client.post(
            "/api/v1/api-keys",
            json={
                "name": "Test API Key",
                "scopes": ["invalid_scope"]
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "Invalid scopes" in response.json()["detail"]

    def test_list_api_keys(self, client, auth_headers):
        """Test listing API keys."""
        # First create a key
        create_response = client.post(
            "/api/v1/api-keys",
            json={"name": "List Test Key", "scopes": ["read"]},
            headers=auth_headers
        )
        assert create_response.status_code == 200

        # Now list keys
        response = client.get("/api/v1/api-keys", headers=auth_headers)
        assert response.status_code == 200
        keys = response.json()
        assert isinstance(keys, list)
        assert len(keys) >= 1

        # Check the created key is in the list
        key_names = [key["name"] for key in keys]
        assert "List Test Key" in key_names

    def test_revoke_api_key(self, client, auth_headers):
        """Test revoking an API key."""
        # Create a key
        create_response = client.post(
            "/api/v1/api-keys",
            json={"name": "Revoke Test Key", "scopes": ["read"]},
            headers=auth_headers
        )
        key_id = create_response.json()["key_info"]["id"]

        # Revoke the key
        response = client.delete(f"/api/v1/api-keys/{key_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify key is revoked by trying to list again
        list_response = client.get("/api/v1/api-keys", headers=auth_headers)
        keys = list_response.json()
        revoked_key = next((k for k in keys if k["id"] == key_id), None)
        assert revoked_key["is_active"] is False

    def test_update_api_key_scopes(self, client, auth_headers):
        """Test updating API key scopes."""
        # Create a key
        create_response = client.post(
            "/api/v1/api-keys",
            json={"name": "Update Test Key", "scopes": ["read"]},
            headers=auth_headers
        )
        key_id = create_response.json()["key_info"]["id"]

        # Update scopes
        response = client.put(
            f"/api/v1/api-keys/{key_id}/scopes",
            json={"scopes": ["read", "write", "users:read"]},
            headers=auth_headers
        )
        assert response.status_code == 200

        updated_key = response.json()
        assert updated_key["scopes"] == ["read", "write", "users:read"]

    def test_list_available_scopes(self, client):
        """Test listing available scopes."""
        response = client.get("/api/v1/api-keys/scopes")
        assert response.status_code == 200

        data = response.json()
        assert "available_scopes" in data
        assert "grouped_scopes" in data
        assert "descriptions" in data

        # Check that our defined scopes are present
        scopes = data["available_scopes"]
        assert "read" in scopes
        assert "write" in scopes
        assert "admin" in scopes
        assert "users:read" in scopes


class TestScopeEnforcement:
    """Test scope enforcement in protected endpoints."""

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def create_api_key_with_scopes(self, client, auth_headers, scopes):
        """Helper to create an API key with specific scopes."""
        response = client.post(
            "/api/v1/api-keys",
            json={"name": f"Test Key {scopes}", "scopes": scopes},
            headers=auth_headers
        )
        return response.json()["api_key"]

    def test_read_scope_can_access_read_endpoint(self, client, auth_headers):
        """Test that read scope can access read endpoints."""
        api_key = self.create_api_key_with_scopes(client, auth_headers, ["read"])

        # Try to access a read endpoint
        response = client.get(
            "/api/v1/users/profile",
            headers={"X-API-Key": api_key}
        )
        # This should succeed (assuming the endpoint exists and is properly configured)
        assert response.status_code in [200, 404]  # 404 is OK if endpoint doesn't exist

    def test_read_scope_denied_write_endpoint(self, client, auth_headers):
        """Test that read scope is denied access to write endpoints."""
        api_key = self.create_api_key_with_scopes(client, auth_headers, ["read"])

        # Try to access a write endpoint
        response = client.post(
            "/api/v1/users",
            json={"username": "test", "password": "test"},
            headers={"X-API-Key": api_key}
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    def test_write_scope_can_access_write_endpoint(self, client, auth_headers):
        """Test that write scope can access write endpoints."""
        api_key = self.create_api_key_with_scopes(client, auth_headers, ["write"])

        # Try to access a write endpoint
        response = client.post(
            "/api/v1/users",
            json={"username": "test", "password": "test"},
            headers={"X-API-Key": api_key}
        )
        # This should succeed (assuming proper validation)
        assert response.status_code in [200, 400, 422]  # Success or validation error

    def test_admin_scope_can_access_admin_endpoint(self, client, auth_headers):
        """Test that admin scope can access admin endpoints."""
        api_key = self.create_api_key_with_scopes(client, auth_headers, ["admin"])

        # Try to access an admin endpoint
        response = client.get(
            "/api/v1/admin/stats",
            headers={"X-API-Key": api_key}
        )
        # This should succeed (assuming the endpoint exists)
        assert response.status_code in [200, 404]

    def test_no_scope_denied_protected_endpoint(self, client):
        """Test that requests without API key are denied for protected endpoints."""
        response = client.get("/api/v1/users/profile")
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_invalid_api_key_denied(self, client):
        """Test that invalid API keys are denied."""
        response = client.get(
            "/api/v1/users/profile",
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401
        assert "Invalid or expired API key" in response.json()["detail"]


class TestMigrationAndBackwardCompatibility:
    """Test migration and backward compatibility features."""

    @pytest.fixture
    async def api_key_service(self, db_session: AsyncSession):
        return ApiKeyService(db_session)

    @pytest.mark.asyncio
    async def test_migrate_legacy_keys_placeholder(self, api_key_service: ApiKeyService):
        """Test the legacy key migration placeholder."""
        # This is a placeholder test - in real implementation,
        # this would test actual migration logic
        migrated_keys = await api_key_service.migrate_legacy_keys(user_id=1)
        assert isinstance(migrated_keys, list)

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, api_key_service: ApiKeyService, test_user: User):
        """Test cleaning up expired API keys."""
        # Create an expired key
        expired_time = datetime.now(UTC) - timedelta(days=1)
        await api_key_service.create_api_key(
            user_id=test_user.id,
            name="Expired Key",
            scopes=["read"],
            expires_at=expired_time
        )

        # Run cleanup
        cleaned_count = await api_key_service.cleanup_expired_keys()
        assert cleaned_count >= 1

        # Verify key is deactivated
        keys = await api_key_service.get_user_api_keys(test_user.id)
        expired_keys = [k for k in keys if not k.is_active]
        assert len(expired_keys) >= 1


if __name__ == "__main__":
    pytest.main([__file__])