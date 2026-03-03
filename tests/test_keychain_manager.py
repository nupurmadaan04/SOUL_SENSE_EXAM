"""
Tests for macOS Keychain integration.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.utils.keychain_manager import (
    KeychainManager,
    MacOSKeychainBackend,
    EncryptedFileBackend,
    get_keychain_manager
)


class TestMacOSKeychainBackend:
    """Test macOS Keychain backend."""
    
    @patch('app.utils.keychain_manager.keyring')
    def test_store_secret(self, mock_keyring):
        """Test storing secret in Keychain."""
        backend = MacOSKeychainBackend()
        
        result = backend.store("soulsense", "db_password", "secret123")
        
        assert result is True
        mock_keyring.set_password.assert_called_once_with("soulsense", "db_password", "secret123")
    
    @patch('app.utils.keychain_manager.keyring')
    def test_retrieve_secret(self, mock_keyring):
        """Test retrieving secret from Keychain."""
        mock_keyring.get_password.return_value = "secret123"
        backend = MacOSKeychainBackend()
        
        secret = backend.retrieve("soulsense", "db_password")
        
        assert secret == "secret123"
        mock_keyring.get_password.assert_called_once_with("soulsense", "db_password")
    
    @patch('app.utils.keychain_manager.keyring')
    def test_delete_secret(self, mock_keyring):
        """Test deleting secret from Keychain."""
        backend = MacOSKeychainBackend()
        
        result = backend.delete("soulsense", "db_password")
        
        assert result is True
        mock_keyring.delete_password.assert_called_once_with("soulsense", "db_password")
    
    @patch('app.utils.keychain_manager.keyring')
    def test_store_failure(self, mock_keyring):
        """Test handling of storage failure."""
        mock_keyring.set_password.side_effect = Exception("Keychain locked")
        backend = MacOSKeychainBackend()
        
        result = backend.store("soulsense", "db_password", "secret123")
        
        assert result is False


class TestEncryptedFileBackend:
    """Test encrypted file backend."""
    
    def test_store_and_retrieve(self, tmp_path):
        """Test storing and retrieving secret from encrypted file."""
        backend = EncryptedFileBackend(str(tmp_path))
        
        # Store
        result = backend.store("soulsense", "db_password", "secret123")
        assert result is True
        
        # Retrieve
        secret = backend.retrieve("soulsense", "db_password")
        assert secret == "secret123"
    
    def test_retrieve_nonexistent(self, tmp_path):
        """Test retrieving non-existent secret returns None."""
        backend = EncryptedFileBackend(str(tmp_path))
        
        secret = backend.retrieve("soulsense", "nonexistent")
        
        assert secret is None
    
    def test_delete_secret(self, tmp_path):
        """Test deleting secret from file."""
        backend = EncryptedFileBackend(str(tmp_path))
        
        # Store first
        backend.store("soulsense", "db_password", "secret123")
        
        # Delete
        result = backend.delete("soulsense", "db_password")
        assert result is True
        
        # Verify deleted
        secret = backend.retrieve("soulsense", "db_password")
        assert secret is None
    
    def test_key_persistence(self, tmp_path):
        """Test encryption key persists across instances."""
        # First instance
        backend1 = EncryptedFileBackend(str(tmp_path))
        backend1.store("soulsense", "test", "value123")
        
        # Second instance with same directory
        backend2 = EncryptedFileBackend(str(tmp_path))
        secret = backend2.retrieve("soulsense", "test")
        
        assert secret == "value123"
    
    def test_file_permissions(self, tmp_path):
        """Test that secret files have restrictive permissions."""
        backend = EncryptedFileBackend(str(tmp_path))
        backend.store("soulsense", "test", "secret")
        
        # Find the secret file
        secret_files = list(tmp_path.glob("*"))
        secret_file = [f for f in secret_files if f.name != ".key"][0]
        
        # Check permissions (should be 0o600 on Unix)
        if os.name != 'nt':  # Skip on Windows
            stat_info = secret_file.stat()
            assert oct(stat_info.st_mode)[-3:] == '600'


class TestKeychainManager:
    """Test KeychainManager."""
    
    @patch('app.utils.keychain_manager.platform.system', return_value='Darwin')
    @patch('app.utils.keychain_manager.MacOSKeychainBackend')
    def test_macos_uses_keychain(self, mock_backend_class, mock_platform):
        """Test that macOS uses Keychain backend."""
        mock_backend = Mock()
        mock_backend_class.return_value = mock_backend
        
        manager = KeychainManager()
        
        assert manager.backend == mock_backend
        mock_backend_class.assert_called_once()
    
    @patch('app.utils.keychain_manager.platform.system', return_value='Linux')
    def test_linux_uses_file_backend(self, mock_platform, tmp_path):
        """Test that Linux uses encrypted file backend."""
        with patch('app.utils.keychain_manager.EncryptedFileBackend') as mock_backend_class:
            mock_backend = Mock()
            mock_backend_class.return_value = mock_backend
            
            manager = KeychainManager()
            
            assert manager.backend == mock_backend
    
    def test_force_backend(self, tmp_path):
        """Test forcing specific backend."""
        with patch('app.utils.keychain_manager.EncryptedFileBackend') as mock_backend_class:
            mock_backend = Mock()
            mock_backend_class.return_value = mock_backend
            
            manager = KeychainManager(force_backend="file")
            
            assert manager.backend == mock_backend
    
    def test_store_and_get_secret(self, tmp_path):
        """Test storing and retrieving secret through manager."""
        manager = KeychainManager(force_backend="file")
        
        # Store
        result = manager.store_secret("soulsense", "api_key", "key123")
        assert result is True
        
        # Retrieve
        secret = manager.get_secret("soulsense", "api_key")
        assert secret == "key123"
    
    def test_get_secret_with_default(self, tmp_path):
        """Test get_secret returns default for missing secret."""
        manager = KeychainManager(force_backend="file")
        
        secret = manager.get_secret("soulsense", "nonexistent", default="fallback")
        
        assert secret == "fallback"
    
    def test_delete_secret(self, tmp_path):
        """Test deleting secret through manager."""
        manager = KeychainManager(force_backend="file")
        
        # Store first
        manager.store_secret("soulsense", "temp", "value")
        
        # Delete
        result = manager.delete_secret("soulsense", "temp")
        assert result is True
        
        # Verify deleted
        secret = manager.get_secret("soulsense", "temp")
        assert secret is None
    
    @patch.dict(os.environ, {
        'DB_PASSWORD': 'dbpass123',
        'API_KEY': 'apikey456',
        'EMPTY_VAR': ''
    })
    def test_migrate_from_env(self, tmp_path):
        """Test migrating secrets from environment variables."""
        manager = KeychainManager(force_backend="file")
        
        env_vars = {
            'db_password': 'DB_PASSWORD',
            'api_key': 'API_KEY',
            'missing': 'NONEXISTENT',
            'empty': 'EMPTY_VAR'
        }
        
        migrated = manager.migrate_from_env("soulsense", env_vars)
        
        # Should migrate 2 (DB_PASSWORD and API_KEY, not NONEXISTENT or empty)
        assert migrated == 2
        
        # Verify migrated secrets
        assert manager.get_secret("soulsense", "db_password") == "dbpass123"
        assert manager.get_secret("soulsense", "api_key") == "apikey456"


class TestSingleton:
    """Test singleton pattern."""
    
    def test_get_keychain_manager_singleton(self):
        """Test that get_keychain_manager returns same instance."""
        manager1 = get_keychain_manager()
        manager2 = get_keychain_manager()
        
        assert manager1 is manager2


class TestIntegration:
    """Integration tests for real-world scenarios."""
    
    def test_database_password_workflow(self, tmp_path):
        """Test typical database password storage workflow."""
        manager = KeychainManager(force_backend="file")
        
        # Initial setup: store password
        manager.store_secret("soulsense", "postgres_password", "prod_pass_123")
        
        # Application retrieves password
        db_password = manager.get_secret("soulsense", "postgres_password")
        assert db_password == "prod_pass_123"
        
        # Password rotation: update password
        manager.store_secret("soulsense", "postgres_password", "new_pass_456")
        
        # Verify new password
        db_password = manager.get_secret("soulsense", "postgres_password")
        assert db_password == "new_pass_456"
    
    def test_multiple_services(self, tmp_path):
        """Test managing secrets for multiple services."""
        manager = KeychainManager(force_backend="file")
        
        # Store secrets for different services
        manager.store_secret("soulsense_db", "password", "db_pass")
        manager.store_secret("soulsense_redis", "password", "redis_pass")
        manager.store_secret("soulsense_api", "key", "api_key")
        
        # Retrieve each
        assert manager.get_secret("soulsense_db", "password") == "db_pass"
        assert manager.get_secret("soulsense_redis", "password") == "redis_pass"
        assert manager.get_secret("soulsense_api", "key") == "api_key"
    
    def test_secret_not_found_graceful_degradation(self, tmp_path):
        """Test graceful handling of missing secrets."""
        manager = KeychainManager(force_backend="file")
        
        # Try to get non-existent secret with fallback
        secret = manager.get_secret("soulsense", "missing", default="fallback_value")
        
        assert secret == "fallback_value"


# Fixtures

@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create temporary directory for tests."""
    return tmp_path_factory.mktemp("secrets")
