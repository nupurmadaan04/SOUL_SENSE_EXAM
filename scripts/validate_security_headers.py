#!/usr/bin/env python3
"""
Security Headers Validation Script for CI/CD

This script validates that all required security headers are present
on deployed API endpoints. It can be used in CI pipelines to ensure
security headers are properly enforced.

Usage:
    python scripts/validate_security_headers.py --url https://api.example.com

Exit codes:
    0 - All validations passed
    1 - Missing required headers
    2 - Invalid header values
    3 - Network/connection error
"""

import argparse
import sys
import requests
from typing import Dict, List, Tuple
import json


class SecurityHeadersValidator:
    """Validates security headers against policy requirements."""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def validate_headers(self, endpoint: str = "/api/v1/health") -> Tuple[bool, List[str], Dict[str, str]]:
        """
        Validate security headers on the specified endpoint.

        Returns:
            (success, errors, headers)
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            headers = dict(response.headers)
            errors = []

            # Check required headers
            required_headers = {
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }

            for header, expected_value in required_headers.items():
                if header not in headers:
                    errors.append(f"Missing required header: {header}")
                elif headers[header] != expected_value:
                    errors.append(f"Invalid {header} value: got '{headers[header]}', expected '{expected_value}'")

            # Validate Content Security Policy
            if "Content-Security-Policy" not in headers:
                errors.append("Missing required header: Content-Security-Policy")
            else:
                csp = headers["Content-Security-Policy"]
                required_csp_directives = [
                    "default-src 'self'",
                    "script-src 'none'",
                    "style-src 'none'",
                    "img-src 'self' data:",
                    "connect-src 'self'",
                    "frame-ancestors 'none'",
                    "base-uri 'self'",
                    "form-action 'self'"
                ]

                for directive in required_csp_directives:
                    if directive not in csp:
                        errors.append(f"CSP missing required directive: {directive}")

            # HSTS validation (environment-aware)
            # In production/staging, HSTS should be present
            # In development, it should not be present
            hsts_present = "Strict-Transport-Security" in headers

            # For HTTPS URLs, HSTS should be present (production/staging)
            if url.startswith("https://"):
                if not hsts_present:
                    errors.append("HSTS header missing on HTTPS endpoint (required for production/staging)")
                else:
                    hsts_value = headers["Strict-Transport-Security"]
                    if "max-age=31536000" not in hsts_value:
                        errors.append(f"Invalid HSTS max-age: {hsts_value}")
            else:
                # For HTTP URLs (development), HSTS should not be present
                if hsts_present:
                    errors.append("HSTS header present on HTTP endpoint (should only be used with HTTPS)")

            success = len(errors) == 0
            return success, errors, headers

        except requests.exceptions.RequestException as e:
            return False, [f"Network error: {str(e)}"], {}
        except Exception as e:
            return False, [f"Unexpected error: {str(e)}"], {}


def main():
    parser = argparse.ArgumentParser(description="Validate security headers on API endpoints")
    parser.add_argument("--url", required=True, help="Base URL of the API to test")
    parser.add_argument("--endpoint", default="/api/v1/health", help="Specific endpoint to test")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--quiet", action="store_true", help="Only output errors")

    args = parser.parse_args()

    validator = SecurityHeadersValidator(args.url, args.timeout)
    success, errors, headers = validator.validate_headers(args.endpoint)

    if args.json:
        result = {
            "success": success,
            "endpoint": args.endpoint,
            "url": f"{args.url}{args.endpoint}",
            "errors": errors,
            "headers": headers
        }
        print(json.dumps(result, indent=2))
    else:
        if not args.quiet:
            print(f"🔍 Validating security headers on: {args.url}{args.endpoint}")
            print()

        if success:
            if not args.quiet:
                print("✅ All security header validations passed!")
                print()
                print("📋 Headers found:")
                for header, value in headers.items():
                    if header.lower().startswith(('x-', 'content-security', 'referrer', 'strict-transport')):
                        print(f"   {header}: {value}")
        else:
            print("❌ Security header validation failed!")
            print()
            print("🚨 Errors found:")
            for error in errors:
                print(f"   • {error}")
            print()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()