"""
Environment validation utilities for SoulSense application.

This module provides comprehensive validation for environment variables
with support for different environments and type checking.
"""

import os
import re
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"
load_dotenv(ENV_FILE)


class EnvironmentValidator:
    """Validator for environment variables with type checking and validation."""

    def __init__(self, env: str = "development"):
        self.env = env
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_required_string(self, key: str, value: Optional[str]) -> bool:
        """Validate required string variable."""
        if not value or not value.strip():
            self.errors.append(f"Required environment variable '{key}' is missing or empty")
            return False
        return True

    def validate_optional_string(self, key: str, value: Optional[str], default: str = "") -> str:
        """Validate optional string variable with default."""
        return value.strip() if value else default

    def validate_integer(self, key: str, value: Optional[str], min_val: Optional[int] = None,
                        max_val: Optional[int] = None) -> Optional[int]:
        """Validate integer variable."""
        if not value:
            return None
        try:
            int_val = int(value)
            if min_val is not None and int_val < min_val:
                self.errors.append(f"'{key}' must be >= {min_val}, got {int_val}")
                return None
            if max_val is not None and int_val > max_val:
                self.errors.append(f"'{key}' must be <= {max_val}, got {int_val}")
                return None
            return int_val
        except ValueError:
            self.errors.append(f"'{key}' must be a valid integer, got '{value}'")
            return None

    def validate_boolean(self, key: str, value: Optional[str]) -> Optional[bool]:
        """Validate boolean variable."""
        if not value:
            return None
        lower_val = value.lower()
        if lower_val in ('true', '1', 'yes', 'on'):
            return True
        elif lower_val in ('false', '0', 'no', 'off'):
            return False
        else:
            self.errors.append(f"'{key}' must be a valid boolean (true/false), got '{value}'")
            return None

    def validate_url(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate URL variable."""
        if not value:
            return None
        try:
            result = urlparse(value)
            if not result.scheme or not result.netloc:
                self.errors.append(f"'{key}' must be a valid URL, got '{value}'")
                return None
            return value
        except Exception:
            self.errors.append(f"'{key}' must be a valid URL, got '{value}'")
            return None

    def validate_email(self, key: str, value: Optional[str]) -> Optional[str]:
        """Validate email variable."""
        if not value:
            return None
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            self.errors.append(f"'{key}' must be a valid email address, got '{value}'")
            return None
        return value

    def check_secret_exposure(self, key: str, value: str) -> None:
        """Check if sensitive variables are exposed in development."""
        sensitive_keywords = ['secret', 'key', 'token', 'password', 'credential']
        if self.env == "development" and any(keyword in key.lower() for keyword in sensitive_keywords):
            if value and not value.startswith(('dev_', 'test_', 'dummy_')):
                self.warnings.append(f"Potential secret exposure in development: '{key}'")

    def validate_environment_variables(self, required_vars: Dict[str, Any],
                                     optional_vars: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all environment variables."""
        validated = {}

        # Validate required variables
        for key, config in required_vars.items():
            var_type = config.get('type', 'string')
            value = os.getenv(key)

            if var_type == 'string':
                if self.validate_required_string(key, value):
                    validated[key] = value
                    self.check_secret_exposure(key, value)
            elif var_type == 'int':
                int_val = self.validate_integer(key, value, config.get('min'), config.get('max'))
                if int_val is not None:
                    validated[key] = int_val
            elif var_type == 'bool':
                bool_val = self.validate_boolean(key, value)
                if bool_val is not None:
                    validated[key] = bool_val
            elif var_type == 'url':
                url_val = self.validate_url(key, value)
                if url_val:
                    validated[key] = url_val
            elif var_type == 'email':
                email_val = self.validate_email(key, value)
                if email_val:
                    validated[key] = email_val

        # Validate optional variables
        for key, config in optional_vars.items():
            var_type = config.get('type', 'string')
            default = config.get('default', '')
            value = os.getenv(key)

            if var_type == 'string':
                validated[key] = self.validate_optional_string(key, value, default)
            elif var_type == 'int':
                int_val = self.validate_integer(key, value, config.get('min'), config.get('max'))
                validated[key] = int_val if int_val is not None else config.get('default', 0)
            elif var_type == 'bool':
                bool_val = self.validate_boolean(key, value)
                validated[key] = bool_val if bool_val is not None else config.get('default', False)

        return validated

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


def validate_environment_on_startup(env: str = "development") -> Dict[str, Any]:
    """
    Validate environment variables on application startup.

    Args:
        env: Environment name (development, staging, production)

    Returns:
        Dict containing validation results and validated variables

    Raises:
        SystemExit: If validation fails
    """
    validator = EnvironmentValidator(env)

    # Define required variables based on environment
    # Define variables
    if env in ['staging', 'production']:
        required_vars = {
            'APP_ENV': {'type': 'string'},
            'DATABASE_URL': {'type': 'string'},
            'JWT_SECRET_KEY': {'type': 'string'},
            'DATABASE_HOST': {'type': 'string'},
            'DATABASE_PORT': {'type': 'int', 'min': 1, 'max': 65535},
            'DATABASE_NAME': {'type': 'string'},
            'DATABASE_USER': {'type': 'string'},
            'DATABASE_PASSWORD': {'type': 'string'},
        }
        optional_vars = {
            'HOST': {'type': 'string', 'default': '127.0.0.1'},
            'PORT': {'type': 'int', 'default': 8000, 'min': 1, 'max': 65535},
            'DEBUG': {'type': 'bool', 'default': False},
            'JWT_ALGORITHM': {'type': 'string', 'default': 'HS256'},
            'JWT_EXPIRATION_HOURS': {'type': 'int', 'default': 24, 'min': 1},
        }
    else:
        # Development defaults (relaxed validation)
        required_vars = {} 
        optional_vars = {
            'APP_ENV': {'type': 'string', 'default': 'development'},
            'DATABASE_URL': {'type': 'string', 'default': 'sqlite:///../../data/soulsense.db'},
            'JWT_SECRET_KEY': {'type': 'string', 'default': 'dev_jwt_secret'},
            'HOST': {'type': 'string', 'default': '127.0.0.1'},
            'PORT': {'type': 'int', 'default': 8000, 'min': 1, 'max': 65535},
            'DEBUG': {'type': 'bool', 'default': True},
            'JWT_ALGORITHM': {'type': 'string', 'default': 'HS256'},
            'JWT_EXPIRATION_HOURS': {'type': 'int', 'default': 24, 'min': 1},
            'WELCOME_MESSAGE': {'type': 'string', 'default': 'Welcome to Soul Sense!'},
        }

    validated_vars = validator.validate_environment_variables(required_vars, optional_vars)
    summary = validator.get_validation_summary()

    return {
        'validated_variables': validated_vars,
        'validation_summary': summary
    }


def log_environment_summary(validated_vars: Dict[str, Any], summary: Dict[str, Any]) -> None:
    """Log environment validation summary."""
    print("Environment Validation Summary:")
    print(f"   [OK] Valid: {summary['valid']}")
    print(f"   [ERR] Errors: {summary['error_count']}")
    print(f"   [WARN] Warnings: {summary['warning_count']}")

    if summary['errors']:
        print("\n[ERR] Validation Errors:")
        for error in summary['errors']:
            print(f"   - {error}")

    if summary['warnings']:
        print("\n[WARN] Validation Warnings:")
        for warning in summary['warnings']:
            print(f"   - {warning}")

    # Log non-sensitive variables
    print("\nEnvironment Configuration (non-sensitive):")
    sensitive_keys = {'JWT_SECRET_KEY', 'DATABASE_PASSWORD', 'SECRET_KEY'}
    for key, value in validated_vars.items():
        if key not in sensitive_keys:
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: [REDACTED]")