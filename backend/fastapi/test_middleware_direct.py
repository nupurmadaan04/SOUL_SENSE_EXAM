#!/usr/bin/env python3
"""
Test security headers middleware directly
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from starlette.responses import JSONResponse
from starlette.requests import Request
from unittest.mock import Mock
import asyncio

# Import the middleware directly
from api.middleware.security import SecurityHeadersMiddleware

async def test_middleware():
    """Test the security headers middleware directly"""

    # Create a mock request
    request = Mock(spec=Request)

    # Create a mock response
    response = JSONResponse({"test": "data"})

    # Create middleware instance
    middleware = SecurityHeadersMiddleware(app=None)

    # Mock the call_next function to return our response
    async def call_next(request):
        return response

    # Call the middleware
    result = await middleware.dispatch(request, call_next)

    print("Security Headers Test Results:")
    print("=" * 40)

    headers = result.headers

    # Check required headers
    checks = [
        ("X-Frame-Options", "DENY"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ]

    for header, expected in checks:
        actual = headers.get(header)
        if actual == expected:
            print(f"✅ {header}: {actual}")
        else:
            print(f"❌ {header}: Expected '{expected}', got '{actual}'")

    # Check Content-Security-Policy
    csp = headers.get("Content-Security-Policy")
    if csp:
        print(f"✅ Content-Security-Policy: Present")
        print(f"   Full CSP: {csp}")

        # Check CSP components
        csp_checks = [
            "default-src 'self'",
            "script-src 'none'",
            "style-src 'none'",
            "img-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'"
        ]

        print("   CSP Analysis:")
        for check in csp_checks:
            if check in csp:
                print(f"   ✅ {check}")
            else:
                print(f"   ❌ Missing: {check}")
    else:
        print("❌ Content-Security-Policy: MISSING")

    # Check HSTS (should not be present in dev mode since cookie_secure=False)
    hsts = headers.get("Strict-Transport-Security")
    if hsts:
        print(f"⚠️  Strict-Transport-Security: {hsts} (Present - check if this is expected)")
    else:
        print("✅ Strict-Transport-Security: Not present (expected in dev mode)")

if __name__ == "__main__":
    asyncio.run(test_middleware())