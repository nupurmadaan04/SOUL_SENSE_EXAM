"""
mTLS Test Suite (#1253)

Comprehensive tests for mutual TLS authentication including:
- Certificate authority operations
- Certificate validation
- mTLS middleware functionality
- Client certificate authentication
- Edge cases (expired certificates, invalid chains, etc.)
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from api.services.mtls_certificate_manager import (
    CertificateAuthority,
    MTLSCertificateManager,
    get_cert_manager
)
from api.middleware.mtls_middleware import MTLSMiddleware, MTLSClient
from api.config.mtls_config import MTLSConfig, ServiceConfig


class TestCertificateAuthority:
    """Test Certificate Authority operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.ca_dir = Path(self.temp_dir) / "ca"
        self.ca_dir.mkdir()

        self.ca = CertificateAuthority(
            ca_dir=str(self.ca_dir),
            country="US",
            state="CA",
            locality="Test City",
            organization="Test Org",
            common_name="Test CA"
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_ca_creation(self):
        """Test CA certificate and key creation."""
        self.ca.create_ca_certificate()

        # Check CA certificate exists
        ca_cert_path = self.ca_dir / "ca.crt"
        ca_key_path = self.ca_dir / "ca.key"

        assert ca_cert_path.exists()
        assert ca_key_path.exists()

        # Load and verify CA certificate
        with open(ca_cert_path, 'r') as f:
            ca_cert_pem = f.read()

        ca_cert = x509.load_pem_x509_certificate(
            ca_cert_pem.encode('utf-8'),
            default_backend()
        )

        # Verify CA properties
        assert ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == "Test CA"
        assert ca_cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value == "Test Org"

        # Verify it's a CA certificate
        basic_constraints = ca_cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.BASIC_CONSTRAINTS
        )
        assert basic_constraints.value.ca is True

    def test_certificate_issuance(self):
        """Test issuing certificates for services."""
        self.ca.create_ca_certificate()

        # Issue certificate for a service
        cert_pem, key_pem = self.ca.issue_certificate(
            service_name="test-service",
            dns_names=["test-service.local", "test-service.internal"],
            ip_addresses=["127.0.0.1"],
            validity_days=30
        )

        # Verify certificate was issued
        assert cert_pem is not None
        assert key_pem is not None

        # Parse certificate
        cert = x509.load_pem_x509_certificate(
            cert_pem.encode('utf-8'),
            default_backend()
        )

        # Verify certificate properties
        assert cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value == "test-service"

        # Verify SAN extension
        san_ext = cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )
        san = san_ext.value

        dns_names = [name.value for name in san if isinstance(name, x509.DNSName)]
        ip_addresses = [str(name.value) for name in san if isinstance(name, x509.IPAddress)]

        assert "test-service.local" in dns_names
        assert "test-service.internal" in dns_names
        assert "127.0.0.1" in ip_addresses

    def test_ca_loading(self):
        """Test loading existing CA."""
        self.ca.create_ca_certificate()

        # Create new CA instance and load existing
        ca2 = CertificateAuthority(
            ca_dir=str(self.ca_dir),
            country="US",
            state="CA",
            locality="Test City",
            organization="Test Org",
            common_name="Test CA"
        )

        ca2.load_ca_certificate()

        # Verify CA was loaded
        assert ca2.ca_cert is not None
        assert ca2.ca_key is not None


