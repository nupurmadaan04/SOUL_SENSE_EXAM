import pytest
from unittest.mock import MagicMock, patch
from app.services.keychain_service import KeychainService

@pytest.fixture
def mock_keyring():
    with patch('app.services.keychain_service.keyring') as mock:
        with patch('app.services.keychain_service.KEYRING_AVAILABLE', True):
            yield mock

def test_keychain_service_is_supported(mock_keyring):
    # Should be supported if keyring is available
    assert KeychainService.is_supported() is True

def test_keychain_service_set_secret(mock_keyring):
    mock_keyring.set_password.return_value = None
    
    result = KeychainService.set_secret("test_account", "test_secret")
    
    assert result is True
    mock_keyring.set_password.assert_called_once_with(
        KeychainService.SERVICE_NAME, "test_account", "test_secret"
    )

def test_keychain_service_get_secret(mock_keyring):
    mock_keyring.get_password.return_value = "secret_value"
    
    result = KeychainService.get_secret("test_account")
    
    assert result == "secret_value"
    mock_keyring.get_password.assert_called_once_with(
        KeychainService.SERVICE_NAME, "test_account"
    )

def test_keychain_service_delete_secret(mock_keyring):
    mock_keyring.delete_password.return_value = None
    
    result = KeychainService.delete_secret("test_account")
    
    assert result is True
    mock_keyring.delete_password.assert_called_once_with(
        KeychainService.SERVICE_NAME, "test_account"
    )

def test_keychain_service_error_handling(mock_keyring):
    mock_keyring.set_password.side_effect = Exception("OS Error")
    
    result = KeychainService.set_secret("test_account", "test_secret")
    
    assert result is False

def test_keychain_not_available():
    with patch('app.services.keychain_service.KEYRING_AVAILABLE', False):
        assert KeychainService.is_supported() is False
        assert KeychainService.set_secret("a", "b") is False
        assert KeychainService.get_secret("a") is None
