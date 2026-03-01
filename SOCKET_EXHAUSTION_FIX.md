# Socket Exhaustion in gRPC Communication Fix (#1160)

## Issue Description
gRPC connections not closed properly, leading to network resource exhaustion.

**Objective:** Prevent network resource exhaustion.

**Edge Cases:**
- Timeout retries
- Network partitions

**Test Cases:**
- Simulate packet drops
- Monitor open sockets

**Recommended Testing:**
- `netstat -an`
- Stress test connection churn

**Technical Implementation:**
- Use connection pooling
- Ensure `channel.close()`
- Keepalive tuning

## Solution Implemented

### Changes Made

Modified `NLPClient` in `backend/fastapi/api/services/nlp_client.py` to implement connection reuse and proper keepalive settings:

1. **Persistent Channel with Keepalive Options:**
   - Created channel in `__init__` with keepalive parameters
   - `grpc.keepalive_time_ms`: 30000 (30 seconds)
   - `grpc.keepalive_timeout_ms`: 5000 (5 seconds)
   - `grpc.keepalive_permit_without_calls`: True
   - Additional HTTP/2 ping settings for connection health

2. **Connection Reuse:**
   - Removed per-method channel creation
   - Methods now use the persistent `self._stub`
   - Singleton pattern ensures one channel per client instance

3. **Proper Channel Lifecycle:**
   - Channel created once in constructor
   - Closed in `__aexit__` context manager

### How It Fixes the Issue

- **Prevents Socket Exhaustion:** Reusing a single channel instead of creating new ones for each call
- **Connection Pooling:** Singleton client acts as a connection pool
- **Keepalive Tuning:** Maintains connection health and detects dead connections
- **Handles Edge Cases:** Keepalive settings help with network partitions and timeouts
- **Resource Management:** Proper channel closing prevents leaks

### Files Modified
- `backend/fastapi/api/services/nlp_client.py`

### Testing
- Syntax validation passed
- Ready for stress testing with `netstat -an` and connection churn tests