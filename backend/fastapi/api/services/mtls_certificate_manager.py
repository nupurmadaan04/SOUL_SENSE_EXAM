"""
mTLS Certificate Authority and Management System (#1253)

Provides internal Certificate Authority (CA) for issuing and managing
mutual TLS certificates between internal services.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class CertificateAuthority:
    """
    Internal Certificate Authority for issuing mTLS certificates.

    Manages CA private key, certificate, and certificate revocation lists.
    """

    def __init__(self, ca_dir: str = "certs/ca", key_size: int = 4096):
        self.ca_dir = Path(ca_dir)
        self.key_size = key_size
        self.ca_cert_path = self.ca_dir / "ca.crt"
        self.ca_key_path = self.ca_dir / "ca.key"
        self.crl_path = self.ca_dir / "ca.crl"
        self.serial_file = self.ca_dir / "serial.txt"

        # Create CA directory if it doesn't exist
        self.ca_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or load CA
        self._load_or_create_ca()

    def _load_or_create_ca(self):
        """Load existing CA or create new one."""
        if self.ca_cert_path.exists() and self.ca_key_path.exists():
            logger.info("Loading existing CA certificate and key")
            self._load_ca()
        else:
            logger.info("Creating new Certificate Authority")
            self._create_ca()

    def _create_ca(self):
        """Create new Certificate Authority."""
        # Generate CA private key
        self.ca_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )

        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SoulSense Internal"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Certificate Authority"),
            x509.NameAttribute(NameOID.COMMON_NAME, "SoulSense Internal CA"),
        ])

        # CA certificate valid for 10 years
        ca_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.ca_private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(UTC)
        ).not_valid_after(
            datetime.now(UTC) + timedelta(days=3650)  # 10 years
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(self.ca_private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(self.ca_private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_encipherment=False,
                non_repudiation=False,
                digital_signature=True,
                content_commitment=False,
            ),
            critical=True,
        ).sign(self.ca_private_key, hashes.SHA256(), default_backend())

        # Save CA certificate and private key
        with open(self.ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

        with open(self.ca_key_path, "wb") as f:
            f.write(self.ca_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Initialize serial number
        with open(self.serial_file, "w") as f:
            f.write("1000\n")

        logger.info(f"CA certificate created: {self.ca_cert_path}")

    def _load_ca(self):
        """Load existing CA certificate and private key."""
        # Load CA certificate
        with open(self.ca_cert_path, "rb") as f:
            ca_cert_data = f.read()
        self.ca_cert = x509.load_pem_x509_certificate(ca_cert_data, default_backend())

        # Load CA private key
        with open(self.ca_key_path, "rb") as f:
            ca_key_data = f.read()
        self.ca_private_key = serialization.load_pem_private_key(
            ca_key_data, password=None, backend=default_backend()
        )

    def get_next_serial(self) -> int:
        """Get next certificate serial number."""
        if not self.serial_file.exists():
            serial = 1000
        else:
            with open(self.serial_file, "r") as f:
                serial = int(f.read().strip())
            serial += 1

        with open(self.serial_file, "w") as f:
            f.write(f"{serial}\n")

        return serial

    def issue_certificate(
        self,
        service_name: str,
        common_name: str,
        dns_names: List[str] = None,
        ip_addresses: List[str] = None,
        validity_days: int = 365
    ) -> Tuple[str, str, str]:
        """
        Issue a new certificate for a service.

        Args:
            service_name: Name of the service (used for file naming)
            common_name: Certificate common name
            dns_names: List of DNS names for SAN extension
            ip_addresses: List of IP addresses for SAN extension
            validity_days: Certificate validity period

        Returns:
            Tuple of (cert_pem, key_pem, cert_path)
        """
        # Generate service private key
        service_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,  # Smaller key for services
            backend=default_backend()
        )

        # Create certificate subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SoulSense Internal"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, service_name),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        # Build SAN extension
        san_names = []
        if dns_names:
            san_names.extend([x509.DNSName(name) for name in dns_names])
        if ip_addresses:
            san_names.extend([x509.IPAddress(ip) for ip in ip_addresses])

        # Certificate builder
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            self.ca_cert.subject
        ).public_key(
            service_private_key.public_key()
        ).serial_number(
            self.get_next_serial()
        ).not_valid_before(
            datetime.now(UTC)
        ).not_valid_after(
            datetime.now(UTC) + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(service_private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(self.ca_private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
                content_commitment=False,
                non_repudiation=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtensionOID.CLIENT_AUTH,
                x509.oid.ExtensionOID.SERVER_AUTH,
            ]),
            critical=False,
        )

        # Add SAN extension if names provided
        if san_names:
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName(san_names),
                critical=False,
            )

        # Sign certificate
        certificate = cert_builder.sign(self.ca_private_key, hashes.SHA256(), default_backend())

        # Convert to PEM format
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        key_pem = service_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Save certificate and key
        service_dir = self.ca_dir / service_name
        service_dir.mkdir(exist_ok=True)

        cert_path = service_dir / f"{service_name}.crt"
        key_path = service_dir / f"{service_name}.key"

        with open(cert_path, "w") as f:
            f.write(cert_pem)

        with open(key_path, "w") as f:
            f.write(key_pem)

        logger.info(f"Certificate issued for service {service_name}: {cert_path}")

        return cert_pem, key_pem, str(cert_path)

    def get_ca_certificate(self) -> str:
        """Get CA certificate in PEM format."""
        with open(self.ca_cert_path, "r") as f:
            return f.read()

    def revoke_certificate(self, serial_number: int):
        """Revoke a certificate (placeholder for CRL implementation)."""
        logger.warning(f"Certificate revocation not yet implemented. Serial: {serial_number}")

    def list_certificates(self) -> List[Dict[str, Any]]:
        """List all issued certificates."""
        certificates = []

        for service_dir in self.ca_dir.iterdir():
            if service_dir.is_dir() and service_dir.name != "ca":
                cert_path = service_dir / f"{service_dir.name}.crt"
                if cert_path.exists():
                    try:
                        with open(cert_path, "rb") as f:
                            cert_data = f.read()
                        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

                        certificates.append({
                            "service_name": service_dir.name,
                            "serial_number": cert.serial_number,
                            "subject": cert.subject.rfc4514_string(),
                            "not_before": cert.not_valid_before.isoformat(),
                            "not_after": cert.not_valid_after.isoformat(),
                            "is_expired": cert.not_valid_after < datetime.now(UTC),
                        })
                    except Exception as e:
                        logger.error(f"Error reading certificate {cert_path}: {e}")

        return certificates


class MTLSCertificateManager:
    """
    Manages mTLS certificates for internal services.

    Handles certificate lifecycle, rotation, and validation.
    """

    def __init__(self, certs_dir: str = "certs"):
        self.certs_dir = Path(certs_dir)
        self.ca = CertificateAuthority(ca_dir=str(self.certs_dir / "ca"))
        self.services_file = self.certs_dir / "services.json"

        # Load service configurations
        self.services = self._load_services()

    def _load_services(self) -> Dict[str, Dict[str, Any]]:
        """Load service configurations."""
        if self.services_file.exists():
            with open(self.services_file, "r") as f:
                return json.load(f)
        return {}

    def _save_services(self):
        """Save service configurations."""
        with open(self.services_file, "w") as f:
            json.dump(self.services, f, indent=2)

    def register_service(
        self,
        service_name: str,
        common_name: str,
        dns_names: List[str] = None,
        ip_addresses: List[str] = None,
        ports: List[int] = None
    ):
        """
        Register a new service for mTLS.

        Args:
            service_name: Unique service identifier
            common_name: Certificate common name
            dns_names: Service DNS names
            ip_addresses: Service IP addresses
            ports: Service ports (for validation)
        """
        if service_name in self.services:
            logger.warning(f"Service {service_name} already registered")
            return

        # Issue certificate for service
        cert_pem, key_pem, cert_path = self.ca.issue_certificate(
            service_name=service_name,
            common_name=common_name,
            dns_names=dns_names,
            ip_addresses=ip_addresses
        )

        # Store service configuration
        self.services[service_name] = {
            "common_name": common_name,
            "dns_names": dns_names or [],
            "ip_addresses": ip_addresses or [],
            "ports": ports or [],
            "cert_path": cert_path,
            "issued_at": datetime.now(UTC).isoformat(),
            "status": "active"
        }

        self._save_services()
        logger.info(f"Service {service_name} registered with mTLS certificate")

    def get_service_certificate(self, service_name: str) -> Optional[Dict[str, str]]:
        """Get certificate and key for a service."""
        if service_name not in self.services:
            return None

        service_config = self.services[service_name]
        cert_path = Path(service_config["cert_path"])
        key_path = cert_path.with_suffix('.key')

        if not cert_path.exists() or not key_path.exists():
            logger.error(f"Certificate files missing for service {service_name}")
            return None

        with open(cert_path, "r") as f:
            cert_pem = f.read()

        with open(key_path, "r") as f:
            key_pem = f.read()

        return {
            "certificate": cert_pem,
            "private_key": key_pem,
            "ca_certificate": self.ca.get_ca_certificate()
        }

    def rotate_certificate(self, service_name: str) -> bool:
        """
        Rotate certificate for a service.

        Returns True if rotation was successful.
        """
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found")
            return False

        service_config = self.services[service_name]

        try:
            # Issue new certificate
            cert_pem, key_pem, cert_path = self.ca.issue_certificate(
                service_name=service_name,
                common_name=service_config["common_name"],
                dns_names=service_config["dns_names"],
                ip_addresses=service_config["ip_addresses"]
            )

            # Update service configuration
            service_config["cert_path"] = cert_path
            service_config["issued_at"] = datetime.now(UTC).isoformat()
            service_config["rotated_at"] = datetime.now(UTC).isoformat()

            self._save_services()
            logger.info(f"Certificate rotated for service {service_name}")
            return True

        except Exception as e:
            logger.error(f"Certificate rotation failed for {service_name}: {e}")
            return False

    def validate_certificate(self, service_name: str, certificate_pem: str) -> bool:
        """
        Validate a certificate against the CA.

        Returns True if certificate is valid and issued by our CA.
        """
        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode('utf-8'),
                default_backend()
            )

            # Check if issued by our CA
            if cert.issuer != self.ca.ca_cert.subject:
                logger.warning(f"Certificate not issued by our CA for service {service_name}")
                return False

            # Check expiration
            now = datetime.now(UTC)
            if cert.not_valid_before > now or cert.not_valid_after < now:
                logger.warning(f"Certificate expired or not yet valid for service {service_name}")
                return False

            # Check service name matches
            if service_name not in self.services:
                logger.warning(f"Unknown service {service_name}")
                return False

            service_config = self.services[service_name]
            expected_cn = service_config["common_name"]

            # Check common name
            cn_attr = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            if not cn_attr or cn_attr[0].value != expected_cn:
                logger.warning(f"Common name mismatch for service {service_name}")
                return False

            return True

        except Exception as e:
            logger.error(f"Certificate validation failed for {service_name}: {e}")
            return False

    def get_ca_certificate(self) -> str:
        """Get CA certificate for client validation."""
        return self.ca.get_ca_certificate()

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services with their status."""
        services = []
        for name, config in self.services.items():
            cert_path = Path(config["cert_path"])
            cert_exists = cert_path.exists()
            key_exists = cert_path.with_suffix('.key').exists()

            services.append({
                "service_name": name,
                "common_name": config["common_name"],
                "status": config["status"],
                "issued_at": config["issued_at"],
                "cert_exists": cert_exists,
                "key_exists": key_exists,
                "dns_names": config["dns_names"],
                "ip_addresses": config["ip_addresses"],
            })

        return services

    def cleanup_expired_certificates(self, days_old: int = 30):
        """Clean up old certificate files."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        for service_name, service_config in self.services.items():
            rotated_at = service_config.get("rotated_at")
            if rotated_at:
                rotated_date = datetime.fromisoformat(rotated_at)
                if rotated_date < cutoff_date:
                    # Remove old certificate files
                    cert_path = Path(service_config["cert_path"])
                    old_cert = cert_path.parent / f"{service_name}_old.crt"
                    old_key = cert_path.parent / f"{service_name}_old.key"

                    if old_cert.exists():
                        old_cert.unlink()
                        logger.info(f"Cleaned up old certificate: {old_cert}")

                    if old_key.exists():
                        old_key.unlink()
                        logger.info(f"Cleaned up old key: {old_key}")


# Global certificate manager instance
_cert_manager: Optional[MTLSCertificateManager] = None


def get_cert_manager() -> MTLSCertificateManager:
    """Get or create certificate manager instance."""
    global _cert_manager
    if _cert_manager is None:
        _cert_manager = MTLSCertificateManager()
    return _cert_manager</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\backend\fastapi\api\services\mtls_certificate_manager.py