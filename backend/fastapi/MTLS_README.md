# Mutual TLS Authentication Implementation (#1253)

This document describes the implementation of mutual TLS (mTLS) authentication for internal service-to-service communication in the Soul Sense application.

## Overview

Mutual TLS authentication ensures that both client and server verify each other's identity using X.509 certificates. This implementation provides:

- Internal Certificate Authority (CA) for issuing certificates
- Service certificate lifecycle management
- FastAPI middleware for mTLS validation
- Client library for mTLS HTTP requests
- Automated certificate rotation
- Comprehensive testing and validation

## Architecture

### Components

1. **Certificate Authority (CA)**: Internal CA for issuing and managing service certificates
2. **MTLS Certificate Manager**: Manages service registration and certificate lifecycle
3. **MTLS Middleware**: FastAPI middleware for validating client certificates
4. **MTLS Client**: HTTP client with mTLS support for internal service communication

### Certificate Structure

```
certs/
├── ca/
│   ├── ca.crt          # CA certificate
│   └── ca.key          # CA private key
└── services/
    ├── api-gateway/
    │   ├── cert.pem    # Service certificate
    │   └── key.pem     # Service private key
    └── nlp-service/
        ├── cert.pem
        └── key.pem
```

## Setup and Configuration

### Prerequisites

```bash
pip install cryptography fastapi uvicorn httpx pydantic
```

### Initial Setup

Run the setup script to initialize mTLS:

```bash
# Setup with default services
python setup_mtls.py

# Setup with custom configuration
python setup_mtls.py --config custom_mtls_config.json --certs-dir /path/to/certs

# Setup specific services only
python setup_mtls.py --services api-gateway nlp-service

# Validate existing setup
python setup_mtls.py --validate-only
```

### Service Registration

Services are registered with their network identifiers:

```python
from api.config.mtls_config import register_service_in_config

# Register a service
register_service_in_config(
    service_name="my-service",
    dns_names=["my-service.local", "my-service.internal"],
    ip_addresses=["10.0.0.1", "127.0.0.1"],
    ports=[443, 8443],
    description="My internal service"
)
```

## FastAPI Integration

### Adding mTLS Middleware

```python
from fastapi import FastAPI
from api.middleware.mtls_middleware import create_mtls_app

app = FastAPI(title="My Service")

# Add mTLS middleware
app = create_mtls_app(
    app,
    mtls_required_paths=["/api/internal", "/api/services"],
    exempt_paths=["/health", "/metrics", "/docs"]
)

@app.get("/api/internal/data")
async def get_internal_data(request: Request):
    # Access client certificate information
    cert_info = request.state.client_cert_info
    return {"data": "internal", "client": cert_info["service_name"]}
```

### Accessing Client Certificate Information

```python
from api.middleware.mtls_middleware import get_client_cert_info

@app.get("/api/secure")
async def secure_endpoint(request: Request):
    cert_info = get_client_cert_info(request)
    if cert_info:
        return {
            "message": f"Hello {cert_info['service_name']}",
            "cert_valid": True
        }
    return {"error": "No client certificate"}
```

## Service Client Usage

### Making mTLS Requests

```python
import asyncio
from api.middleware.mtls_middleware import MTLSClient

async def call_internal_service():
    # Create mTLS client
    client = MTLSClient("my-service", certs_dir="certs")

    # Make authenticated request
    response = await client.get("https://api-gateway.local/api/internal/data")
    return response

# Run the async function
result = asyncio.run(call_internal_service())
```

### Integration with Existing Clients

For services that need to communicate with mTLS endpoints:

```python
import httpx
from api.services.mtls_certificate_manager import get_cert_manager

class MTLSServiceClient:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.cert_manager = get_cert_manager()
        self.cert_data = self.cert_manager.get_service_certificate(service_name)

    async def get(self, url: str) -> dict:
        async with httpx.AsyncClient(
            cert=(self.cert_data["certificate"], self.cert_data["private_key"]),
            verify=self.cert_data["ca_certificate"]
        ) as client:
            response = await client.get(url)
            return response.json()
```

## Certificate Management

### Manual Certificate Operations

```python
from api.services.mtls_certificate_manager import get_cert_manager

manager = get_cert_manager()

# Get service certificate
cert_data = manager.get_service_certificate("my-service")

# Rotate certificate
new_cert = manager.rotate_certificate("my-service")

# Validate certificate
is_valid = manager.validate_certificate("my-service", cert_pem)
```

### Automated Rotation

Certificates can be automatically rotated based on configuration:

```python
from api.config.mtls_config import MTLSConfig

config = MTLSConfig(
    auto_rotate=True,
    rotation_warning_days=30,
    rotation_check_interval=86400  # Check daily
)
```

## Testing

### Running Tests

```bash
# Run all mTLS tests
pytest tests/test_mtls.py -v

# Run specific test class
pytest tests/test_mtls.py::TestCertificateAuthority -v

# Run integration tests
pytest tests/test_mtls.py::TestMTLSIntegration -v
```

### Manual Testing

Test mTLS endpoints:

```bash
# Test exempt endpoint (no cert required)
curl https://my-service.local/health

# Test mTLS endpoint (cert required) - will fail without cert
curl https://my-service.local/api/internal/data

# Test with client certificate
curl --cert certs/services/my-service/cert.pem \
     --key certs/services/my-service/key.pem \
     --cacert certs/ca/ca.crt \
     https://my-service.local/api/internal/data
```

