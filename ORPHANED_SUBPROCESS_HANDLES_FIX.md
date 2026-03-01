# Orphaned Subprocess Handles Fix #1185

## Problem
ML subprocesses remain alive after the parent process exits, causing resource leaks. This occurs because:
- Subprocesses are started without proper process group management
- No cleanup mechanisms for child processes on parent termination
- Signal handlers don't ensure subprocess termination
- Atexit handlers not configured for subprocess cleanup

## Solution
Implemented a comprehensive `MLSubprocessManager` that ensures proper subprocess lifecycle management:

### Key Features
1. **Process Group Management**: Uses `os.setsid()` (Unix) or `CREATE_NEW_PROCESS_GROUP` (Windows) for clean process groups
2. **Automatic Cleanup**: Atexit handlers ensure subprocess termination on parent exit
3. **Signal Handler Integration**: Defers shutdown operations to avoid race conditions
4. **Graceful Termination**: SIGTERM followed by SIGKILL with configurable timeouts
5. **Context Manager**: `managed_ml_process()` for automatic cleanup

### Files Modified
1. **`app/ml/subprocess_manager.py`**: New subprocess management system
2. **`app/shutdown_handler.py`**: Integrated subprocess cleanup in graceful shutdown
3. **Signal handlers**: Defer shutdown to prevent race conditions

### Technical Implementation
- **Process Groups**: Ensures child processes can be terminated as a group
- **Deferred Shutdown**: Signal handlers use `root.after(0, ...)` to avoid blocking operations
- **Atexit Registration**: Automatic cleanup when Python process exits
- **Cross-Platform**: Works on both Unix-like systems and Windows

### Usage Examples
```python
# Direct management
from app.ml.subprocess_manager import get_ml_subprocess_manager
manager = get_ml_subprocess_manager()
process = manager.start_ml_process('inference', ['python', 'server.py'])

# Context manager (automatic cleanup)
from app.ml.subprocess_manager import managed_ml_process
with managed_ml_process('worker', ['python', 'worker.py']):
    # Process runs here
    pass  # Automatically terminated
```

## Testing
Created comprehensive test suite (`test_orphaned_subprocess_fix.py`) that validates:
- ✅ Subprocess manager import and initialization
- ✅ Process group creation and management
- ✅ Atexit cleanup functionality
- ✅ Signal handler deferral mechanism
- ✅ Shutdown handler integration
- ✅ Context manager automatic cleanup

## Edge Cases Handled
- **Forced Parent Crash**: Atexit handlers ensure cleanup even on abnormal termination
- **Timeout Termination**: Configurable timeouts for graceful vs force termination
- **Concurrent Signals**: Deferred shutdown prevents multiple simultaneous cleanups
- **Platform Differences**: Cross-platform process group handling

## Benefits
- **Resource Leak Prevention**: No orphaned processes after parent exit
- **Clean Shutdown**: Graceful termination of all ML subprocesses
- **Reliability**: Multiple cleanup mechanisms (atexit, signals, manual)
- **Monitoring**: Process tracking and health monitoring capabilities