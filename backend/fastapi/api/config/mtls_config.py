"""
mTLS Configuration for Internal Services (#1253)

Configuration and setup for mutual TLS authentication between internal services.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MTLSConfig(BaseModel):
    """Configuration for mTLS setup."""

    # Certificate Authority settings
    ca_country: str = Field(default="US", description="CA certificate country")
    ca_state: str = Field(default="CA", description="CA certificate state")
    ca_locality: str = Field(default="San Francisco", description="CA certificate locality")
    ca_organization: str = Field(default="Soul Sense Internal", description="CA certificate organization")
    ca_common_name: str = Field(default="Soul Sense Internal CA", description="CA certificate common name")

    # Certificate settings
    cert_validity_days: int = Field(default=365, description="Certificate validity period in days")
    key_size: int = Field(default=2048, description="RSA key size for certificates")

    # Service configuration
    services: Dict[str, Dict] = Field(default_factory=dict, description="Registered services configuration")

    # Paths
    certs_dir: str = Field(default="certs", description="Directory for storing certificates")
    ca_dir: str = Field(default="certs/ca", description="CA certificates directory")
    services_dir: str = Field(default="certs/services", description="Service certificates directory")

    # mTLS middleware settings
    mtls_required_paths: List[str] = Field(
        default=["/api/internal", "/api/services"],
        description="URL paths requiring mTLS authentication"
    )
    mtls_exempt_paths: List[str] = Field(
        default=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
        description="URL paths exempt from mTLS"
    )

    # Certificate rotation settings
    rotation_check_interval: int = Field(default=86400, description="Certificate rotation check interval in seconds")
    rotation_warning_days: int = Field(default=30, description="Days before expiration to warn about rotation")
    auto_rotate: bool = Field(default=True, description="Automatically rotate certificates")

    # Security settings
    require_client_cert: bool = Field(default=True, description="Require client certificates for mTLS endpoints")
    verify_cert_chain: bool = Field(default=True, description="Verify certificate chain of trust")
    check_revocation: bool = Field(default=False, description="Check certificate revocation status")


class ServiceConfig(BaseModel):
    """Configuration for a registered service."""

    name: str = Field(..., description="Service name")
    dns_names: List[str] = Field(default_factory=list, description="DNS names for the service")
    ip_addresses: List[str] = Field(default_factory=list, description="IP addresses for the service")
    ports: List[int] = Field(default_factory=lambda: [443, 8443], description="Ports the service listens on")
    description: Optional[str] = Field(default=None, description="Service description")


def load_mtls_config(config_file: str = "mtls_config.json") -> MTLSConfig:
    """
    Load mTLS configuration from file.

    Args:
        config_file: Path to configuration file

    Returns:
        MTLSConfig instance
    """
    config_path = Path(config_file)

    if config_path.exists():
        import json
        with open(config_path, 'r') as f:
            data = json.load(f)
        return MTLSConfig(**data)
    else:
        # Create default configuration
        config = MTLSConfig()
        save_mtls_config(config, config_file)
        return config


def save_mtls_config(config: MTLSConfig, config_file: str = "mtls_config.json") -> None:
    """
    Save mTLS configuration to file.

    Args:
        config: MTLSConfig instance
        config_file: Path to save configuration
    """
    import json
    config_path = Path(config_file)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, 'w') as f:
        json.dump(config.dict(), f, indent=2)


def get_service_config(service_name: str, config: MTLSConfig) -> Optional[ServiceConfig]:
    """
    Get service configuration.

    Args:
        service_name: Name of the service
        config: MTLS configuration

    Returns:
        ServiceConfig instance or None if not found
    """
    service_data = config.services.get(service_name)
    if service_data:
        return ServiceConfig(**service_data)
    return None


def register_service_in_config(
    service_name: str,
    dns_names: List[str] = None,
    ip_addresses: List[str] = None,
    ports: List[int] = None,
    description: str = None,
    config_file: str = "mtls_config.json"
) -> None:
    """
    Register a service in the mTLS configuration.

    Args:
        service_name: Name of the service
        dns_names: DNS names for the service
        ip_addresses: IP addresses for the service
        ports: Ports the service listens on
        description: Service description
        config_file: Configuration file path
    """
    config = load_mtls_config(config_file)

    service_config = ServiceConfig(
        name=service_name,
        dns_names=dns_names or [],
        ip_addresses=ip_addresses or [],
        ports=ports or [443, 8443],
        description=description
    )

    config.services[service_name] = service_config.dict()
    save_mtls_config(config, config_file)


def get_mtls_enabled_services(config: MTLSConfig) -> List[str]:
    """
    Get list of services with mTLS enabled.

    Args:
        config: MTLS configuration

    Returns:
        List of service names
    """
    return list(config.services.keys())


def setup_mtls_directories(config: MTLSConfig) -> None:
    """
    Create necessary directories for mTLS certificates.

    Args:
        config: MTLS configuration
    """
    dirs = [
        Path(config.certs_dir),
        Path(config.ca_dir),
        Path(config.services_dir)
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)


# Default configuration instance
default_config = MTLSConfig()

# Environment variable overrides
if os.getenv("MTLS_CA_COUNTRY"):
    default_config.ca_country = os.getenv("MTLS_CA_COUNTRY")

if os.getenv("MTLS_CERT_VALIDITY_DAYS"):
    default_config.cert_validity_days = int(os.getenv("MTLS_CERT_VALIDITY_DAYS"))

if os.getenv("MTLS_CERTS_DIR"):
    default_config.certs_dir = os.getenv("MTLS_CERTS_DIR")

if os.getenv("MTLS_AUTO_ROTATE", "").lower() in ("false", "0", "no"):
    default_config.auto_rotate = False