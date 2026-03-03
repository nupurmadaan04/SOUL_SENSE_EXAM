# Payload Size Limits and DoS Protection (Issue #1068)

## Overview

This implementation adds comprehensive payload size limits and DoS (Denial of Service) protection to the SoulSense API. It prevents backend crashes due to oversized or malformed payloads by enforcing configurable limits on request body size, JSON nesting depth, array/object sizes, and detecting compression bombs.

## Table of Contents

- [Features](#features)
- [Configuration](#configuration)
- [Error Codes](#error-codes)
- [Implementation Details](#implementation-details)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Security Considerations](#security-considerations)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

## Features

### 1. Request Body Size Limits
- **Max Request Size**: Configurable maximum request body size (default: 10MB)
- **Content-Length Validation**: Early rejection based on Content-Length header
- **Streaming Validation**: Real-time size checking during body read

### 2. JSON Payload Validation
- **Nesting Depth**: Maximum JSON nesting depth (default: 20 levels)
- **Array Size**: Maximum elements in JSON arrays (default: 10,000)
- **Object Keys**: Maximum keys in JSON objects (default: 1,000)
- **Structure Validation**: Comprehensive structural integrity checks

### 3. Compression Bomb Detection
- **Gzip Detection**: Identifies gzip compression bombs
- **Zip Detection**: Identifies zip archive bombs
- **Ratio Threshold**: Configurable compression ratio threshold (default: 10:1)
- **Size Limits**: Maximum uncompressed size checks

### 4. Multipart Form Validation
- **Part Limits**: Maximum number of parts in multipart requests (default: 100)
- **File Size**: Maximum file upload size (default: 50MB)
- **Boundary Validation**: Proper multipart boundary checking

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_REQUEST_SIZE_BYTES` | 10485760 (10MB) | Maximum request body size |
| `MAX_JSON_DEPTH` | 20 | Maximum JSON nesting depth |
| `MAX_MULTIPART_PARTS` | 100 | Maximum multipart parts |
| `MAX_MULTIPART_FILE_SIZE_BYTES` | 52428800 (50MB) | Maximum file upload size |
| `MAX_ARRAY_SIZE` | 10000 | Maximum JSON array elements |
| `MAX_OBJECT_KEYS` | 1000 | Maximum JSON object keys |
| `ENABLE_COMPRESSION_BOMB_CHECK` | true | Enable compression bomb detection |
| `COMPRESSION_BOMB_RATIO` | 10.0 | Compression ratio threshold |

### Programmatic Configuration

Configuration is handled through the Pydantic settings in `backend/fastapi/api/config.py`:

```python
from api.config import get_settings_instance

settings = get_settings_instance()
print(f"Max request size: {settings.max_request_size_bytes} bytes")
print(f"Max JSON depth: {settings.max_json_depth}")
```

### Customizing Limits

To customize limits for your deployment, set environment variables:

```bash
# .env file
MAX_REQUEST_SIZE_BYTES=20971520      # 20MB
MAX_JSON_DEPTH=25                     # 25 levels
MAX_ARRAY_SIZE=50000                  # 50k elements
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `DOS001` | Payload too large | 413 |
| `DOS002` | JSON depth exceeded | 413 |
| `DOS003` | Malformed payload | 400 |
| `DOS004` | Compression bomb detected | 413 |
| `DOS005` | Too many multipart parts | 413 |

## Error Response Format

```json
{
  "code": "DOS001",
  "message": "Request body too large: 15728640 bytes (max: 10485760 bytes)",
  "details": {
    "size_bytes": 15728640,
    "max_size_bytes": 10485760,
    "size_mb": 15.0,
    "max_size_mb": 10.0
  }
}
```

## Implementation Details

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PayloadLimitMiddleware                    │
├─────────────────────────────────────────────────────────────┤
│  1. Path Exclusion Check                                      │
│     └─ Skip health checks, docs, static files               │
│                                                               │
│  2. Content-Length Check                                      │
│     └─ Validate header before reading body                  │
│                                                               │
│  3. Body Read with Limit                                      │
│     └─ Stream body with real-time size checking             │
│                                                               │
│  4. Content-Type Validation                                   │
│     └─ Apply specific validation based on content type      │
│                                                               │
│  5. Structure Validation                                      │
│     └─ Validate JSON/array/object structure                 │
│                                                               │
│  6. Bomb Detection                                            │
│     └─ Check for compression bombs                          │
└─────────────────────────────────────────────────────────────┘
```

### Middleware Integration

The `PayloadLimitMiddleware` is added as the outermost middleware in the FastAPI application stack:

```python
# In backend/fastapi/api/main.py
from .middleware.payload_limit_middleware import PayloadLimitMiddleware
app.add_middleware(PayloadLimitMiddleware)
```

### Excluded Paths

The following paths are excluded from payload validation:
- `/health`, `/healthz`, `/ready`, `/alive`, `/metrics`
- `/favicon.ico`
- `/docs`, `/redoc`, `/openapi.json`
- `/static/` (static files)

## Usage Examples

### Valid Request

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'
```

Response: `200 OK`

### Oversized Payload

```bash
# Create large payload
python3 -c "print('{\"data\": \"' + 'x'*20000000 + '\"}')" > /tmp/large.json

curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d @/tmp/large.json
```

Response: `413 Payload Too Large`
```json
{
  "code": "DOS001",
  "message": "Request body too large: 20000015 bytes (max: 10485760 bytes)",
  "details": {
    "size_bytes": 20000015,
    "max_size_bytes": 10485760,
    "size_mb": 19.07,
    "max_size_mb": 10.0
  }
}
```

### Deeply Nested JSON

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{"l1":{"l2":{"l3":{"l4":{"l5":{"l6":{"l7":{"l8":{"l9":{"l10":{"l11":{"l12":{"l13":{"l14":{"l15":{"l16":{"l17":{"l18":{"l19":{"l20":{"l21":"deep"}}}}}}}}}}}}}}}}}}}}}'
```

Response: `413 Payload Too Large`
```json
{
  "code": "DOS002",
  "message": "JSON nesting depth exceeded: 21 (max: 20)",
  "details": {
    "depth": 21,
    "max_depth": 20
  }
}
```

### Large Array

```bash
curl -X POST "http://localhost:8000/api/v1/users" \
  -H "Content-Type: application/json" \
  -d '{"items": ['$(python3 -c "print(','.join([str(i) for i in range(15000)]))")']}'
```

Response: `400 Bad Request`
```json
{
  "code": "DOS003",
  "message": "Payload structure violation: Array has too many elements: 15000 (max: 10000)",
  "details": {
    "elements": 15000,
    "max_elements": 10000
  }
}
```

## Testing

### Automated Tests

```bash
cd backend/fastapi

# Run all payload limit tests
pytest tests/unit/test_payload_limits_1068.py tests/unit/test_payload_limit_middleware_1068.py -v

# Run with coverage
pytest tests/unit/test_payload_limits_1068.py tests/unit/test_payload_limit_middleware_1068.py \
  --cov=api.utils.payload_validator --cov=api.middleware.payload_limit_middleware -v

# Expected: 70/70 tests passing
```

### Manual Testing Script

```python
#!/usr/bin/env python3
"""Quick test script for payload limits."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_small_payload():
    """Test 1: Small payload should pass."""
    print("Test 1: Small payload...")
    resp = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    print(f"  Status: {resp.status_code}")
    assert resp.status_code in [200, 201, 422, 409]
    print("  ✓ PASSED")

def test_oversized_payload():
    """Test 2: Oversized payload should fail."""
    print("Test 2: Oversized payload (20MB)...")
    resp = requests.post(f"{BASE_URL}/api/v1/auth/register", 
        json={"data": "x" * 20000000})
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 413
    data = resp.json()
    assert data["code"] == "DOS001"
    print("  ✓ PASSED - Correctly rejected")

def test_deep_nesting():
    """Test 3: Deep nesting should fail."""
    print("Test 3: Deep nesting (50 levels)...")
    data = {}
    current = data
    for _ in range(50):
        current["nested"] = {}
        current = current["nested"]
    
    resp = requests.post(f"{BASE_URL}/api/v1/auth/register", json=data)
    print(f"  Status: {resp.status_code}")
    assert resp.status_code in [400, 413]
    print("  ✓ PASSED - Correctly rejected")

def test_health_excluded():
    """Test 4: Health check should pass."""
    print("Test 4: Health check (excluded path)...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {resp.status_code}")
    assert resp.status_code == 200
    print("  ✓ PASSED")

if __name__ == "__main__":
    test_small_payload()
    test_oversized_payload()
    test_deep_nesting()
    test_health_excluded()
    print("\nAll tests passed! ✓")
```

### Test Coverage

- ✅ Payload size validation (Content-Length and body)
- ✅ JSON depth calculation and validation
- ✅ Array size validation
- ✅ Object key count validation
- ✅ Gzip compression bomb detection
- ✅ Zip archive bomb detection
- ✅ Multipart form validation
- ✅ Error response structure
- ✅ Excluded paths (health, docs, static)
- ✅ Configuration loading
- ✅ Exception handling

## Security Considerations

### Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| 50MB JSON Body | Rejected by size limit before parsing |
| Deep Nested Arrays | Rejected by depth validation |
| Compression Bombs | Detected via ratio analysis |
| Multipart Abuse | Limited by part count |
| Malformed Payloads | Caught by validation error handlers |
| Circular References | Cannot exist in JSON (would fail parsing) |
| Unicode in JSON | Handled correctly |
| Binary Data in JSON | Base64 encoded validation |

### Performance Impact

- **Minimal overhead** for valid requests
- **Early rejection** prevents resource exhaustion
- **Streaming validation** avoids memory spikes
- **Excluded paths** have zero overhead
- **Non-blocking** for legitimate traffic

### Best Practices

1. **Monitor Logs**: Watch for repeated violations from same IPs
2. **Adjust Limits**: Tune based on legitimate use cases
3. **Rate Limiting**: Combine with rate limiting for comprehensive protection
4. **Testing**: Regularly test with fuzzing tools

## Monitoring and Logging

All payload violations are logged with:
- Request ID for tracing
- Violation type and details
- Client IP (if available)
- Request path

### Log Format

```
WARNING:api.payload_limit:{message} [request_id={id} path={path} ...]
```

### Example Log Entries

```
WARNING:api.payload_limit:Request body exceeded size limit: 15728640 bytes (max: 10485760 bytes) [request_id=abc-123 path=/api/v1/upload size_bytes=15728640 max_size_bytes=10485760]

WARNING:api.payload_limit:JSON nesting depth exceeded: 21 (max: 20) [request_id=def-456 path=/api/v1/data depth=21 max_depth=20]

WARNING:api.payload_limit:Compression bomb detected: ratio 50.0:1 (threshold: 10:1) [request_id=ghi-789 path=/api/v1/import compression_ratio=50.0 threshold=10.0]

WARNING:api.payload_limit:Payload validation error: Array has too many elements [request_id=jkl-012 path=/api/v1/bulk elements=15000 max_elements=10000]
```

## Troubleshooting

### Issue: Legitimate requests being rejected

**Solution**: Adjust limits in configuration:

```bash
# Increase limits for specific use cases
MAX_REQUEST_SIZE_BYTES=20971520  # 20MB
MAX_ARRAY_SIZE=50000             # 50k elements
```

### Issue: File uploads failing

**Solution**: Check multipart file size limit:

```bash
MAX_MULTIPART_FILE_SIZE_BYTES=104857600  # 100MB
```

### Issue: Complex nested data rejected

**Solution**: Increase JSON depth limit:

```bash
MAX_JSON_DEPTH=30  # 30 levels
```

### Issue: False positives on compression

**Solution**: Adjust compression ratio:

```bash
COMPRESSION_BOMB_RATIO=20.0  # More lenient
```

## Future Enhancements

Potential improvements for future iterations:

1. **Rate Limiting Integration**: Combine with rate limiting for comprehensive DoS protection
2. **IP-based Limits**: Different limits for authenticated vs unauthenticated users
3. **Graduated Responses**: Warnings before hard rejections
4. **Metrics**: Prometheus metrics for payload violations
5. **Machine Learning**: ML-based anomaly detection for unusual payload patterns
6. **Admin Dashboard**: Visual monitoring of violations and trends
7. **Custom Endpoint Limits**: Per-endpoint size limits via decorators

## References

- Issue: #1068
- [OWASP DoS Protection](https://owasp.org/www-community/attacks/Denial_of_Service)
- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)
- [RFC 7231 (HTTP/1.1)](https://tools.ietf.org/html/rfc7231)

## Changelog

### Version 1.0.0
- Initial implementation
- Payload size limits
- JSON depth validation
- Compression bomb detection
- Multipart validation
- Comprehensive test coverage (70 tests)

---

**Maintainers**: Please update this document when modifying payload limits or adding new protections.
