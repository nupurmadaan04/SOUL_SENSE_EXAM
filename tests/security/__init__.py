"""
Security Regression Tests Package

This package contains automated tests to validate authentication and authorization
security behaviors, preventing reintroduction of known vulnerabilities.

Tests included:
- JWT token validation (expired, tampered, malformed)
- Role-based access control (admin vs regular user permissions)
- Refresh token security (replay prevention, rotation)
- Comprehensive security regression suite

All tests are designed to run in CI and fail builds on security regressions.
"""

# Import all test modules to ensure they are discovered by pytest
from . import test_jwt_security
from . import test_rbac_security
from . import test_refresh_token_security
from . import test_security_regression_suite

__all__ = [
    'test_jwt_security',
    'test_rbac_security',
    'test_refresh_token_security',
    'test_security_regression_suite'
]