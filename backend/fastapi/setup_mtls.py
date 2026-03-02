#!/usr/bin/env python3
"""
mTLS Setup Script (#1253)

Initialize mutual TLS authentication for internal services:
- Create Certificate Authority
- Register services
- Generate service certificates
- Configure mTLS middleware
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add the api directory to the path
sys.path.insert(0, str(Path(__file__).parent / "api"))

from api.services.mtls_certificate_manager import MTLSCertificateManager
from api.config.mtls_config import (
    MTLSConfig,
    ServiceConfig,
    load_mtls_config,
    save_mtls_config,
    register_service_in_config,
    setup_mtls_directories
)


def create_ca(manager: MTLSCertificateManager) -> bool:
    """Create Certificate Authority."""
    print("Creating Certificate Authority...")
    try:
        manager.ca.create_ca_certificate()
        print("✓ Certificate Authority created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create Certificate Authority: {e}")
        return False


def register_services(manager: MTLSCertificateManager, services: List[Dict[str, Any]]) -> bool:
    """Register services with the certificate manager."""
    print(f"Registering {len(services)} services...")
    success_count = 0

    for service_data in services:
        try:
            service_config = ServiceConfig(**service_data)
            manager.register_service(service_config)
            print(f"✓ Registered service: {service_config.name}")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to register service {service_data.get('name', 'unknown')}: {e}")

    print(f"Registered {success_count}/{len(services)} services")
    return success_count == len(services)


def generate_certificates(manager: MTLSCertificateManager, service_names: List[str]) -> bool:
    """Generate certificates for registered services."""
    print(f"Generating certificates for {len(service_names)} services...")
    success_count = 0

    for service_name in service_names:
        try:
            cert_data = manager.generate_service_certificate(service_name)
            if cert_data:
                print(f"✓ Generated certificate for service: {service_name}")
                success_count += 1
            else:
                print(f"✗ Failed to generate certificate for service: {service_name}")
        except Exception as e:
            print(f"✗ Error generating certificate for {service_name}: {e}")

    print(f"Generated certificates for {success_count}/{len(service_names)} services")
    return success_count == len(service_names)


def validate_setup(manager: MTLSCertificateManager, service_names: List[str]) -> bool:
    """Validate the mTLS setup."""
    print("Validating mTLS setup...")
    success_count = 0

    for service_name in service_names:
        try:
            cert_data = manager.get_service_certificate(service_name)
            if cert_data and manager.validate_certificate(service_name, cert_data["certificate"]):
                print(f"✓ Service {service_name} certificate is valid")
                success_count += 1
            else:
                print(f"✗ Service {service_name} certificate validation failed")
        except Exception as e:
            print(f"✗ Error validating service {service_name}: {e}")

    print(f"Validated {success_count}/{len(service_names)} services")
    return success_count == len(service_names)


def create_default_services() -> List[Dict[str, Any]]:
    """Create default service configurations."""
    return [
        {
            "name": "api-gateway",
            "dns_names": ["api-gateway.local", "api-gateway.soul-sense.internal"],
            "ip_addresses": ["127.0.0.1", "10.0.0.10"],
            "ports": [443, 8443],
            "description": "API Gateway service"
        },
        {
            "name": "nlp-service",
            "dns_names": ["nlp-service.local", "nlp-service.soul-sense.internal"],
            "ip_addresses": ["127.0.0.1", "10.0.0.11"],
            "ports": [443, 8443],
            "description": "NLP processing service"
        },
        {
            "name": "email-service",
            "dns_names": ["email-service.local", "email-service.soul-sense.internal"],
            "ip_addresses": ["127.0.0.1", "10.0.0.12"],
            "ports": [443, 8443],
            "description": "Email notification service"
        },
        {
            "name": "github-service",
            "dns_names": ["github-service.local", "github-service.soul-sense.internal"],
            "ip_addresses": ["127.0.0.1", "10.0.0.13"],
            "ports": [443, 8443],
            "description": "GitHub integration service"
        },
        {
            "name": "auth-service",
            "dns_names": ["auth-service.local", "auth-service.soul-sense.internal"],
            "ip_addresses": ["127.0.0.1", "10.0.0.14"],
            "ports": [443, 8443],
            "description": "Authentication service"
        }
    ]


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="mTLS Setup for Internal Services")
    parser.add_argument(
        "--config",
        default="mtls_config.json",
        help="Path to mTLS configuration file"
    )
    parser.add_argument(
        "--services-config",
        help="Path to services configuration JSON file"
    )
    parser.add_argument(
        "--certs-dir",
        default="certs",
        help="Directory for storing certificates"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of CA and certificates"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing setup"
    )
    parser.add_argument(
        "--services",
        nargs="*",
        help="Specific services to set up (default: all)"
    )

    args = parser.parse_args()

    # Load or create configuration
    try:
        config = load_mtls_config(args.config)
        print(f"Loaded configuration from {args.config}")
    except Exception as e:
        print(f"Creating new configuration: {e}")
        config = MTLSConfig()

    # Override certs directory if specified
    if args.certs_dir:
        config.certs_dir = args.certs_dir
        config.ca_dir = str(Path(args.certs_dir) / "ca")
        config.services_dir = str(Path(args.certs_dir) / "services")

    # Create certificate manager
    manager = MTLSCertificateManager(config)

    # Load services configuration
    if args.services_config:
        try:
            with open(args.services_config, 'r') as f:
                services_data = json.load(f)
            services = [ServiceConfig(**s) for s in services_data]
        except Exception as e:
            print(f"Failed to load services config: {e}")
            return 1
    else:
        services = create_default_services()

    # Convert to dict format for registration
    services_dict = [s.dict() for s in services]

    # Filter services if specified
    if args.services:
        services_dict = [s for s in services_dict if s["name"] in args.services]
        if not services_dict:
            print(f"No matching services found for: {args.services}")
            return 1

    service_names = [s["name"] for s in services_dict]

    # Validate only mode
    if args.validate_only:
        print("Validating existing mTLS setup...")
        if validate_setup(manager, service_names):
            print("✓ mTLS setup validation successful")
            return 0
        else:
            print("✗ mTLS setup validation failed")
            return 1

    # Setup directories
    print("Setting up certificate directories...")
    setup_mtls_directories(config)

    # Create CA if it doesn't exist or force recreation
    ca_exists = Path(config.ca_dir) / "ca.crt"
    if not ca_exists.exists() or args.force:
        if not create_ca(manager):
            return 1
    else:
        print("Certificate Authority already exists, skipping creation")

    # Register services
    if not register_services(manager, services_dict):
        return 1

    # Generate certificates
    if not generate_certificates(manager, service_names):
        return 1

    # Validate setup
    if not validate_setup(manager, service_names):
        return 1

    # Save configuration
    try:
        save_mtls_config(config, args.config)
        print(f"✓ Configuration saved to {args.config}")
    except Exception as e:
        print(f"✗ Failed to save configuration: {e}")
        return 1

    print("\n🎉 mTLS setup completed successfully!")
    print(f"Certificates stored in: {config.certs_dir}")
    print(f"Configuration saved to: {args.config}")
    print("\nNext steps:")
    print("1. Configure your FastAPI applications with mTLS middleware")
    print("2. Update service clients to use mTLS certificates")
    print("3. Deploy certificates to production environments")
    print("4. Test mTLS authentication between services")

    return 0


if __name__ == "__main__":
    sys.exit(main())