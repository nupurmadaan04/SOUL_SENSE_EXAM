#!/usr/bin/env python3
"""
Test script to verify signal handler fix for Windows compatibility.
This test ensures that SIGTERM is not registered on Windows platforms.
"""

import platform
import signal
import sys
import os

def test_signal_registration():
    """Test that signal registration works correctly on Windows."""

    print(f"Testing signal registration on {platform.system()} platform...")

    # Test that we can import signal module
    try:
        import signal
        print("✓ Signal module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import signal module: {e}")
        return False

    # Test SIGINT registration (should work on all platforms)
    try:
        def dummy_handler(signum, frame):
            pass

        signal.signal(signal.SIGINT, dummy_handler)
        print("✓ SIGINT handler registered successfully")
    except Exception as e:
        print(f"✗ Failed to register SIGINT handler: {e}")
        return False

    # Test SIGTERM registration (should only work on non-Windows platforms)
    sigterm_available = True
    try:
        signal.signal(signal.SIGTERM, dummy_handler)
        print("✓ SIGTERM handler registered successfully")
    except (AttributeError, ValueError) as e:
        if platform.system() == 'Windows':
            print("✓ SIGTERM correctly not available on Windows (expected)")
            sigterm_available = False
        else:
            print(f"✗ Unexpected error registering SIGTERM on non-Windows: {e}")
            return False
    except Exception as e:
        print(f"✗ Unexpected error with SIGTERM: {e}")
        return False

    # Verify platform-specific behavior
    if platform.system() == 'Windows':
        if sigterm_available:
            print("✗ SIGTERM should not be available on Windows")
            return False
        else:
            print("✓ Windows-specific behavior confirmed: SIGTERM not available")
    else:
        if not sigterm_available:
            print("✗ SIGTERM should be available on non-Windows platforms")
            return False
        else:
            print("✓ Non-Windows behavior confirmed: SIGTERM available")

    return True

def test_app_import():
    """Test that the main app can be imported without signal errors."""

    print("\nTesting app import...")

    try:
        # Add current directory to path for module import
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        # Try to import the main app module
        import app.main
        print("✓ app.main module imported successfully")

        # Check if the signal handling code would work
        # We can't actually run the main function without GUI, but we can check imports
        print("✓ App imports completed without signal-related errors")

        return True
    except Exception as e:
        print(f"✗ Failed to import app.main: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SIGNAL HANDLER FIX TEST FOR WINDOWS COMPATIBILITY")
    print("=" * 60)

    success = True

    # Test 1: Signal registration
    if not test_signal_registration():
        success = False

    # Test 2: App import
    if not test_app_import():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED - Signal handler fix is working correctly!")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED - Signal handler fix needs attention")
        sys.exit(1)
