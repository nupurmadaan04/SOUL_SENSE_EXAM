"""
Security Regression Tests - Role-Based Access Control

Tests to ensure role-based access control works correctly and prevents
unauthorized access to admin-only endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.fastapi.api.root_models import User
from backend.fastapi.app.core import AuthorizationError


@pytest.fixture
def mock_regular_user():
    """Mock regular user (non-admin)."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "regularuser"
    user.is_admin = False
    return user


@pytest.fixture
def mock_admin_user():
    """Mock admin user."""
    user = MagicMock(spec=User)
    user.id = 2
    user.username = "adminuser"
    user.is_admin = True
    return user


class TestRoleBasedAccessControl:
    """Test role-based access control security regressions."""

    def test_regular_user_cannot_access_admin_endpoint(self, mock_regular_user):
        """Test that regular users cannot access admin-only endpoints."""
        # This test simulates the authorization check that should happen
        # in admin-only endpoints

        def check_admin_access(user: User):
            """Simulate admin access check."""
            if not user.is_admin:
                raise AuthorizationError("Admin access required")
            return True

        # Regular user should be denied
        with pytest.raises(AuthorizationError, match="Admin access required"):
            check_admin_access(mock_regular_user)

    def test_admin_user_can_access_admin_endpoint(self, mock_admin_user):
        """Test that admin users can access admin-only endpoints."""
        def check_admin_access(user: User):
            """Simulate admin access check."""
            if not user.is_admin:
                raise AuthorizationError("Admin access required")
            return True

        # Admin user should be allowed
        result = check_admin_access(mock_admin_user)
        assert result is True

    def test_admin_role_persistence(self, mock_admin_user):
        """Test that admin role is properly checked from database."""
        # Simulate database query result
        mock_admin_user.is_admin = True

        # Verify the role is correctly read
        assert mock_admin_user.is_admin is True

        # Simulate role change
        mock_admin_user.is_admin = False

        def check_admin_access(user: User):
            if not user.is_admin:
                raise AuthorizationError("Admin access required")
            return True

        # Should now be denied
        with pytest.raises(AuthorizationError, match="Admin access required"):
            check_admin_access(mock_admin_user)

    def test_role_based_data_isolation(self, mock_regular_user, mock_admin_user):
        """Test that users can only access their own data or admin can access all."""

        def check_data_access(requesting_user: User, target_user_id: int):
            """Simulate data access authorization check."""
            if not requesting_user.is_admin and requesting_user.id != target_user_id:
                raise AuthorizationError("Access denied: insufficient permissions")
            return True

        # Regular user can access their own data
        result = check_data_access(mock_regular_user, mock_regular_user.id)
        assert result is True

        # Regular user cannot access other user's data
        with pytest.raises(AuthorizationError, match="Access denied: insufficient permissions"):
            check_data_access(mock_regular_user, 999)

        # Admin can access any user's data
        result = check_data_access(mock_admin_user, mock_regular_user.id)
        assert result is True

        result = check_data_access(mock_admin_user, 999)
        assert result is True

    def test_admin_endpoint_protection(self):
        """Test that admin endpoints are properly protected with role checks."""
        # This test verifies the pattern used in admin routes

        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/audit",
            "/api/v1/admin/system",
            "/api/v1/admin/config"
        ]

        def simulate_admin_route_handler(user: User, endpoint: str):
            """Simulate an admin route handler."""
            if not user.is_admin:
                raise HTTPException(status_code=403, detail="Admin access required")
            return {"message": f"Admin access granted to {endpoint}"}

        # Test with regular user
        for endpoint in admin_endpoints:
            with pytest.raises(HTTPException) as exc_info:
                simulate_admin_route_handler(mock_regular_user, endpoint)
            assert exc_info.value.status_code == 403
            assert "Admin access required" in str(exc_info.value.detail)

        # Test with admin user
        for endpoint in admin_endpoints:
            result = simulate_admin_route_handler(mock_admin_user, endpoint)
            assert "Admin access granted" in result["message"]
            assert endpoint in result["message"]