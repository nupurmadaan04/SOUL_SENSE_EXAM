"""
mTLS Middleware for FastAPI (#1253)

Provides mutual TLS authentication and validation for internal service communication.
"""

import logging
import ssl
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID, ExtensionOID

from api.services.mtls_certificate_manager import get_cert_manager

logger = logging.getLogger(__name__)


class MTLSMiddleware(BaseHTTPMiddleware):
    """
    Middleware for mutual TLS authentication.

    Validates client certificates against internal CA and enforces mTLS
    for protected endpoints.
    """

    def __init__(
        self,
        app,
        mtls_required_paths: list = None,
        exempt_paths: list = None,
        cert_header: str = "X-Client-Cert"
    ):
        super().__init__(app)
        self.cert_manager = get_cert_manager()
        self.mtls_required_paths = mtls_required_paths or ["/api/internal", "/api/services"]
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        self.cert_header = cert_header

    async def dispatch(self, request: Request, call_next):
        """Process request with mTLS validation."""

        # Skip mTLS validation for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Check if path requires mTLS
        requires_mtls = self._requires_mtls(request.url.path)

        if requires_mtls:
            # Validate client certificate
            cert_valid, cert_info = self._validate_client_certificate(request)

            if not cert_valid:
                logger.warning(f"mTLS validation failed for {request.url.path} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Client certificate required",
                        "message": "Valid client certificate must be provided for this endpoint"
                    }
                )

            # Add certificate info to request state
            request.state.client_cert_info = cert_info

        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from mTLS validation."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    def _requires_mtls(self, path: str) -> bool:
        """Check if path requires mTLS authentication."""
        return any(path.startswith(required) for required in self.mtls_required_paths)

    def _validate_client_certificate(self, request: Request) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate client certificate from request.

        Returns (is_valid, cert_info) tuple.
        """
        try:
            # Try to get certificate from header first (for proxies/load balancers)
            cert_pem = request.headers.get(self.cert_header)

            # If not in header, try to get from SSL connection (direct TLS)
            if not cert_pem and hasattr(request, 'scope') and 'extensions' in request.scope:
                ssl_info = request.scope.get('extensions', {}).get('ssl')
                if ssl_info and 'client_cert' in ssl_info:
                    cert_pem = ssl_info['client_cert']

            if not cert_pem:
                logger.debug("No client certificate found in request")
                return False, None

            # Parse certificate
            try:
                cert = x509.load_pem_x509_certificate(
                    cert_pem.encode('utf-8'),
                    default_backend()
                )
            except Exception as e:
                logger.warning(f"Failed to parse client certificate: {e}")
                return False, None

            # Extract service name from certificate
            service_name = self._extract_service_name(cert)
            if not service_name:
                logger.warning("Could not extract service name from certificate")
                return False, None

            # Validate certificate against our CA
            is_valid = self.cert_manager.validate_certificate(service_name, cert_pem)
            if not is_valid:
                logger.warning(f"Certificate validation failed for service {service_name}")
                return False, None

            # Extract certificate information
            cert_info = {
                "service_name": service_name,
                "common_name": self._get_common_name(cert),
                "serial_number": cert.serial_number,
                "not_before": cert.not_valid_before.isoformat(),
                "not_after": cert.not_valid_after.isoformat(),
                "issuer": cert.issuer.rfc4514_string(),
                "subject": cert.subject.rfc4514_string(),
                "dns_names": self._get_dns_names(cert),
                "ip_addresses": self._get_ip_addresses(cert),
            }

            logger.debug(f"Valid certificate presented by service {service_name}")
            return True, cert_info

        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return False, None

    def _extract_service_name(self, cert: x509.Certificate) -> Optional[str]:
        """Extract service name from certificate organizational unit."""
        try:
            ou_attrs = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)
            if ou_attrs:
                return ou_attrs[0].value
        except Exception:
            pass
        return None

    def _get_common_name(self, cert: x509.Certificate) -> Optional[str]:
        """Get common name from certificate."""
        try:
            cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if cn_attrs:
                return cn_attrs[0].value
        except Exception:
            pass
        return None

    def _get_dns_names(self, cert: x509.Certificate) -> list[str]:
        """Get DNS names from certificate SAN extension."""
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san = san_ext.value
            return [name.value for name in san if isinstance(name, x509.DNSName)]
        except Exception:
            return []

    def _get_ip_addresses(self, cert: x509.Certificate) -> list[str]:
        """Get IP addresses from certificate SAN extension."""
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            san = san_ext.value
            return [str(name.value) for name in san if isinstance(name, x509.IPAddress)]
        except Exception:
            return []


class MTLSClient:
    """
    HTTP client with mTLS support for internal service communication.
    """

    def __init__(self, service_name: str, certs_dir: str = "certs"):
        self.service_name = service_name
        self.cert_manager = get_cert_manager()

        # Get service certificate
        cert_data = self.cert_manager.get_service_certificate(service_name)
        if not cert_data:
            raise ValueError(f"No certificate found for service {service_name}")

        # Create SSL context with client certificate
        self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        self.ssl_context.check_hostname = True
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Load CA certificate for server verification
        ca_cert_path = Path(certs_dir) / "ca" / "ca.crt"
        if ca_cert_path.exists():
            self.ssl_context.load_verify_locations(str(ca_cert_path))
        else:
            # Load CA cert from string
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
                f.write(cert_data["ca_certificate"])
                temp_ca_path = f.name

            try:
                self.ssl_context.load_verify_locations(temp_ca_path)
            finally:
                os.unlink(temp_ca_path)

        # Load client certificate and key
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as cert_file:
            cert_file.write(cert_data["certificate"])
            cert_path = cert_file.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as key_file:
            key_file.write(cert_data["private_key"])
            key_path = key_file.name

        try:
            self.ssl_context.load_cert_chain(cert_path, key_path)
        finally:
            os.unlink(cert_path)
            os.unlink(key_path)

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make GET request with mTLS."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make POST request with mTLS."""
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make PUT request with mTLS."""
        return await self._request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request with mTLS."""
        return await self._request("DELETE", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with mTLS authentication."""
        try:
            import httpx

            async with httpx.AsyncClient(verify=self.ssl_context) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()

                # Try to parse JSON response
                try:
                    return response.json()
                except Exception:
                    return {"text": response.text, "status_code": response.status_code}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {method} {url}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Request failed for {method} {url}: {e}")
            raise


def create_mtls_app(
    app,
    mtls_required_paths: list = None,
    exempt_paths: list = None
):
    """
    Create FastAPI app with mTLS middleware.

    Args:
        app: FastAPI application instance
        mtls_required_paths: List of URL paths that require mTLS
        exempt_paths: List of URL paths exempt from mTLS

    Returns:
        FastAPI app with mTLS middleware
    """
    if mtls_required_paths is None:
        mtls_required_paths = ["/api/internal", "/api/services"]

    if exempt_paths is None:
        exempt_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]

    # Add mTLS middleware
    app.add_middleware(
        MTLSMiddleware,
        mtls_required_paths=mtls_required_paths,
        exempt_paths=exempt_paths
    )

    logger.info("mTLS middleware enabled for internal service communication")
    return app


def get_client_cert_info(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get client certificate information from request.

    Only available for requests that passed mTLS validation.
    """
    return getattr(request.state, 'client_cert_info', None)</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\backend\fastapi\api\middleware\mtls_middleware.py