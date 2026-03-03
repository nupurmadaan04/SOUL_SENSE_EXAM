# Pull Request: Add Payload Size Limits and DoS Protection (Issue #1068)

## Summary

This PR implements comprehensive payload size limits and DoS (Denial of Service) protection to prevent backend crashes due to oversized or malformed payloads. It addresses Issue #1068 by enforcing configurable limits on request body size, JSON nesting depth, array/object sizes, and detecting compression bombs.

## Problem Statement

Large JSON or deeply nested payloads may exhaust server memory, leading to:
- Denial of Service attacks
- Application crashes
- Resource exhaustion
- Potential security vulnerabilities

## Solution

Implemented a multi-layered protection system with the following features:

### 1. Request Body Size Limits
- **Max Request Size**: Configurable maximum (default: 10MB)
- **Content-Length Validation**: Early rejection based on Content-Length header
- **Streaming Validation**: Real-time size checking during body read

### 2. JSON Payload Validation
- **Nesting Depth**: Maximum JSON nesting depth (default: 20 levels)
- **Array Size**: Maximum elements in JSON arrays (default: 10,000)
- **Object Keys**: Maximum keys in JSON objects (default: 1,000)

### 3. Compression Bomb Detection
- **Gzip Detection**: Identifies gzip compression bombs
- **Zip Detection**: Identifies zip archive bombs
- **Ratio Threshold**: Configurable compression ratio (default: 10:1)

### 4. Multipart Form Validation
- **Part Limits**: Maximum number of parts (default: 100)
- **File Size**: Maximum file upload size (default: 50MB)

## Changes Made

### New Files

| File | Purpose |
|------|---------|
| `backend/fastapi/api/utils/payload_validator.py` | Core validation utilities |
| `backend/fastapi/api/middleware/payload_limit_middleware.py` | FastAPI middleware implementation |
| `backend/fastapi/tests/unit/test_payload_limits_1068.py` | Unit tests (54 tests) |
| `backend/fastapi/tests/unit/test_payload_limit_middleware_1068.py` | Integration tests (16 tests) |
| `PAYLOAD_SIZE_LIMITS_1068.md` | Complete documentation |

### Modified Files

| File | Changes |
|------|---------|
| `backend/fastapi/api/config.py` | Added 8 payload limit configuration settings |
| `backend/fastapi/api/constants/errors.py` | Added 5 DoS error codes (DOS001-DOS005) |
| `backend/fastapi/api/exceptions.py` | Added PayloadSizeException exception classes |
| `backend/fastapi/api/main.py` | Integrated PayloadLimitMiddleware into app |

## Configuration

### Environment Variables

```bash
# Request size limits
MAX_REQUEST_SIZE_BYTES=10485760          # 10MB default
MAX_JSON_DEPTH=20                         # Max nesting depth
MAX_ARRAY_SIZE=10000                      # Max array elements
MAX_OBJECT_KEYS=1000                      # Max object keys

# Multipart limits
MAX_MULTIPART_PARTS=100                   # Max form parts
MAX_MULTIPART_FILE_SIZE_BYTES=52428800    # 50MB default

# Compression bomb detection
ENABLE_COMPRESSION_BOMB_CHECK=true        # Enable/disable
COMPRESSION_BOMB_RATIO=10.0               # Compression ratio threshold
```

### Programmatic Access

```python
from api.config import get_settings_instance

settings = get_settings_instance()
print(settings.max_request_size_bytes)  # 10485760
print(settings.max_json_depth)          # 20
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

## Testing

### Automated Tests

```bash
# Run all tests
cd backend/fastapi
pytest tests/unit/test_payload_limits_1068.py tests/unit/test_payload_limit_middleware_1068.py -v

# Results: 70/70 tests passing
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

### Manual Testing

#### Test 1: Small Payload (Should Pass)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"SecurePass123!"}'
# Expected: 200 or 201
```

#### Test 2: Oversized Payload (Should Fail)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"data": "'$(python -c "print('x'*20000000)")'"}'
# Expected: 413 Payload Too Large
```

#### Test 3: Deeply Nested JSON (Should Fail)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"l1":{"l2":{"l3":{"l4":{"l5":{"l6":{"l7":{"l8":{"l9":{"l10":{"l11":{"l12":{"l13":{"l14":{"l15":{"l16":{"l17":{"l18":{"l19":{"l20":{"l21":"deep"}}}}}}}}}}}}}}}}}}}}}'
# Expected: 413 Payload Too Large
```

## Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| 50MB JSON body | Rejected by size limit before parsing |
| Deep nested arrays | Rejected by depth validation |
| Compression bombs | Detected via ratio analysis |
| Multipart abuse | Limited by part count |
| Malformed payloads | Caught by validation error handlers |
| Circular references | Cannot exist in JSON (would fail parsing) |
| Unicode in JSON | Handled correctly |
| Binary data | Base64 encoded validation |

## Performance Impact

- **Minimal overhead** for valid requests
- **Early rejection** prevents resource exhaustion
- **Streaming validation** avoids memory spikes
- **Excluded paths** have zero overhead
- **Non-blocking** for legitimate traffic

## Security Considerations

- Middleware runs as outermost layer to block attacks early
- All violations are logged with request ID for tracing
- Graceful error responses don't leak system information
- Configurable limits allow environment-specific tuning
- No impact on legitimate users within limits

## Checklist

- [x] Code follows project style guidelines
- [x] Self-review completed
- [x] Comments added for complex logic
- [x] Documentation updated (`PAYLOAD_SIZE_LIMITS_1068.md`)
- [x] Tests added (70 tests, all passing)
- [x] Edge cases handled
- [x] Error codes follow existing convention
- [x] No breaking changes to existing API
- [x] Configuration is backward compatible
- [x] Logging added for security events

## Related Issues

- Closes #1068

## Screenshots/Logs

Example log output:
```
WARNING:api.payload_limit:Request body exceeded size limit: 15728640 bytes (max: 10485760 bytes) [request_id=abc-123 path=/api/v1/upload]

WARNING:api.payload_limit:JSON nesting depth exceeded: 21 (max: 20) [request_id=def-456 path=/api/v1/data]

WARNING:api.payload_limit:Compression bomb detected: ratio 50.0:1 (threshold: 10:1) [request_id=ghi-789 path=/api/v1/import]
```

## Deployment Notes

1. No database migrations required
2. Configuration can be adjusted via environment variables
3. Monitor logs after deployment for false positives
4. Consider adjusting limits based on production traffic patterns

## Future Enhancements (Out of Scope)

- Rate limiting integration for comprehensive DoS protection
- IP-based graduated limits
- Prometheus metrics for payload violations
- ML-based anomaly detection for unusual patterns
- Admin dashboard for monitoring violations

---

**Reviewer Notes:**
- Please verify the default limits are appropriate for the production environment
- Consider if any endpoints need custom (higher) limits for file uploads
- Review error messages for clarity and security (no information leakage)
