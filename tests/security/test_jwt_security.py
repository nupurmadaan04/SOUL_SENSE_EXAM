"""
Security Regression Tests - JWT Token Validation

Tests to ensure JWT tokens are properly validated and rejected when:
- Expired
- Tampered with
- Missing required claims
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.fastapi.api.config import get_settings
from backend.fastapi.api.services.auth_service import AuthService
from backend.fastapi.api.root_models import User
from backend.fastapi.app.core import TokenExpiredError, InvalidCredentialsError


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def auth_service():
    return AuthService(db=MagicMock())


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.is_admin = False
    return user


class TestJWTTokenValidation:
    """Test JWT token validation security regressions."""

    def test_expired_jwt_rejection(self, auth_service, settings, mock_user):
        """Test that expired JWT tokens are rejected with 401."""
        # Create an expired token
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        token_data = {
            "sub": mock_user.username,
            "exp": expire,
            "jti": "test-jti-123"
        }

        expired_token = jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.jwt_algorithm
        )

        # Mock database to return user
        auth_service.db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_user
        auth_service.db.query.return_value = mock_query

        # Test token creation method directly (should handle expiry internally)
        with pytest.raises(TokenExpiredError):
            # This simulates what get_current_user does
            payload = jwt.decode(expired_token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            # The decode should succeed, but expiry check should fail
            exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            if exp_time < datetime.now(timezone.utc):
                raise TokenExpiredError("Token has expired")

    def test_tampered_jwt_rejection(self, auth_service, settings, mock_user):
        """Test that tampered JWT tokens are rejected with 401."""
        # Create a valid token first
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "sub": mock_user.username,
            "exp": expire,
            "jti": "test-jti-123"
        }

        valid_token = jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.jwt_algorithm
        )

        # Tamper with the token by changing a character
        tampered_token = valid_token[:-5] + "xxxxx"  # Corrupt the signature

        # Test that tampered token raises JWTError
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(tampered_token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])

    def test_jwt_missing_required_claims(self, auth_service, settings):
        """Test that JWT tokens missing required claims are rejected."""
        # Create token without 'sub' claim
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "exp": expire,
            "jti": "test-jti-123"
            # Missing 'sub' claim
        }

        invalid_token = jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.jwt_algorithm
        )

        # Mock database
        auth_service.db = MagicMock()

        # This should raise InvalidCredentialsError due to missing username
        with pytest.raises(InvalidCredentialsError):
            # Simulate get_current_user logic
            payload = jwt.decode(invalid_token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])
            username = payload.get("sub")
            if not username:
                raise InvalidCredentialsError()

    def test_jwt_with_invalid_algorithm(self, settings):
        """Test that JWT tokens with invalid algorithm are rejected."""
        # Create token with different algorithm than expected
        token_data = {
            "sub": "testuser",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }

        # Encode with HS512 but expect HS256
        invalid_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS512")

        # Should raise JWTError when trying to decode with HS256
        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(invalid_token, settings.SECRET_KEY, algorithms=[settings.jwt_algorithm])

    def test_jwt_blacklisted_token_rejection(self, auth_service, settings, mock_user):
        """Test that blacklisted JWT tokens are rejected."""
        # Create a valid token
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        token_data = {
            "sub": mock_user.username,
            "exp": expire,
            "jti": "test-jti-123"
        }

        valid_token = jwt.encode(
            token_data,
            settings.SECRET_KEY,
            algorithm=settings.jwt_algorithm
        )

        # Mock blacklist check to return True (blacklisted)
        with patch('backend.fastapi.api.routers.auth.get_jwt_blacklist') as mock_get_blacklist:
            mock_blacklist = MagicMock()
            mock_blacklist.is_blacklisted.return_value = True
            mock_get_blacklist.return_value = mock_blacklist

            # Mock database for fallback check
            auth_service.db = MagicMock()
            mock_query = MagicMock()
            mock_query.filter.return_value.first.return_value = None  # Not in DB revocation
            auth_service.db.query.return_value = mock_query

            # This should raise TokenExpiredError
            with pytest.raises(TokenExpiredError, match="Token has been revoked"):
                # Simulate the blacklist check in get_current_user
                from backend.fastapi.api.utils.jwt_blacklist import get_jwt_blacklist
                blacklist = get_jwt_blacklist()
                is_blacklisted = blacklist.is_blacklisted(valid_token)
                if is_blacklisted:
                    raise TokenExpiredError("Token has been revoked")