# Zombie Process Accumulation in Celery Fix (#1162)

## Issue Description
Unreaped child processes remain defunct, causing process table overflow.

**Objective:** Prevent process table overflow.

**Technical Implementation:**
- Handle SIGCHLD
- Use spawn start method
- Ensure wait() calls

## Solution Implemented

### Changes Made

Modified `celery_app.py` to prevent zombie process accumulation:

1. **Set Multiprocessing Start Method:**
   - `multiprocessing.set_start_method('spawn', force=True)`
   - Prevents zombie issues by using spawn instead of fork

2. **SIGCHLD Signal Handler:**
   - Registered `sigchld_handler` to reap zombie processes
   - Uses `os.waitpid(-1, os.WNOHANG)` in a loop to reap all zombies
   - Logs reaped processes for monitoring

3. **Proper Process Management:**
   - Handler catches SIGCHLD signals when child processes terminate
   - Non-blocking wait prevents hanging

### How It Fixes the Issue

- **Prevents Process Table Overflow:** Reaps zombies immediately when they terminate
- **Handles SIGCHLD:** Signal handler ensures no defunct processes accumulate
- **Spawn Method:** More robust process creation that avoids fork-related zombies
- **Wait Calls:** `os.waitpid` properly cleans up terminated child processes

### Files Modified
- `backend/fastapi/api/celery_app.py`

### Testing
- Syntax validation passed
- Ready for monitoring with `ps aux | grep defunct` or `top` to verify no zombie accumulation