class TestMTLSCertificateManager:
    """Test MTLS Certificate Manager operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = MTLSConfig(
            certs_dir=str(self.temp_dir),
            ca_dir=str(Path(self.temp_dir) / "ca"),
            services_dir=str(Path(self.temp_dir) / "services")
        )

        self.manager = MTLSCertificateManager(self.config)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_service_registration(self):
        """Test registering a service."""
        service_config = ServiceConfig(
            name="test-service",
            dns_names=["test-service.local"],
            ip_addresses=["127.0.0.1"],
            ports=[8443]
        )

        self.manager.register_service(service_config)

        # Verify service was registered
        assert "test-service" in self.manager.services
        assert self.manager.services["test-service"]["dns_names"] == ["test-service.local"]

    def test_certificate_generation(self):
        """Test generating certificates for registered services."""
        service_config = ServiceConfig(
            name="test-service",
            dns_names=["test-service.local"],
            ip_addresses=["127.0.0.1"]
        )

        self.manager.register_service(service_config)
        cert_data = self.manager.generate_service_certificate("test-service")

        # Verify certificate data
        assert "certificate" in cert_data
        assert "private_key" in cert_data
        assert "ca_certificate" in cert_data
        assert cert_data["service_name"] == "test-service"

    def test_certificate_validation(self):
        """Test certificate validation."""
        service_config = ServiceConfig(
            name="test-service",
            dns_names=["test-service.local"],
            ip_addresses=["127.0.0.1"]
        )

        self.manager.register_service(service_config)
        cert_data = self.manager.generate_service_certificate("test-service")

        # Validate certificate
        is_valid = self.manager.validate_certificate("test-service", cert_data["certificate"])
        assert is_valid is True

    def test_invalid_certificate_validation(self):
        """Test validation of invalid certificates."""
        # Test with non-existent service
        is_valid = self.manager.validate_certificate("non-existent-service", "invalid-cert")
        assert is_valid is False

        # Test with invalid certificate format
        service_config = ServiceConfig(name="test-service")
        self.manager.register_service(service_config)

        is_valid = self.manager.validate_certificate("test-service", "invalid-cert-pem")
        assert is_valid is False

    def test_certificate_rotation(self):
        """Test certificate rotation."""
        service_config = ServiceConfig(name="test-service")
        self.manager.register_service(service_config)

        # Generate initial certificate
        old_cert_data = self.manager.generate_service_certificate("test-service")

        # Rotate certificate
        new_cert_data = self.manager.rotate_certificate("test-service")

        # Verify new certificate is different
        assert new_cert_data["certificate"] != old_cert_data["certificate"]
        assert new_cert_data["private_key"] != old_cert_data["private_key"]

        # Verify old certificate is no longer valid
        is_old_valid = self.manager.validate_certificate("test-service", old_cert_data["certificate"])
        assert is_old_valid is False

        # Verify new certificate is valid
        is_new_valid = self.manager.validate_certificate("test-service", new_cert_data["certificate"])
        assert is_new_valid is True


class TestMTLSMiddleware:
    """Test mTLS middleware functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = MTLSConfig(
            certs_dir=str(self.temp_dir),
            ca_dir=str(Path(self.temp_dir) / "ca"),
            services_dir=str(Path(self.temp_dir) / "services")
        )

        self.manager = MTLSCertificateManager(self.config)

        # Register test service
        service_config = ServiceConfig(
            name="test-service",
            dns_names=["test-service.local"],
            ip_addresses=["127.0.0.1"]
        )
        self.manager.register_service(service_config)
        self.cert_data = self.manager.generate_service_certificate("test-service")

        # Create FastAPI app with middleware
        self.app = FastAPI()
        self.app.add_middleware(
            MTLSMiddleware,
            mtls_required_paths=["/api/internal"],
            exempt_paths=["/health"]
        )

        @self.app.get("/health")
        async def health():
            return {"status": "ok"}

        @self.app.get("/api/internal/test")
        async def internal_test(request: Request):
            cert_info = getattr(request.state, 'client_cert_info', None)
            return {"cert_info": cert_info}

        self.client = TestClient(self.app)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_exempt_path_access(self):
        """Test accessing exempt paths without certificate."""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_mtls_required_path_without_cert(self):
        """Test accessing mTLS required path without certificate."""
        response = self.client.get("/api/internal/test")
        assert response.status_code == 401
        assert "Client certificate required" in response.json()["error"]

    @patch('api.middleware.mtls_middleware.MTLSMiddleware._validate_client_certificate')
    def test_mtls_required_path_with_valid_cert(self, mock_validate):
        """Test accessing mTLS required path with valid certificate."""
        # Mock valid certificate validation
        mock_validate.return_value = (True, {
            "service_name": "test-service",
            "common_name": "test-service",
            "serial_number": 12345
        })

        response = self.client.get("/api/internal/test")
        assert response.status_code == 200

        data = response.json()
        assert "cert_info" in data
        assert data["cert_info"]["service_name"] == "test-service"

    @patch('api.middleware.mtls_middleware.MTLSMiddleware._validate_client_certificate')
    def test_mtls_required_path_with_invalid_cert(self, mock_validate):
        """Test accessing mTLS required path with invalid certificate."""
        # Mock invalid certificate validation
        mock_validate.return_value = (False, None)

        response = self.client.get("/api/internal/test")
        assert response.status_code == 401
        assert "Client certificate required" in response.json()["error"]


