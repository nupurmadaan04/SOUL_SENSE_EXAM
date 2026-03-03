"""
macOS Keychain integration for secure local secrets management.

Provides cross-platform abstraction with macOS Keychain as primary backend,
falling back to encrypted file storage on other platforms.
"""

import platform
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SecretBackend(ABC):
    """Abstract interface for secret storage backends."""
    
    @abstractmethod
    def store(self, service: str, account: str, secret: str) -> bool:
        """Store a secret."""
        pass
    
    @abstractmethod
    def retrieve(self, service: str, account: str) -> Optional[str]:
        """Retrieve a secret."""
        pass
    
    @abstractmethod
    def delete(self, service: str, account: str) -> bool:
        """Delete a secret."""
        pass


class MacOSKeychainBackend(SecretBackend):
    """macOS Keychain backend using keyring library."""
    
    def __init__(self):
        try:
            import keyring
            self.keyring = keyring
            logger.info("macOS Keychain backend initialized")
        except ImportError:
            raise RuntimeError("keyring library required for macOS Keychain")
    
    def store(self, service: str, account: str, secret: str) -> bool:
        try:
            self.keyring.set_password(service, account, secret)
            logger.info(f"Stored secret for {service}:{account} in Keychain")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret in Keychain: {e}")
            return False
    
    def retrieve(self, service: str, account: str) -> Optional[str]:
        try:
            secret = self.keyring.get_password(service, account)
            if secret:
                logger.debug(f"Retrieved secret for {service}:{account}")
            return secret
        except Exception as e:
            logger.error(f"Failed to retrieve secret from Keychain: {e}")
            return None
    
    def delete(self, service: str, account: str) -> bool:
        try:
            self.keyring.delete_password(service, account)
            logger.info(f"Deleted secret for {service}:{account} from Keychain")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret from Keychain: {e}")
            return False


class EncryptedFileBackend(SecretBackend):
    """Fallback encrypted file storage for non-macOS platforms."""
    
    def __init__(self, secrets_dir: str = ".secrets"):
        from pathlib import Path
        from cryptography.fernet import Fernet
        import os
        
        self.secrets_dir = Path(secrets_dir)
        self.secrets_dir.mkdir(exist_ok=True, mode=0o700)
        
        key_file = self.secrets_dir / ".key"
        if key_file.exists():
            self.key = key_file.read_bytes()
        else:
            self.key = Fernet.generate_key()
            key_file.write_bytes(self.key)
            os.chmod(key_file, 0o600)
        
        self.cipher = Fernet(self.key)
        logger.info("Encrypted file backend initialized")
    
    def _get_path(self, service: str, account: str) -> "Path":
        from pathlib import Path
        import hashlib
        name = hashlib.sha256(f"{service}:{account}".encode()).hexdigest()
        return self.secrets_dir / name
    
    def store(self, service: str, account: str, secret: str) -> bool:
        try:
            path = self._get_path(service, account)
            encrypted = self.cipher.encrypt(secret.encode())
            path.write_bytes(encrypted)
            import os
            os.chmod(path, 0o600)
            logger.info(f"Stored secret for {service}:{account} in encrypted file")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret in file: {e}")
            return False
    
    def retrieve(self, service: str, account: str) -> Optional[str]:
        try:
            path = self._get_path(service, account)
            if not path.exists():
                return None
            encrypted = path.read_bytes()
            decrypted = self.cipher.decrypt(encrypted)
            logger.debug(f"Retrieved secret for {service}:{account}")
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to retrieve secret from file: {e}")
            return None
    
    def delete(self, service: str, account: str) -> bool:
        try:
            path = self._get_path(service, account)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted secret for {service}:{account} from file")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret from file: {e}")
            return False


class KeychainManager:
    """
    Cross-platform secrets manager with macOS Keychain integration.
    
    Usage:
        manager = KeychainManager()
        manager.store_secret("soulsense", "db_password", "secret123")
        password = manager.get_secret("soulsense", "db_password")
    """
    
    def __init__(self, force_backend: Optional[str] = None):
        """
        Initialize with appropriate backend.
        
        Args:
            force_backend: Override auto-detection ('keychain' or 'file')
        """
        if force_backend == "keychain":
            self.backend = MacOSKeychainBackend()
        elif force_backend == "file":
            self.backend = EncryptedFileBackend()
        elif platform.system() == "Darwin":
            try:
                self.backend = MacOSKeychainBackend()
            except RuntimeError:
                logger.warning("Keychain unavailable, using encrypted file fallback")
                self.backend = EncryptedFileBackend()
        else:
            self.backend = EncryptedFileBackend()
        
        logger.info(f"KeychainManager initialized with {self.backend.__class__.__name__}")
    
    def store_secret(self, service: str, account: str, secret: str) -> bool:
        """Store a secret securely."""
        return self.backend.store(service, account, secret)
    
    def get_secret(self, service: str, account: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret, returning default if not found."""
        secret = self.backend.retrieve(service, account)
        return secret if secret is not None else default
    
    def delete_secret(self, service: str, account: str) -> bool:
        """Delete a secret."""
        return self.backend.delete(service, account)
    
    def migrate_from_env(self, service: str, env_vars: dict) -> int:
        """
        Migrate secrets from environment variables to secure storage.
        
        Args:
            service: Service name (e.g., 'soulsense')
            env_vars: Dict of {account: env_var_name}
        
        Returns:
            Number of secrets migrated
        """
        import os
        migrated = 0
        
        for account, env_var in env_vars.items():
            value = os.getenv(env_var)
            if value:
                if self.store_secret(service, account, value):
                    migrated += 1
                    logger.info(f"Migrated {env_var} to secure storage")
        
        return migrated


# Singleton instance
_manager: Optional[KeychainManager] = None


def get_keychain_manager() -> KeychainManager:
    """Get or create singleton KeychainManager instance."""
    global _manager
    if _manager is None:
        _manager = KeychainManager()
    return _manager
