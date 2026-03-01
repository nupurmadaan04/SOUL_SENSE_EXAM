#!/usr/bin/env python3
"""
Test script for Orphaned Subprocess Handles Fix #1185

Tests the ML subprocess management to prevent orphaned processes:
- Process group management for clean termination
- Automatic cleanup on parent exit
- Signal handling for graceful shutdown
- Atexit handler cleanup
"""

import os
import sys
import time
import signal
import psutil
import subprocess
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_subprocess_manager_import():
    """Test that subprocess manager can be imported"""
    print("Testing subprocess manager import...")

    try:
        from app.ml.subprocess_manager import MLSubprocessManager, get_ml_subprocess_manager
        manager = get_ml_subprocess_manager()
        assert isinstance(manager, MLSubprocessManager)
        print("✓ Subprocess manager imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import subprocess manager: {e}")
        return False

def test_process_group_management():
    """Test process group creation and management"""
    print("Testing process group management...")

    try:
        from app.ml.subprocess_manager import get_ml_subprocess_manager
        manager = get_ml_subprocess_manager()

        # Start a simple subprocess
        if sys.platform == "win32":
            cmd = ["timeout", "10"]  # Windows timeout command
        else:
            cmd = ["sleep", "10"]  # Unix sleep command

        process = manager.start_ml_process("test_process", cmd)
        if process is None:
            print("✗ Failed to start test process")
            return False

        # Check that process is tracked
        assert "test_process" in manager._processes
        assert manager.is_process_running("test_process")

        # Get process info
        info = manager.get_process_info("test_process")
        assert info is not None
        assert "pid" in info
        assert "pgid" in info

        print(f"✓ Process started with PID {info['pid']}, PGID {info['pgid']}")

        # Terminate the process
        success = manager.terminate_process("test_process")
        assert success

        # Check that it's cleaned up
        assert "test_process" not in manager._processes
        assert not manager.is_process_running("test_process")

        print("✓ Process terminated and cleaned up successfully")
        return True

    except Exception as e:
        print(f"✗ Process group management test failed: {e}")
        return False

def test_atexit_cleanup():
    """Test that atexit handlers clean up processes"""
    print("Testing atexit cleanup...")

    try:
        from app.ml.subprocess_manager import get_ml_subprocess_manager
        manager = get_ml_subprocess_manager()

        # Start a process
        if sys.platform == "win32":
            cmd = ["timeout", "30"]  # Longer timeout for testing
        else:
            cmd = ["sleep", "30"]

        process = manager.start_ml_process("atexit_test", cmd)
        if process is None:
            print("✗ Failed to start atexit test process")
            return False

        print(f"✓ Started process for atexit test (PID {process.pid})")

        # The cleanup should happen when the Python process exits
        # We can't easily test atexit in the same process, but we can verify
        # that the manager has registered the handler
        assert manager._atexit_registered

        # Manually trigger cleanup to test the logic
        manager.cleanup_all()

        # Verify process is terminated
        assert not manager.is_process_running("atexit_test")
        print("✓ Atexit cleanup logic works correctly")
        return True

    except Exception as e:
        print(f"✗ Atexit cleanup test failed: {e}")
        return False

def test_signal_handler_deferral():
    """Test that signal handlers defer subprocess cleanup"""
    print("Testing signal handler deferral...")

    # Check that shutdown handlers use root.after() instead of direct call
    files_to_check = [
        Path("app/shutdown_handler.py"),
        Path("app/main.py"),
        Path("temp_refactored.py"),
        Path("temp_main.py"),
    ]

    all_good = True
    for file_path in files_to_check:
        if not file_path.exists():
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Check for deferred shutdown call
        if "root.after(0," in content and "graceful_shutdown" in content:
            print(f"✓ {file_path.name} defers shutdown properly")
        else:
            print(f"✗ {file_path.name} does not defer shutdown")
            all_good = False

    return all_good

def test_shutdown_handler_integration():
    """Test that shutdown handler integrates subprocess cleanup"""
    print("Testing shutdown handler integration...")

    shutdown_file = Path("app/shutdown_handler.py")
    if not shutdown_file.exists():
        print("✗ shutdown_handler.py not found")
        return False

    with open(shutdown_file, 'r') as f:
        content = f.read()

    # Check for subprocess manager integration
    checks = [
        "get_ml_subprocess_manager" in content,
        "cleanup_all" in content,
        "ML subprocesses cleaned up" in content,
    ]

    passed = sum(checks)
    if passed == len(checks):
        print("✓ Shutdown handler integrates subprocess cleanup")
        return True
    else:
        print(f"✗ Shutdown handler missing subprocess cleanup ({passed}/{len(checks)})")
        return False

def test_context_manager():
    """Test the managed_ml_process context manager"""
    print("Testing managed_ml_process context manager...")

    try:
        from app.ml.subprocess_manager import managed_ml_process

        # Test with a simple command
        if sys.platform == "win32":
            cmd = ["cmd", "/c", "echo", "test"]
        else:
            cmd = ["echo", "test"]

        with managed_ml_process("context_test", cmd) as process:
            assert process is not None
            # Wait a bit for process to complete
            time.sleep(0.1)

        # Process should be terminated automatically
        from app.ml.subprocess_manager import get_ml_subprocess_manager
        manager = get_ml_subprocess_manager()
        assert not manager.is_process_running("context_test")

        print("✓ Context manager works correctly")
        return True

    except Exception as e:
        print(f"✗ Context manager test failed: {e}")
        return False

def run_all_tests():
    """Run all orphaned subprocess tests"""
    print("Running Orphaned Subprocess Handles Tests (#1185)")
    print("=" * 50)

    tests = [
        test_subprocess_manager_import,
        test_process_group_management,
        test_atexit_cleanup,
        test_signal_handler_deferral,
        test_shutdown_handler_integration,
        test_context_manager,
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with error: {e}")
            print()

    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("✓ All orphaned subprocess mitigation tests passed!")
        return True
    else:
        print("✗ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)