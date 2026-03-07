# PR: Idempotent PATCH Conflict Resolution Contract

**Issue:** #1474  
**Branch:** `fix/idempotent-patch-conflict-resolution-1474`

## Overview

This PR implements RFC 5789 compliant idempotent PATCH operations with conflict detection and resolution strategies. It provides optimistic concurrency control using ETags and supports multiple conflict resolution strategies.

## Features Implemented

### Idempotent PATCH Operations
- **6 Conflict Strategies**: Reject, Merge, Overwrite, Client Wins, Server Wins, Custom
- **7 Patch Statuses**: Pending, Applied, Conflict, Rejected, Merged, Failed, Retrying
- **4 Change Types**: Added, Modified, Removed, Unchanged
- RFC 6902 JSON Patch style operations (add, remove, replace)

### Optimistic Concurrency Control
- ETag-based version tracking
- If-Match header support
- Automatic conflict detection
- Version history tracking

### Conflict Resolution
- Field-level conflict detection
- Multiple resolution strategies
- Automatic merge for compatible changes
- Configurable per-request strategy

### Idempotency Support
- Idempotency key tracking
- Deduplication of identical requests
- Idempotency key header support

### API Endpoints (7 endpoints)

**Resource Management:**
- `POST /patch-operations/resources` - Create resource (Admin only)
- `GET /patch-operations/resources/{resource_id}` - Get resource

**PATCH Operations:**
- `PATCH /patch-operations/resources/{resource_id}` - Apply PATCH

**History & Versioning:**
- `GET /patch-operations/resources/{resource_id}/history` - Get patch history
- `GET /patch-operations/resources/{resource_id}/version` - Get version info
- `POST /patch-operations/resources/{resource_id}/compare` - Compare versions

**Analytics:**
- `GET /patch-operations/statistics` - Get statistics
- `GET /patch-operations/health` - Health check

## Implementation Details

### PATCH Operation Flow
1. Client reads resource with ETag
2. Client sends PATCH with If-Match header
3. Server validates ETag against current version
4. If ETag matches, apply operations atomically
5. If ETag mismatches, detect conflicts
6. Apply conflict resolution strategy
7. Return result with new ETag

### Conflict Detection
```python
# Conflict exists if both client and server changed from base
if client_value != base_value and server_value != base_value:
    if client_value != server_value:
        # CONFLICT detected
```

### Conflict Resolution Strategies
| Strategy | Behavior |
|----------|----------|
| REJECT | Return 409 Conflict |
| CLIENT_WINS | Client changes take precedence |
| SERVER_WINS | Server changes take precedence |
| MERGE | Combine non-conflicting changes |
| OVERWRITE | Replace server state |

### Request/Response Headers
```http
# Request
PATCH /resources/user-123 HTTP/1.1
If-Match: "abc123"
Idempotency-Key: unique-request-id
Content-Type: application/json

[
  {"op": "replace", "path": "/name", "value": "New Name"}
]

# Response (Success)
HTTP/1.1 200 OK
ETag: "def456"
Content-Type: application/json

{
  "request_id": "req-123",
  "status": "applied",
  "new_etag": "def456",
  "new_version": 2,
  "applied_changes": [...]
}

# Response (Conflict)
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "message": "Conflict detected in fields: ['name']",
  "current_etag": "xyz789",
  "current_version": 3
}
```

## Testing

**18 comprehensive tests covering:**
- Enum validation (3 tests)
- Conflict detection (2 tests)
- Conflict resolution (2 tests)
- Resource management (2 tests)
- PATCH application (5 tests)
- History tracking (1 test)
- Statistics (1 test)
- Global manager lifecycle (2 tests)

## Usage Example

```python
# Create a resource
version = await patch_manager.create_resource(
    resource_id="user-123",
    resource_type="user",
    data={
        "name": "John Doe",
        "email": "john@example.com",
        "role": "user",
        "status": "active"
    }
)
# Returns: ETag "abc123", version 1

# Apply a PATCH
request = PatchRequest(
    request_id="patch-001",
    resource_id="user-123",
    resource_type="user",
    operations=[
        PatchOperation(op="replace", path="/name", value="Jane Doe"),
        PatchOperation(op="replace", path="/role", value="admin")
    ],
    expected_etag="abc123",  # Optimistic concurrency
    idempotency_key="unique-key-123",
    conflict_strategy=ConflictStrategy.REJECT
)

result = await patch_manager.apply_patch(request)

if result.status == PatchStatus.APPLIED:
    print(f"Updated to version {result.new_version}")
    print(f"New ETag: {result.new_etag}")
    # Returns: version 2, ETag "def456"

# Handle conflicts
try:
    result = await patch_manager.apply_patch(request)
except ConflictException as e:
    # Get current state and retry
    current = await patch_manager.get_resource("user-123")
    version = await patch_manager.get_resource_version("user-123")
    # Reapply changes with new ETag
```

### HTTP API Usage
```bash
# Create resource
curl -X POST /patch-operations/resources \
  -H "Content-Type: application/json" \
  -d '{"resource_id": "doc-1", "resource_type": "document", "data": {"title": "Draft"}}'

# Apply PATCH
curl -X PATCH /patch-operations/resources/doc-1 \
  -H "Content-Type: application/json" \
  -H "If-Match: abc123" \
  -H "Idempotency-Key: my-key" \
  -d '{"operations": [{"op": "replace", "path": "/title", "value": "Final"}]}'

# Get patch history
curl /patch-operations/resources/doc-1/history
```

## Files Changed

1. `backend/fastapi/api/utils/patch_conflict_resolution.py` - Core implementation (550+ lines)
2. `backend/fastapi/api/routers/patch_conflict_resolution.py` - API routes (300+ lines)
3. `tests/test_patch_conflict_resolution.py` - Comprehensive tests (350+ lines)
4. `PR_1474_PATCH_CONFLICT_RESOLUTION.md` - Documentation

## Security Considerations

- All resource operations require authentication
- ETag validation prevents lost update problem
- Idempotency prevents duplicate updates
- Audit trail through patch history

## Future Enhancements

- WebSocket support for real-time conflict notification
- Three-way merge for complex conflicts
- Batch PATCH operations
- Conditional PATCH (If-Unmodified-Since)
- JSON Merge Patch (RFC 7386) support
- Diff/patch generation utilities
