"""
Integration of KeychainManager with application configuration.

Provides seamless fallback from Keychain -> Environment -> Default.
"""

import os
import logging
from typing import Optional
from app.utils.keychain_manager import get_keychain_manager

logger = logging.getLogger(__name__)


class SecureConfig:
    """
    Configuration manager with Keychain integration.
    
    Priority order:
    1. Keychain/secure storage
    2. Environment variables
    3. Default values
    """
    
    def __init__(self, service_name: str = "soulsense"):
        self.service_name = service_name
        self.keychain = get_keychain_manager()
        self._cache = {}
    
    def get(self, key: str, env_var: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
        """
        Get configuration value with fallback chain.
        
        Args:
            key: Secret key name in keychain
            env_var: Environment variable name (defaults to key.upper())
            default: Default value if not found
        
        Returns:
            Configuration value or None
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Try keychain
        value = self.keychain.get_secret(self.service_name, key)
        if value:
            logger.debug(f"Loaded {key} from secure storage")
            self._cache[key] = value
            return value
        
        # Try environment
        env_var = env_var or key.upper()
        value = os.getenv(env_var)
        if value:
            logger.debug(f"Loaded {key} from environment variable {env_var}")
            self._cache[key] = value
            return value
        
        # Use default
        if default:
            logger.debug(f"Using default value for {key}")
            self._cache[key] = default
        
        return default
    
    def set(self, key: str, value: str) -> bool:
        """Store a configuration value in secure storage."""
        if self.keychain.store_secret(self.service_name, key, value):
            self._cache[key] = value
            return True
        return False
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()


# Singleton instance
_config: Optional[SecureConfig] = None


def get_secure_config() -> SecureConfig:
    """Get or create singleton SecureConfig instance."""
    global _config
    if _config is None:
        _config = SecureConfig()
    return _config


# Convenience functions for common secrets

def get_database_password(default: Optional[str] = None) -> Optional[str]:
    """Get database password from secure storage or environment."""
    config = get_secure_config()
    return config.get("db_password", "DATABASE_PASSWORD", default)


def get_jwt_secret(default: Optional[str] = None) -> Optional[str]:
    """Get JWT secret key from secure storage or environment."""
    config = get_secure_config()
    return config.get("jwt_secret", "JWT_SECRET_KEY", default)


def get_encryption_key(default: Optional[str] = None) -> Optional[str]:
    """Get encryption key from secure storage or environment."""
    config = get_secure_config()
    return config.get("encryption_key", "ENCRYPTION_KEY", default)


def get_redis_password(default: Optional[str] = None) -> Optional[str]:
    """Get Redis password from secure storage or environment."""
    config = get_secure_config()
    return config.get("redis_password", "REDIS_PASSWORD", default)


def get_smtp_password(default: Optional[str] = None) -> Optional[str]:
    """Get SMTP password from secure storage or environment."""
    config = get_secure_config()
    return config.get("smtp_password", "SMTP_PASSWORD", default)
