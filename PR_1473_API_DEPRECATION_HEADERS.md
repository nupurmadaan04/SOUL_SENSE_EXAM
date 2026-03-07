# PR: API Deprecation Header Standardization

**Issue:** #1473  
**Branch:** `fix/api-deprecation-header-standardization-1473`

## Overview

This PR implements RFC-compliant API deprecation header standardization following RFC 8594. It provides standardized deprecation headers, sunset dates, and migration guidance for API versioning lifecycle management.

## Features Implemented

### RFC 8594 Compliant Headers
- **Deprecation**: `true` - Indicates the endpoint is deprecated
- **Sunset**: HTTP-date format - When endpoint will be removed
- **Link**: With `rel="successor-version"` - Migration path
- **API-Deprecated**: ISO timestamp - When deprecation started
- **API-Sunset**: ISO timestamp - Sunset date
- **API-Alternative**: Alternative endpoint URL

### Deprecation Lifecycle
- **4 Deprecation Statuses**: Active, Deprecated, Sunset, Removed
- **3 Severity Levels**: Info, Warning, Critical
- **4 API Version Statuses**: Stable, Maintenance, Deprecated, End-of-Life

### Management Features
- API version lifecycle tracking
- Deprecation notice management
- Deprecated field tracking
- Client notification system
- Acknowledgement tracking
- Middleware for automatic header injection

### API Endpoints (13 endpoints)

**API Version Management:**
- `POST /api-deprecation/versions` - Register version (Admin only)
- `GET /api-deprecation/versions` - List versions
- `GET /api-deprecation/versions/{version}` - Get version
- `POST /api-deprecation/versions/{version}/deprecate` - Deprecate version (Admin only)

**Deprecation Notices:**
- `POST /api-deprecation/notices` - Create notice (Admin only)
- `GET /api-deprecation/notices` - List notices
- `GET /api-deprecation/notices/{notice_id}` - Get notice

**Header Generation:**
- `GET /api-deprecation/headers` - Get headers for endpoint

**Field Tracking:**
- `POST /api-deprecation/fields` - Register deprecated field (Admin only)
- `GET /api-deprecation/fields/{endpoint_path}` - Get deprecated fields

**Client Management:**
- `POST /api-deprecation/notifications` - Record client notification (Admin only)
- `POST /api-deprecation/acknowledgements` - Client acknowledgement

**Analytics:**
- `GET /api-deprecation/statistics` - Get statistics
- `GET /api-deprecation/health` - Health check

## Implementation Details

### RFC 8594 Header Format
```http
Deprecation: true
Sunset: Sat, 01 Jun 2025 00:00:00 GMT
Link: </api/v2/users>; rel="successor-version", </docs/migration>; rel="migration-guide"
API-Deprecated: 2025-01-01T00:00:00
API-Sunset: 2025-06-01T00:00:00
API-Alternative: /api/v2/users
```

### Default Lifecycle Policy
| Phase | Duration | Description |
|-------|----------|-------------|
| Deprecation Notice | 90 days | Endpoint deprecated but functional |
| Sunset Period | 30 days | Limited support, migration required |
| Removal | - | Endpoint no longer available |

### Header Generation Logic
1. Check if endpoint has active deprecation notice
2. Add `Deprecation: true` header
3. Add `Sunset` header with RFC 7231 date format
4. Add `Link` header with successor-version relation
5. Add custom `API-*` headers with ISO timestamps

## Testing

**20 comprehensive tests covering:**
- Enum validation (3 tests)
- API version management (4 tests)
- Deprecation notice management (3 tests)
- Header generation (2 tests)
- Field tracking (1 test)
- Client notification (2 tests)
- Statistics (1 test)
- Global manager lifecycle (2 tests)
- Header constants (1 test)

## Usage Example

```python
# Register API versions
await deprecation_manager.register_api_version(
    version="v2",
    base_path="/api/v2",
    status=ApiVersionStatus.STABLE,
    documentation_url="/docs/api/v2"
)

# Mark v1 as deprecated
await deprecation_manager.deprecate_version(
    version="v1",
    deprecation_date=datetime.utcnow(),
    sunset_date=datetime(2025, 6, 1)
)

# Create deprecation notice for specific endpoint
await deprecation_manager.create_deprecation_notice(
    notice_id="deprecate-users-v1",
    endpoint_path="/api/v1/users",
    http_method="GET",
    status=DeprecationStatus.DEPRECATED,
    severity=DeprecationSeverity.WARNING,
    sunset_date=datetime(2025, 6, 1),
    alternative_endpoint="/api/v2/users",
    alternative_version="v2",
    migration_guide_url="/docs/migration/v1-to-v2",
    notice_message="Please migrate to v2 API",
    breaking_changes=["Response format changed", "Authentication updated"]
)

# Get headers for response
headers = await deprecation_manager.get_deprecation_headers(
    endpoint_path="/api/v1/users",
    http_method="GET"
)
# Returns:
# {
#   "Deprecation": "true",
#   "Sunset": "Sun, 01 Jun 2025 00:00:00 GMT",
#   "Link": "</api/v2/users>; rel=\"successor-version\"",
#   "API-Deprecated": "2025-01-01T00:00:00",
#   "API-Sunset": "2025-06-01T00:00:00",
#   "API-Alternative": "/api/v2/users"
# }

# Track client notifications
await deprecation_manager.notify_client("client-123", "deprecate-users-v1")

# Client acknowledges
await deprecation_manager.acknowledge_notice("client-123", "deprecate-users-v1")
```

### FastAPI Middleware Usage
```python
from fastapi import FastAPI
from api_deprecation import DeprecationMiddleware

app = FastAPI()
app.add_middleware(DeprecationMiddleware, client_id_header="X-Client-ID")
```

### Decorator Usage
```python
from api_deprecation import deprecated

@router.get("/api/v1/legacy")
@deprecated(
    notice_id="legacy-endpoint",
    alternative_endpoint="/api/v2/modern",
    sunset_date=datetime(2025, 6, 1),
    severity=DeprecationSeverity.WARNING
)
async def legacy_endpoint():
    return {"message": "This endpoint is deprecated"}
```

## Files Changed

1. `backend/fastapi/api/utils/api_deprecation.py` - Core implementation (500+ lines)
2. `backend/fastapi/api/routers/api_deprecation.py` - API routes (350+ lines)
3. `tests/test_api_deprecation.py` - Comprehensive tests (350+ lines)
4. `PR_1473_API_DEPRECATION_HEADERS.md` - Documentation

## Security Considerations

- All deprecation configuration requires admin privileges
- Client tracking is anonymized
- No sensitive data in deprecation headers
- Audit trail for all deprecation changes

## Future Enhancements

- Integration with OpenAPI/Swagger for automatic documentation
- Email notifications for affected clients
- Dashboard for deprecation timeline visualization
- Automated sunset enforcement
- Migration code generation
- Integration with API gateways (Kong, Ambassador)
