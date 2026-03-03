# Fine-Grained API Key Scopes #1264

## Overview

This implementation introduces fine-grained API key scopes to the Soul Sense Exam platform, enforcing the principle of least privilege for API access. API keys can now be restricted to specific operations and resources, significantly reducing the security risk if a key is compromised.

## Architecture

### Core Components

1. **ApiKey Model** - Database model storing API keys with associated scopes
2. **ApiKeyService** - Service for API key lifecycle management and validation
3. **ApiKeyMiddleware** - FastAPI middleware enforcing scope-based access control
4. **API Key Routes** - REST endpoints for key management
5. **Scope Taxonomy** - Hierarchical permission system

### Database Schema

```sql
-- API Keys Table
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(128) UNIQUE NOT NULL,
    scopes JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at DATETIME,
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_api_key_user (user_id),
    INDEX idx_api_key_key (key_hash),
    INDEX idx_api_key_active (is_active),
    INDEX idx_api_key_created (created_at)
);
```

## Scope Taxonomy

### General Scopes
- `read` - Read access to general resources
- `write` - Write access to general resources
- `admin` - Full administrative access

### Resource-Specific Scopes
- `users:read` - Read access to user management
- `users:write` - Write access to user management
- `payments:read` - Read access to payment data
- `payments:write` - Write access to payment data
- `analytics:read` - Read access to analytics data
- `analytics:write` - Write access to analytics data
- `exams:read` - Read access to exam data
- `exams:write` - Write access to exam data
- `journal:read` - Read access to journal entries
- `journal:write` - Write access to journal entries
- `surveys:read` - Read access to survey data
- `surveys:write` - Write access to survey data
- `notifications:read` - Read access to notifications
- `notifications:write` - Write access to notifications
- `settings:read` - Read access to settings
- `settings:write` - Write access to settings

## Implementation Details

### API Key Model

```python
class ApiKey(Base):
    user_id: int
    name: str  # Human-readable identifier
    key_hash: str  # Secure hash of the actual key
    scopes: List[str]  # Granted permissions
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
```

### Middleware Flow

```python
# Request Processing Flow:
# 1. Check if path requires API key authentication
# 2. Extract X-API-Key header
# 3. Validate key exists and is active
# 4. Check required scopes for endpoint
# 5. Allow or deny access

async def api_key_middleware(request, call_next):
    if not requires_authentication(request.url.path):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(401, "API key required")

    # Validate key and scopes
    key_record = await verify_api_key(api_key)
    required_scopes = get_required_scopes(request.url.path, request.method)

    if not has_required_scopes(key_record, required_scopes):
        raise HTTPException(403, "Insufficient permissions")

    request.state.api_key = key_record
    return await call_next(request)
```

### Scope Requirements by Endpoint

| Endpoint Pattern | Method | Required Scopes |
|------------------|--------|------------------|
| `/api/v1/users` | GET | `users:read` |
| `/api/v1/users` | POST | `users:write` |
| `/api/v1/payments` | GET | `payments:read` |
| `/api/v1/analytics` | GET | `analytics:read` |
| `/api/v1/admin/*` | * | `admin` |
| `/api/v1/exams` | GET | `exams:read` |
| `/api/v1/journal` | POST | `journal:write` |

## API Endpoints

### Create API Key
```http
POST /api/v1/api-keys
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "My API Key",
  "scopes": ["read", "users:read"],
  "expires_in_days": 30
}
```

**Response:**
```json
{
  "api_key": "sk-abcd1234...",
  "key_info": {
    "id": 1,
    "name": "My API Key",
    "scopes": ["read", "users:read"],
    "is_active": true,
    "expires_at": "2024-02-15T00:00:00Z",
    "created_at": "2024-01-16T00:00:00Z"
  }
}
```

### List API Keys
```http
GET /api/v1/api-keys
Authorization: Bearer <jwt_token>
```

### Revoke API Key
```http
DELETE /api/v1/api-keys/{key_id}
Authorization: Bearer <jwt_token>
```

### Update API Key Scopes
```http
PUT /api/v1/api-keys/{key_id}/scopes
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "scopes": ["read", "write", "users:read"]
}
```

### List Available Scopes
```http
GET /api/v1/api-keys/scopes
```

## Usage Examples

### Creating a Read-Only Analytics Key
```bash
curl -X POST /api/v1/api-keys \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Analytics Dashboard Key",
    "scopes": ["analytics:read"],
    "expires_in_days": 365
  }'
```

### Using API Key for Requests
```bash
curl -X GET /api/v1/analytics/summary \
  -H "X-API-Key: sk-abcd1234..."
```

