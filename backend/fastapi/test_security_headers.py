#!/usr/bin/env python3
"""
Simple test script to verify security headers are working
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from api.main import app

def test_security_headers():
    """Test that security headers are present in responses"""
    client = TestClient(app)

    # Test health endpoint
    response = client.get("/api/v1/health")
    print(f"Health endpoint status: {response.status_code}")

    headers = response.headers
    print("\nSecurity Headers:")

    expected_headers = [
        "X-Frame-Options",
        "X-Content-Type-Options",
        "Content-Security-Policy",
        "Referrer-Policy"
    ]

    for header in expected_headers:
        if header in headers:
            print(f"✅ {header}: {headers[header]}")
        else:
            print(f"❌ {header}: MISSING")

    # Check CSP content
    if "Content-Security-Policy" in headers:
        csp = headers["Content-Security-Policy"]
        print(f"\nCSP Analysis:")
        checks = [
            ("default-src 'self'", "default-src 'self'" in csp),
            ("script-src 'none'", "script-src 'none'" in csp),
            ("style-src 'none'", "style-src 'none'" in csp),
            ("img-src 'self' data:", "img-src 'self' data:" in csp),
            ("connect-src 'self'", "connect-src 'self'" in csp),
            ("frame-ancestors 'none'", "frame-ancestors 'none'" in csp)
        ]

        for check, passed in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

    # Check HSTS (should not be present in dev mode)
    if "Strict-Transport-Security" in headers:
        print(f"⚠️  Strict-Transport-Security: {headers['Strict-Transport-Security']} (Should not be present in dev)")
    else:
        print("✅ Strict-Transport-Security: Not present (correct for dev mode)")

if __name__ == "__main__":
    test_security_headers()