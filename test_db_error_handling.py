"""Minimal tests for Issue #1229 - Transient failure retries"""

import asyncio
import sys
import importlib.util
from unittest.mock import MagicMock
from sqlalchemy.exc import OperationalError

# Load db_error_handler directly from file
spec = importlib.util.spec_from_file_location(
    "db_error_handler", 
    "backend/fastapi/api/services/db_error_handler.py"
)
db_handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_handler)

_is_transient_error = db_handler._is_transient_error
_calculate_backoff_delay = db_handler._calculate_backoff_delay
_retry_sync_operation = db_handler._retry_sync_operation
_retry_async_operation = db_handler._retry_async_operation
DatabaseConnectionError = db_handler.DatabaseConnectionError


def test_transient_error_detection():
    """Test if transient errors are correctly identified."""
    print("Testing transient error detection...")
    
    # Test 1: Deadlock (transient)
    exc = OperationalError("Deadlock", None, None)
    exc.orig = MagicMock(sqlstate='40001')
    assert _is_transient_error(exc) == True
    print("  ✓ Deadlock detected as transient")
    
    # Test 2: Constraint violation (permanent)
    exc = OperationalError("Constraint", None, None)
    exc.orig = MagicMock(sqlstate='23505')
    assert _is_transient_error(exc) == False
    print("  ✓ Constraint violation detected as permanent")


def test_backoff_calculation():
    """Test exponential backoff calculation."""
    print("\nTesting exponential backoff...")
    
    # Attempt 0: 100ms
    delay = _calculate_backoff_delay(0, base_delay_ms=100, jitter_factor=0)
    assert abs(delay - 0.1) < 0.01
    print(f"  ✓ Attempt 0: {delay:.3f}s (expected 0.1s)")
    
    # Attempt 1: 400ms
    delay = _calculate_backoff_delay(1, base_delay_ms=100, jitter_factor=0)
    assert abs(delay - 0.4) < 0.01
    print(f"  ✓ Attempt 1: {delay:.3f}s (expected 0.4s)")
    
    # Attempt 2: 1600ms
    delay = _calculate_backoff_delay(2, base_delay_ms=100, jitter_factor=0)
    assert abs(delay - 1.6) < 0.01
    print(f"  ✓ Attempt 2: {delay:.3f}s (expected 1.6s)")


def test_sync_retry():
    """Test sync retry logic."""
    print("\nTesting sync retry logic...")
    
    # Test 1: Success on first try
    call_count = 0
    def successful():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = _retry_sync_operation(successful, max_retries=3, base_delay_ms=10)
    assert result == "success" and call_count == 1
    print("  ✓ Success on first attempt (called once)")
    
    # Test 2: Success after retry
    call_count = 0
    def retry_once():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            exc = OperationalError("Deadlock", None, None)
            exc.orig = MagicMock(sqlstate='40001')
            raise exc
        return "success"
    
    result = _retry_sync_operation(retry_once, max_retries=2, base_delay_ms=10)
    assert result == "success" and call_count == 2
    print("  ✓ Success after 1 retry (called twice)")


async def test_async_retry():
    """Test async retry logic."""
    print("\nTesting async retry logic...")
    
    # Test: Success on first try
    call_count = 0
    async def async_success():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = await _retry_async_operation(async_success, max_retries=3, base_delay_ms=5)
    assert result == "success" and call_count == 1
    print("  ✓ Async success on first attempt (called once)")


if __name__ == "__main__":
    print("=" * 60)
    print("Issue #1229 - Transient Failure Retry Tests")
    print("=" * 60)
    
    test_transient_error_detection()
    test_backoff_calculation()
    test_sync_retry()
    asyncio.run(test_async_retry())
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