### Error Responses
```json
// Missing API key
{
  "detail": "API key required",
  "headers": {"WWW-Authenticate": "APIKey realm=\"/api/v1/analytics\""}
}

// Insufficient scopes
{
  "detail": "Insufficient permissions. Required scopes: analytics:write"
}

// Invalid key
{
  "detail": "Invalid or expired API key"
}
```

## Security Considerations

### Key Storage
- API keys are hashed using SHA-256 before storage
- Plain keys are only returned once during creation
- Keys can be revoked immediately if compromised

### Scope Validation
- Scopes are validated on every request
- No scope inheritance (explicit grants only)
- Admin scope provides unrestricted access

### Audit Logging
- All API key usage is logged with timestamps
- Failed authentication attempts are tracked
- Key creation, revocation, and scope changes are audited

### Expiration
- Keys can have optional expiration dates
- Expired keys are automatically deactivated
- Background cleanup removes expired keys

## Migration Strategy

### Existing API Keys
For applications currently using API keys without scopes:

1. **Assessment Phase**: Identify all existing API key usage
2. **Migration Window**: Allow existing keys to work with full permissions temporarily
3. **Gradual Rollout**: Require scopes for new keys while grandfathering existing ones
4. **Sunset Period**: Set expiration dates for legacy keys

### Database Migration
```sql
-- Add new columns to existing api_keys table (if it exists)
ALTER TABLE api_keys ADD COLUMN scopes JSON DEFAULT '["read", "write"]';
ALTER TABLE api_keys ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE api_keys ADD COLUMN expires_at DATETIME;
ALTER TABLE api_keys ADD COLUMN last_used_at DATETIME;
ALTER TABLE api_keys ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE api_keys ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Or create new table if starting fresh
CREATE TABLE api_keys (...);
```

## Testing

### Unit Tests
- API key creation and validation
- Scope checking logic
- Middleware behavior
- Service methods

### Integration Tests
- End-to-end API key authentication
- Scope enforcement on protected endpoints
- Key lifecycle management

### Security Tests
- Privilege escalation attempts
- Invalid key handling
- Scope bypass attempts
- Rate limiting for key operations

### Test Cases
```python
def test_read_scope_denied_write_access():
    # Create key with read scope only
    api_key = create_api_key(scopes=["read"])

    # Attempt write operation
    response = client.post("/api/v1/users", headers={"X-API-Key": api_key})
    assert response.status_code == 403

def test_admin_scope_grants_full_access():
    # Create key with admin scope
    api_key = create_api_key(scopes=["admin"])

    # Access admin endpoint
    response = client.get("/api/v1/admin/stats", headers={"X-API-Key": api_key})
    assert response.status_code == 200
```

## Monitoring and Alerting

### Metrics to Track
- API key creation rate
- Authentication success/failure rates
- Scope violation attempts
- Key expiration rates
- Usage patterns by scope

### Alerts
- High rate of failed authentications
- Privilege escalation attempts
- Mass key revocation events
- Scope violations above threshold

## Performance Considerations

### Database Indexes
- User ID for key listing
- Key hash for fast lookup
- Active status for filtering
- Created/updated timestamps

### Caching
- Valid keys can be cached with short TTL
- Scope requirements are static and cacheable
- User permissions can be cached per session

### Rate Limiting
- API key operations are rate limited
- Failed authentication attempts trigger backoff
- Scope violation attempts may trigger temporary blocks

## Compliance

### GDPR Considerations
- API keys are user-associated for audit purposes
- Keys can be revoked on user request
- Access logs support data portability requests

### Security Standards
- Keys follow least privilege principle
- Audit logging meets SOC 2 requirements
- Expiration prevents indefinite access

## Future Enhancements

### Advanced Features
- **Key Rotation**: Automatic key rotation with overlap periods
- **IP Restrictions**: Bind keys to specific IP ranges
- **Usage Quotas**: Rate limiting per key
- **Key Inheritance**: Hierarchical scope inheritance
- **Temporary Keys**: Short-lived keys for specific operations

### Integration Points
- **OAuth Integration**: API keys as OAuth client credentials
- **Service Accounts**: Keys for programmatic service access
- **Webhooks**: Event-driven key management
- **Multi-Tenant**: Tenant-scoped key permissions

## Conclusion

The fine-grained API key scopes implementation provides a robust foundation for secure API access control. By enforcing the principle of least privilege, the system significantly reduces the blast radius of compromised credentials while maintaining flexibility for various use cases.

The modular design allows for easy extension and customization based on organizational requirements, ensuring the system can evolve with changing security needs and API usage patterns.</content>
<parameter name="filePath">c:\Users\Gupta\Downloads\SOUL_SENSE_EXAM\API_KEY_SCOPES_1264.md