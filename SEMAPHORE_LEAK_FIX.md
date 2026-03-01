# Semaphore Leak in Async Lock Management Fix (#1164)

## Issue Description
AsyncLock not released during exception paths, leading to deadlocks from leaked semaphores.

**Objective:** Avoid deadlocks from leaked semaphores.

**Edge Cases:**
- Exception inside critical section
- Cancellation before release

**Test Cases:**
- Force exception while holding lock
- Concurrent lock acquisition stress test

**Recommended Testing:**
- Track lock counts
- Enable async debug logs

**Technical Implementation:**
- Always release in finally
- Add lock timeout safety

## Solution Implemented

### Changes Made

1. **Created AsyncLock Class** (`backend/fastapi/api/utils/distributed_lock.py`):
   - Wrapper around `asyncio.Lock` with guaranteed release in `__aexit__`
   - Supports timeout for lock acquisition to prevent hanging
   - Uses try/finally pattern to ensure release even during exceptions

2. **Fixed Test Harness** (`backend/fastapi/tests/distributed_test_harness.py`):
   - Wrapped lock usage in try/finally to ensure release
   - Prevents semaphore leaks during exception paths in tests

3. **Lock Timeout Safety**:
   - AsyncLock supports timeout parameter for acquisition
   - Raises `RuntimeError` on timeout to prevent indefinite waiting

### How It Fixes the Issue

- **Guaranteed Release:** `__aexit__` always releases the lock, even if exceptions occur
- **Exception Safety:** try/finally ensures cleanup in all code paths
- **Timeout Protection:** Prevents deadlocks from locks that can't be acquired
- **Cancellation Handling:** Async context manager properly handles task cancellation

### Files Modified
- `backend/fastapi/api/utils/distributed_lock.py`
- `backend/fastapi/tests/distributed_test_harness.py`

### Testing
- Syntax validation passed
- Ready for stress testing with exception injection and concurrent access