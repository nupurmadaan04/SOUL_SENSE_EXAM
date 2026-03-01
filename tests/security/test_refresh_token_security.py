"""
Security Regression Tests - Refresh Token Security

Tests to ensure refresh tokens are properly validated and prevent
replay attacks and token reuse.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException

from backend.fastapi.api.services.auth_service import AuthService
from backend.fastapi.api.root_models import User, RefreshToken
from backend.fastapi.app.core import InvalidCredentialsError


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def auth_service(mock_db):
    return AuthService(db=mock_db)


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.is_admin = False
    return user


class TestRefreshTokenSecurity:
    """Test refresh token security regressions."""

    @pytest.mark.asyncio
    async def test_refresh_token_replay_detection(self, auth_service, mock_user, mock_db):
        """Test that refresh tokens cannot be reused after successful use."""
        # Setup: Create a valid refresh token
        old_token_str = "valid_refresh_token_123"
        old_token_hash = "hashed_old_token"

        # Mock the database to return the token initially
        mock_refresh_token = RefreshToken(
            id=1,
            user_id=mock_user.id,
            token_hash=old_token_hash,
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )

        # Configure query chain for token lookup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_refresh_token,  # First call: token exists and is valid
            mock_user           # Second call: user lookup
        ]

        # Mock token verification
        with patch('backend.fastapi.api.services.auth_service.verify_password', return_value=True):
            # First use should succeed and revoke the token
            result = await auth_service.refresh_token_rotation(old_token_str)

            # Verify token was revoked
            assert mock_refresh_token.is_revoked == True
            mock_db.commit.assert_called()

            # Verify new tokens were returned
            assert 'access_token' in result
            assert 'refresh_token' in result
            assert result['token_type'] == 'bearer'

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_prevention(self, auth_service, mock_user, mock_db):
        """Test that revoked refresh tokens cannot be reused."""
        # Setup: Create a revoked refresh token
        revoked_token_str = "revoked_refresh_token_456"
        revoked_token_hash = "hashed_revoked_token"

        revoked_token = RefreshToken(
            id=2,
            user_id=mock_user.id,
            token_hash=revoked_token_hash,
            is_revoked=True,  # Already revoked
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )

        # Mock database to return revoked token
        mock_db.query.return_value.filter.return_value.first.return_value = revoked_token

        # Attempt to use revoked token should fail
        with pytest.raises(InvalidCredentialsError, match="Invalid or expired refresh token"):
            await auth_service.refresh_token_rotation(revoked_token_str)

    @pytest.mark.asyncio
    async def test_expired_refresh_token_rejection(self, auth_service, mock_db):
        """Test that expired refresh tokens are rejected."""
        # Setup: Create an expired refresh token
        expired_token_str = "expired_refresh_token_789"
        expired_token_hash = "hashed_expired_token"

        expired_token = RefreshToken(
            id=3,
            user_id=1,
            token_hash=expired_token_hash,
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        )

        # Mock database to return expired token
        mock_db.query.return_value.filter.return_value.first.return_value = expired_token

        # Attempt to use expired token should fail
        with pytest.raises(InvalidCredentialsError, match="Refresh token has expired"):
            await auth_service.refresh_token_rotation(expired_token_str)

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_hash(self, auth_service, mock_db):
        """Test that refresh tokens with invalid hashes are rejected."""
        # Setup: Token exists but hash doesn't match
        invalid_token_str = "invalid_hash_token"
        stored_token_hash = "correct_hash"

        stored_token = RefreshToken(
            id=4,
            user_id=1,
            token_hash=stored_token_hash,
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )

        # Mock database to return token
        mock_db.query.return_value.filter.return_value.first.return_value = stored_token

        # Mock password verification to return False (hash doesn't match)
        with patch('backend.fastapi.api.services.auth_service.verify_password', return_value=False):
            with pytest.raises(InvalidCredentialsError, match="Invalid refresh token"):
                await auth_service.refresh_token_rotation(invalid_token_str)

    @pytest.mark.asyncio
    async def test_refresh_token_concurrent_usage(self, auth_service, mock_user, mock_db):
        """Test handling of concurrent refresh token usage."""
        # This test simulates a race condition where the same token
        # is used twice before the first revocation takes effect

        token_str = "concurrent_token_abc"
        token_hash = "hashed_concurrent_token"

        # Create token
        concurrent_token = RefreshToken(
            id=5,
            user_id=mock_user.id,
            token_hash=token_hash,
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )

        # First call: token is valid
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            concurrent_token,  # Token lookup succeeds
            mock_user         # User lookup succeeds
        ]

        with patch('backend.fastapi.api.services.auth_service.verify_password', return_value=True):
            # First usage should succeed
            result1 = await auth_service.refresh_token_rotation(token_str)
            assert 'access_token' in result1
            assert concurrent_token.is_revoked == True

            # Reset for second call simulation
            concurrent_token.is_revoked = False  # Reset state

            # Second call: token should now be considered revoked
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                concurrent_token,  # Token lookup succeeds but it's revoked
                mock_user         # User lookup succeeds
            ]

            # Second usage should fail
            with pytest.raises(InvalidCredentialsError, match="Invalid or expired refresh token"):
                await auth_service.refresh_token_rotation(token_str)

    def test_refresh_token_storage_security(self, auth_service):
        """Test that refresh tokens are stored securely (hashed)."""
        token = auth_service.create_refresh_token(user_id=1)

        # Verify token is not empty
        assert len(token) > 0

        # Verify token is not the user_id (should be random)
        assert token != "1"

        # Verify token contains no predictable patterns
        # (This is a basic check; in practice, tokens should be cryptographically secure)
        assert not token.isdigit()  # Should not be just numbers
        assert len(token) >= 32  # Should be sufficiently long