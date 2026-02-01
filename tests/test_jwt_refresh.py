import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from backend.fastapi.api.services.auth_service import AuthService
from backend.fastapi.api.root_models import User, RefreshToken
from backend.fastapi.api.exceptions import AuthException
from backend.fastapi.api.constants.errors import ErrorCode

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def auth_service(mock_db):
    return AuthService(db=mock_db)

@pytest.fixture
def mock_user():
    return User(id=1, username="testuser", password_hash="hashed_secret")

def test_create_refresh_token(auth_service, mock_db):
    """Verify refresh token creation and DB storage"""
    token = auth_service.create_refresh_token(user_id=1)
    
    assert len(token) > 0
    # Verify DB add was called
    assert mock_db.add.called
    stored_token = mock_db.add.call_args[0][0]
    assert isinstance(stored_token, RefreshToken)
    assert stored_token.user_id == 1
    assert stored_token.expires_at > datetime.now(timezone.utc)
    assert not stored_token.is_revoked

def test_refresh_token_rotation_success(auth_service, mock_user, mock_db):
    """Verify using a valid token returns new tokens and revokes the old one"""
    # Setup mocks
    old_token_str = "valid_old_token"
    mock_db_token = RefreshToken(
        id=1, 
        user_id=1, 
        token_hash="hashed_old_token", 
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    
    # Configure query chain
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_db_token, # First query: Find refresh token
        mock_user      # Second query: Find user
    ]
    
    with patch("hashlib.sha256") as mock_hash:
        mock_hash.return_value.hexdigest.return_value = "hashed_old_token"
        
        # Action
        access_token, new_refresh_token = auth_service.refresh_access_token(old_token_str)
        
        # Verify old token revoked
        assert mock_db_token.is_revoked is True
        
        # Verify new tokens returned
        assert len(access_token) > 0
        assert len(new_refresh_token) > 0
        assert new_refresh_token != old_token_str

def test_refresh_token_invalid(auth_service, mock_db):
    """Verify using an invalid token raises exception"""
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(AuthException) as exc:
        auth_service.refresh_access_token("invalid_token")
    
    assert exc.value.detail["code"] == ErrorCode.AUTH_INVALID_TOKEN

def test_refresh_token_revoked(auth_service, mock_db):
    """Verify using a revoked token raises exception (Rotation enforcement)"""
    mock_db.query.return_value.filter.return_value.first.return_value = None # Filter includes is_revoked=False
    
    with pytest.raises(AuthException) as exc:
        auth_service.refresh_access_token("revoked_token")
        
    assert exc.value.detail["code"] == ErrorCode.AUTH_INVALID_TOKEN

def test_manual_revocation(auth_service, mock_db):
    """Verify manual revocation works (Logout)"""
    mock_db_token = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_db_token
    
    auth_service.revoke_refresh_token("some_token")
    
    assert mock_db_token.is_revoked is True
    assert mock_db.commit.called