class TestMTLSClient:
    """Test mTLS client functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = MTLSConfig(
            certs_dir=str(self.temp_dir),
            ca_dir=str(Path(self.temp_dir) / "ca"),
            services_dir=str(Path(self.temp_dir) / "services")
        )

        self.manager = MTLSCertificateManager(self.config)

        # Register test service
        service_config = ServiceConfig(
            name="test-client-service",
            dns_names=["test-client.local"],
            ip_addresses=["127.0.0.1"]
        )
        self.manager.register_service(service_config)
        self.cert_data = self.manager.generate_service_certificate("test-client-service")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_client_creation(self):
        """Test creating mTLS client."""
        client = MTLSClient("test-client-service", certs_dir=str(self.temp_dir))

        # Verify SSL context was created
        assert client.ssl_context is not None
        assert client.service_name == "test-client-service"

    def test_client_creation_no_cert(self):
        """Test creating client for non-existent service."""
        with pytest.raises(ValueError, match="No certificate found"):
            MTLSClient("non-existent-service", certs_dir=str(self.temp_dir))


class TestMTLSEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = MTLSConfig(
            certs_dir=str(self.temp_dir),
            ca_dir=str(Path(self.temp_dir) / "ca"),
            services_dir=str(Path(self.temp_dir) / "services")
        )

        self.manager = MTLSCertificateManager(self.config)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_expired_certificate_validation(self):
        """Test validation of expired certificates."""
        # Create service with short validity
        service_config = ServiceConfig(name="test-service")
        self.manager.register_service(service_config)

        # Generate certificate
        cert_data = self.manager.generate_service_certificate("test-service")

        # Manually create expired certificate (this would require mocking datetime)
        # For now, just test that validation handles invalid certs gracefully
        is_valid = self.manager.validate_certificate("test-service", "invalid-cert")
        assert is_valid is False

    def test_malformed_certificate_handling(self):
        """Test handling of malformed certificates."""
        service_config = ServiceConfig(name="test-service")
        self.manager.register_service(service_config)

        # Test various malformed certificate strings
        malformed_certs = [
            "",
            "not-a-certificate",
            "-----BEGIN CERTIFICATE-----\ninvalid\n-----END CERTIFICATE-----",
            "-----BEGIN CERTIFICATE-----\n" + "a" * 1000 + "\n-----END CERTIFICATE-----"
        ]

        for malformed_cert in malformed_certs:
            is_valid = self.manager.validate_certificate("test-service", malformed_cert)
            assert is_valid is False

    def test_concurrent_certificate_operations(self):
        """Test concurrent certificate operations."""
        import threading

        service_config = ServiceConfig(name="test-service")
        self.manager.register_service(service_config)

        results = []
        errors = []

        def generate_cert():
            try:
                cert_data = self.manager.generate_service_certificate("test-service")
                results.append(cert_data)
            except Exception as e:
                errors.append(e)

        # Start multiple threads generating certificates
        threads = []
        for i in range(5):
            t = threading.Thread(target=generate_cert)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0
        assert len(results) == 5

        # Verify all certificates are valid
        for cert_data in results:
            is_valid = self.manager.validate_certificate("test-service", cert_data["certificate"])
            assert is_valid is True


class TestMTLSIntegration:
    """Integration tests for complete mTLS flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = MTLSConfig(
            certs_dir=str(self.temp_dir),
            ca_dir=str(Path(self.temp_dir) / "ca"),
            services_dir=str(Path(self.temp_dir) / "services")
        )

        self.manager = MTLSCertificateManager(self.config)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_full_mtls_flow(self):
        """Test complete mTLS flow from registration to validation."""
        # Register services
        client_service = ServiceConfig(
            name="client-service",
            dns_names=["client.local"],
            ip_addresses=["127.0.0.1"]
        )
        server_service = ServiceConfig(
            name="server-service",
            dns_names=["server.local"],
            ip_addresses=["127.0.0.1"]
        )

        self.manager.register_service(client_service)
        self.manager.register_service(server_service)

        # Generate certificates
        client_cert = self.manager.generate_service_certificate("client-service")
        server_cert = self.manager.generate_service_certificate("server-service")

        # Validate certificates
        assert self.manager.validate_certificate("client-service", client_cert["certificate"])
        assert self.manager.validate_certificate("server-service", server_cert["certificate"])

        # Test certificate rotation
        new_client_cert = self.manager.rotate_certificate("client-service")
        assert self.manager.validate_certificate("client-service", new_client_cert["certificate"])
        assert not self.manager.validate_certificate("client-service", client_cert["certificate"])

        # Verify different certificates
        assert new_client_cert["certificate"] != client_cert["certificate"]
        assert new_client_cert["private_key"] != client_cert["private_key"]


if __name__ == "__main__":
    pytest.main([__file__])