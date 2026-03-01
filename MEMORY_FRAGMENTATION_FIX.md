# Memory Fragmentation in Long-Running Tasks Fix (#1165)

## Issue Description
Large allocations not reclaimed in Celery loops, causing gradual memory bloat.

**Objective:** Prevent gradual memory bloat.

**Edge Cases:**
- Batch processing loops
- Model inference cycles

**Test Cases:**
- Long-duration task execution
- Monitor RSS growth

**Recommended Testing:**
- Memory profiling tools
- Heap inspection

**Technical Implementation:**
- Force garbage collection
- Use max_tasks_per_child
- Avoid global object retention

## Solution Implemented

### Changes Made

1. **Celery Worker Configuration** (`backend/fastapi/api/celery_app.py`):
   - `worker_max_tasks_per_child=50`: Restart worker after 50 tasks to prevent memory accumulation
   - `worker_prefetch_multiplier=1`: Limit prefetch to reduce memory pressure
   - `task_time_limit=3600`: Kill tasks running longer than 1 hour
   - `task_soft_time_limit=3300`: Soft limit at 55 minutes for graceful shutdown

2. **Memory Management in Tasks** (`backend/fastapi/api/celery_tasks.py`):
   - Added `cleanup_memory()` function for garbage collection
   - Memory limit enforcement before task execution
   - Forced GC after large operations (export, notification, archive tasks)
   - Memory thresholds: 512MB for general tasks, 1024MB for archive operations

3. **Proactive Memory Guard Integration**:
   - Uses existing `enforce_memory_limit()` from memory_guard utility
   - Tasks check memory usage before starting heavy operations

### How It Fixes the Issue

- **Prevents Memory Bloat:** Worker restarts after max tasks prevent accumulation
- **Forces Garbage Collection:** Explicit GC calls reclaim memory after large allocations
- **Memory Limits:** Tasks fail gracefully if memory thresholds are exceeded
- **Time Limits:** Prevents runaway tasks from consuming resources indefinitely
- **Handles Edge Cases:** Batch processing and inference cycles are bounded by memory/time limits

### Files Modified
- `backend/fastapi/api/celery_app.py`
- `backend/fastapi/api/celery_tasks.py`

### Testing
- Syntax validation passed
- Ready for memory profiling and RSS monitoring during long-running task execution