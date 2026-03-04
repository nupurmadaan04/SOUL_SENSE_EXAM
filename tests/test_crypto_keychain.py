import pytest
from unittest.mock import MagicMock, patch
from app.auth.crypto import EncryptionManager

@pytest.fixture
def mock_keychain_service():
    with patch('app.auth.crypto.KeychainService') as mock:
        yield mock

@pytest.fixture
def mock_feature_flags():
    with patch('app.auth.crypto.feature_flags') as mock:
        yield mock

def test_encryption_manager_with_keychain_enabled(mock_keychain_service, mock_feature_flags):
    # Setup
    mock_feature_flags.is_enabled.return_value = True
    mock_keychain_service.get_secret.return_value = "stored_master_key"
    
    # Reset singleton-like state for test
    EncryptionManager._key = None
    EncryptionManager._cipher = None
    
    # Action
    key = EncryptionManager._get_key()
    
    # Verify
    assert key == b"stored_master_key"
    mock_keychain_service.get_secret.assert_called_with("master_key")

def test_encryption_manager_keychain_generation(mock_keychain_service, mock_feature_flags):
    # Setup - No key in keychain
    mock_feature_flags.is_enabled.return_value = True
    mock_keychain_service.get_secret.return_value = None
    mock_keychain_service.set_secret.return_value = True
    
    # Reset
    EncryptionManager._key = None
    
    # Action
    key = EncryptionManager._get_key()
    
    # Verify
    assert key is not None
    mock_keychain_service.set_secret.assert_called_once()
    # Check that it's a valid Fernet key (32 bytes base64 encoded)
    from cryptography.fernet import Fernet
    Fernet(key) 

def test_encryption_manager_fallback(mock_keychain_service, mock_feature_flags):
    # Setup - Flag disabled
    mock_feature_flags.is_enabled.return_value = False
    
    # Reset
    EncryptionManager._key = None
    
    # Action
    key = EncryptionManager._get_key()
    
    # Verify
    # Should yield the deterministic key
    assert key is not None
    assert mock_keychain_service.get_secret.called is False