## Deployment Guide

### Certificate Distribution

1. **Development Environment**:
   ```bash
   # Generate certificates for dev
   python setup_mtls.py --certs-dir certs/dev
   ```

2. **Staging Environment**:
   ```bash
   # Generate certificates for staging
   python setup_mtls.py --certs-dir certs/staging
   ```

3. **Production Environment**:
   ```bash
   # Generate certificates for production
   python setup_mtls.py --certs-dir certs/prod
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

# Copy certificates
COPY certs/ca/ca.crt /app/certs/ca/
COPY certs/services/my-service/ /app/certs/services/my-service/

# Set certificate environment
ENV MTLS_CERTS_DIR=/app/certs

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8443", "--ssl-keyfile", "/app/certs/services/my-service/key.pem", "--ssl-certfile", "/app/certs/services/my-service/cert.pem"]
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mtls-certificates
type: Opaque
data:
  ca.crt: <base64-encoded-ca-cert>
  service.crt: <base64-encoded-service-cert>
  service.key: <base64-encoded-service-key>

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    spec:
      containers:
      - name: app
        image: my-service:latest
        ports:
        - containerPort: 8443
        volumeMounts:
        - name: certs
          mountPath: /app/certs
          readOnly: true
      volumes:
      - name: certs
        secret:
          secretName: mtls-certificates
```

## Monitoring and Alerting

### Certificate Expiration Monitoring

```python
from api.services.mtls_certificate_manager import get_cert_manager
from datetime import datetime, timedelta

def check_certificate_expirations():
    manager = get_cert_manager()
    warning_days = 30

    for service_name in manager.services:
        cert_data = manager.get_service_certificate(service_name)
        if cert_data:
            cert = x509.load_pem_x509_certificate(
                cert_data["certificate"].encode(),
                default_backend()
            )

            days_until_expiry = (cert.not_valid_after - datetime.utcnow()).days

            if days_until_expiry <= warning_days:
                print(f"WARNING: Certificate for {service_name} expires in {days_until_expiry} days")
                # Send alert/notification
```

### mTLS Authentication Metrics

```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class MTLSMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Track mTLS authentication attempts
        if request.url.path.startswith("/api/internal"):
            cert_info = getattr(request.state, 'client_cert_info', None)
            if cert_info:
                # Record successful mTLS authentication
                print(f"mTLS auth success: {cert_info['service_name']}")
            else:
                # Record failed mTLS authentication
                print(f"mTLS auth failed: {request.client.host}")

        response = await call_next(request)
        return response
```

## Troubleshooting

### Common Issues

1. **Certificate Validation Failed**
   ```
   Error: Client certificate required
   ```
   - Check if client certificate is properly configured
   - Verify certificate is not expired
   - Ensure CA certificate is trusted

2. **SSL Handshake Failed**
   ```
   Error: [SSL: CERTIFICATE_VERIFY_FAILED]
   ```
   - Check CA certificate path
   - Verify certificate chain of trust
   - Ensure server certificate is valid

3. **Service Registration Failed**
   ```
   Error: Service already registered
   ```
   - Use different service name or update existing registration
   - Check configuration file for conflicts

### Debugging Commands

```bash
# Check certificate validity
openssl x509 -in certs/services/my-service/cert.pem -text -noout

# Verify certificate against CA
openssl verify -CAfile certs/ca/ca.crt certs/services/my-service/cert.pem

# Test mTLS connection
openssl s_client -connect my-service.local:8443 \
    -cert certs/services/client-service/cert.pem \
    -key certs/services/client-service/key.pem \
    -CAfile certs/ca/ca.crt
```

### Logs and Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable cryptography debug logs
import cryptography
cryptography.utils.CRYPTOGRAPHY_DEBUG = True
```

## Security Considerations

### Certificate Security

- Store private keys securely with restricted permissions (600)
- Rotate certificates regularly (recommended: 90 days)
- Use strong key sizes (minimum 2048-bit RSA)
- Implement certificate revocation checking

### Network Security

- Use TLS 1.3 for all mTLS connections
- Implement proper firewall rules
- Monitor for certificate-based attacks
- Regular security audits of certificate usage

### Operational Security

- Automate certificate rotation
- Implement monitoring and alerting
- Regular backup of CA private key (offline storage)
- Document certificate distribution procedures

## API Reference

### CertificateAuthority

- `create_ca_certificate()`: Create new CA certificate
- `load_ca_certificate()`: Load existing CA certificate
- `issue_certificate(service_name, dns_names, ip_addresses, validity_days)`: Issue service certificate

### MTLSCertificateManager

- `register_service(service_config)`: Register a service
- `generate_service_certificate(service_name)`: Generate certificate for service
- `validate_certificate(service_name, cert_pem)`: Validate service certificate
- `rotate_certificate(service_name)`: Rotate service certificate
- `get_service_certificate(service_name)`: Get service certificate data

### MTLSMiddleware

- Validates client certificates for protected endpoints
- Extracts certificate information for request processing
- Configurable exempt paths and required paths

### MTLSClient

- HTTP client with automatic mTLS certificate configuration
- Supports async HTTP requests
- Handles certificate loading and SSL context setup

## Future Enhancements

- Certificate revocation lists (CRL)
- Online Certificate Status Protocol (OCSP)
- Hardware Security Modules (HSM) integration
- Certificate transparency logging
- Automated certificate discovery
- Integration with external CAs (Let's Encrypt, AWS ACM)