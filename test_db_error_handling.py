#!/usr/bin/env python3
"""
Comprehensive tests for database error handling with transient failure retries (Issue #1229).

Tests cover:
- Transient error detection (SQLState codes)
- Retry logic with exponential backoff
- Jitter to prevent thundering herd
- Sync and async operations
- Max retries limit
"""

import sys
import os
import asyncio
import importlib.util
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from collections import Counter

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

def load_module(name, path):
    """Load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_transient_error_detection():
    """Test detection of transient vs permanent database errors."""
    print("Testing transient error detection...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    from sqlalchemy.exc import OperationalError, DatabaseError
    
    # Mock database exception with SQLState
    class MockOrigException:
        def __init__(self, sqlstate):
            self.sqlstate = sqlstate
    
    # Test 1: Deadlock (40001) - Transient
    print("  - Test 1: Deadlock (40001) - should be transient")
    exc = OperationalError("Deadlock", None, None)
    exc.orig = MockOrigException('40001')
    assert db_handler._is_transient_error(exc) == True
    print("    ✓ Correctly identified as transient")
    
    # Test 2: Lock timeout (55P03) - Transient
    print("  - Test 2: Lock timeout (55P03) - should be transient")
    exc = OperationalError("Lock not available", None, None)
    exc.orig = MockOrigException('55P03')
    assert db_handler._is_transient_error(exc) == True
    print("    ✓ Correctly identified as transient")
    
    # Test 3: Connection error (08006) - Transient
    print("  - Test 3: Connection error (08006) - should be transient")
    exc = OperationalError("Connection failure", None, None)
    exc.orig = MockOrigException('08006')
    assert db_handler._is_transient_error(exc) == True
    print("    ✓ Correctly identified as transient")
    
    # Test 4: Constraint violation (23505) - Permanent
    print("  - Test 4: Constraint violation (23505) - should be permanent")
    exc = OperationalError("Unique constraint violation", None, None)
    exc.orig = MockOrigException('23505')
    assert db_handler._is_transient_error(exc) == False
    print("    ✓ Correctly identified as permanent")
    
    # Test 5: DisconnectionError - Always Transient
    print("  - Test 5: DisconnectionError - should be transient")
    from sqlalchemy.exc import DisconnectionError
    exc = DisconnectionError("Connection lost")
    assert db_handler._is_transient_error(exc) == True
    print("    ✓ Correctly identified as transient")
    
    print("✓ All transient error detection tests passed!\n")


def test_exponential_backoff_calculation():
    """Test exponential backoff delay calculation."""
    print("Testing exponential backoff calculation...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    
    # Test exponential backoff sequence (without jitter for base calculation)
    print("  - Testing base delays (ignoring jitter)...")
    
    # Run multiple times to account for random jitter
    delays_by_attempt = {0: [], 1: [], 2: []}
    for _ in range(100):
        for attempt in range(3):
            delay = db_handler._calculate_backoff_delay(attempt, base_delay_ms=100, jitter_factor=0.0)
            delays_by_attempt[attempt].append(delay)
    
    # Check average delays match expected exponential backoff
    # Attempt 0: 100ms = 0.1s
    # Attempt 1: 400ms = 0.4s
    # Attempt 2: 1600ms = 1.6s
    avg_0 = sum(delays_by_attempt[0]) / len(delays_by_attempt[0])
    avg_1 = sum(delays_by_attempt[1]) / len(delays_by_attempt[1])
    avg_2 = sum(delays_by_attempt[2]) / len(delays_by_attempt[2])
    
    assert abs(avg_0 - 0.1) < 0.01, f"Attempt 0 average {avg_0}s != 0.1s"
    assert abs(avg_1 - 0.4) < 0.01, f"Attempt 1 average {avg_1}s != 0.4s"
    assert abs(avg_2 - 1.6) < 0.01, f"Attempt 2 average {avg_2}s != 1.6s"
    print(f"    ✓ Attempt 0: {avg_0:.3f}s (expected 0.1s)")
    print(f"    ✓ Attempt 1: {avg_1:.3f}s (expected 0.4s)")
    print(f"    ✓ Attempt 2: {avg_2:.3f}s (expected 1.6s)")
    
    # Test jitter application
    print("  - Testing jitter application...")
    delays_with_jitter = []
    for _ in range(100):
        delay = db_handler._calculate_backoff_delay(0, base_delay_ms=100, jitter_factor=0.1)
        delays_with_jitter.append(delay)
    
    avg_jittered = sum(delays_with_jitter) / len(delays_with_jitter)
    assert abs(avg_jittered - 0.1) < 0.01, f"With jitter average {avg_jittered}s should stay ~0.1s"
    
    # Check that delays vary (not all the same)
    unique_delays = len(set(delays_with_jitter))
    assert unique_delays > 50, f"Should have varied delays with jitter, got {unique_delays} unique values"
    print(f"    ✓ Jitter creates variation: {unique_delays} unique delays in 100 attempts")
    
    print("✓ All exponential backoff tests passed!\n")

    print("✓ All exponential backoff tests passed!\n")


def test_retry_logic_sync():
    """Test sync retry logic with transient errors."""
    print("Testing sync retry logic...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    from sqlalchemy.exc import OperationalError
    
    # Test 1: Successful operation on first try
    print("  - Test 1: Successful operation on first try")
    call_count = 0
    def successful_op():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = db_handler._retry_sync_operation(
        successful_op,
        operation_name="test",
        max_retries=3
    )
    assert result == "success"
    assert call_count == 1
    print(f"    ✓ Called once, returned 'success'")
    
    # Test 2: Successful operation after 2 retries (transient error)
    print("  - Test 2: Successful operation after 2 retries")
    call_count = 0
    def failing_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            exc = OperationalError("Deadlock", None, None)
            exc.orig = MagicMock(sqlstate='40001')
            raise exc
        return "success"
    
    result = db_handler._retry_sync_operation(
        failing_then_success,
        operation_name="test",
        max_retries=3,
        base_delay_ms=10,  # Use small delay for testing
    )
    assert result == "success"
    assert call_count == 3
    print(f"    ✓ Retried 2 times, then succeeded on 3rd attempt")
    
    # Test 3: Exhausted retries with persistent transient error
    print("  - Test 3: Exhausted retries with persistent transient error")
    call_count = 0
    def always_fails():
        nonlocal call_count
        call_count += 1
        exc = OperationalError("Deadlock", None, None)
        exc.orig = MagicMock(sqlstate='40001')
        raise exc
    
    try:
        db_handler._retry_sync_operation(
            always_fails,
            operation_name="test",
            max_retries=2,  # Only 2 retries
            base_delay_ms=10,
        )
        assert False, "Should have raised DatabaseConnectionError"
    except db_handler.DatabaseConnectionError:
        assert call_count == 3  # Initial attempt + 2 retries
        print(f"    ✓ Failed after {call_count} attempts (initial + 2 retries)")
    
    # Test 4: Permanent error - should not retry
    print("  - Test 4: Permanent error - should not retry")
    call_count = 0
    def permanent_error():
        nonlocal call_count
        call_count += 1
        exc = OperationalError("Constraint violation", None, None)
        exc.orig = MagicMock(sqlstate='23505')  # Constraint violation
        raise exc
    
    try:
        db_handler._retry_sync_operation(
            permanent_error,
            operation_name="test",
            max_retries=3,
            base_delay_ms=10,
        )
        assert False, "Should have raised PermanentDatabaseError"
    except db_handler.PermanentDatabaseError:
        assert call_count == 1  # Only attempted once, no retries
        print(f"    ✓ Did not retry on permanent error (called once)")
    
    print("✓ All sync retry logic tests passed!\n")


async def test_retry_logic_async():
    """Test async retry logic with transient errors."""
    print("Testing async retry logic...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    from sqlalchemy.exc import OperationalError
    
    # Test 1: Successful async operation on first try
    print("  - Test 1: Successful async operation on first try")
    call_count = 0
    async def successful_async_op():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        return "success"
    
    result = await db_handler._retry_async_operation(
        successful_async_op,
        operation_name="test",
        max_retries=3
    )
    assert result == "success"
    assert call_count == 1
    print(f"    ✓ Called once, returned 'success'")
    
    # Test 2: Successful async operation after 1 retry
    print("  - Test 2: Successful async operation after 1 retry")
    call_count = 0
    async def failing_async_then_success():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        if call_count < 2:
            exc = OperationalError("Deadlock", None, None)
            exc.orig = MagicMock(sqlstate='40001')
            raise exc
        return "success"
    
    result = await db_handler._retry_async_operation(
        failing_async_then_success,
        operation_name="test",
        max_retries=3,
        base_delay_ms=5,
    )
    assert result == "success"
    assert call_count == 2
    print(f"    ✓ Retried 1 time, then succeeded on 2nd attempt")
    
    # Test 3: Permanent error - should not retry
    print("  - Test 3: Permanent error - should not retry")
    call_count = 0
    async def permanent_error_async():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        exc = OperationalError("Constraint violation", None, None)
        exc.orig = MagicMock(sqlstate='23505')
        raise exc
    
    try:
        await db_handler._retry_async_operation(
            permanent_error_async,
            operation_name="test",
            max_retries=3,
            base_delay_ms=5,
        )
        assert False, "Should have raised PermanentDatabaseError"
    except db_handler.PermanentDatabaseError:
        assert call_count == 1
        print(f"    ✓ Did not retry on permanent error (called once)")
    
    print("✓ All async retry logic tests passed!\n")


def test_decorator_retry():
    """Test handle_db_operation decorator with retry logic."""
    print("Testing decorator retry logic...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    from sqlalchemy.exc import OperationalError
    
    # Test 1: Sync decorator with successful operation
    print("  - Test 1: Sync decorator with successful operation")
    call_count = 0
    
    @db_handler.handle_db_operation("test_op", max_retries=2, base_delay_ms=10)
    def sync_successful_op():
        nonlocal call_count
        call_count += 1
        return "success"
    
    result = sync_successful_op()
    assert result == "success"
    assert call_count == 1
    print(f"    ✓ Sync decorator works, called once")
    
    # Test 2: Sync decorator with retry on transient error
    print("  - Test 2: Sync decorator with retry on transient error")
    call_count = 0
    
    @db_handler.handle_db_operation("test_op", max_retries=2, base_delay_ms=10)
    def sync_retry_op():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            exc = OperationalError("Deadlock", None, None)
            exc.orig = MagicMock(sqlstate='40001')
            raise exc
        return "success"
    
    result = sync_retry_op()
    assert result == "success"
    assert call_count == 2
    print(f"    ✓ Sync decorator retried and succeeded (2 attempts)")
    
    print("✓ All decorator retry tests passed!\n")


def test_safe_db_query_retry():
    """Test safe_db_query with retry logic."""
    print("Testing safe_db_query with retry logic...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    from sqlalchemy.exc import OperationalError
    
    mock_db = Mock()
    
    # Test 1: Successful query
    print("  - Test 1: Successful query")
    call_count = 0
    def successful_query():
        nonlocal call_count
        call_count += 1
        return {"id": 1, "name": "Test"}
    
    result = db_handler.safe_db_query(mock_db, successful_query, "test query")
    assert result == {"id": 1, "name": "Test"}
    assert call_count == 1
    print(f"    ✓ Query executed successfully on first attempt")
    
    # Test 2: Query with retry on transient error
    print("  - Test 2: Query with retry on transient error")
    call_count = 0
    def retry_query():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            exc = OperationalError("Lock timeout", None, None)
            exc.orig = MagicMock(sqlstate='55P03')
            raise exc
        return {"id": 2, "result": "retry_success"}
    
    result = db_handler.safe_db_query(
        mock_db, 
        retry_query, 
        "test query",
        max_retries=3,
        base_delay_ms=10
    )
    assert result == {"id": 2, "result": "retry_success"}
    assert call_count == 3
    print(f"    ✓ Query retried twice and succeeded (3 attempts total)")
    
    print("✓ All safe_db_query retry tests passed!\n")


def test_database_error_types():
    """Test different exception types and their handling."""
    print("Testing database error types...")
    
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')
    
    # Test 1: DatabaseConnectionError
    print("  - Test 1: DatabaseConnectionError base class")
    exc = db_handler.DatabaseConnectionError("Test error")
    assert str(exc) == "Test error"
    print("    ✓ Raised and caught correctly")
    
    # Test 2: TransientDatabaseError subclass
    print("  - Test 2: TransientDatabaseError subclass")
    exc = db_handler.TransientDatabaseError("Transient error")
    assert isinstance(exc, db_handler.DatabaseConnectionError)
    print("    ✓ Properly inherits from DatabaseConnectionError")
    
    # Test 3: PermanentDatabaseError subclass
    print("  - Test 3: PermanentDatabaseError subclass")
    exc = db_handler.PermanentDatabaseError("Permanent error")
    assert isinstance(exc, db_handler.DatabaseConnectionError)
    print("    ✓ Properly inherits from DatabaseConnectionError")
    
    print("✓ All database error type tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Database Error Handling with Transient Retry Tests (Issue #1229)")
    print("=" * 60 + "\n")
    
    test_database_error_types()
    test_transient_error_detection()
    test_exponential_backoff_calculation()
    test_retry_logic_sync()
    test_safe_db_query_retry()
    test_decorator_retry()
    
    # Run async tests
    asyncio.run(test_retry_logic_async())
    
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print("\nTransient failure retry implementation working correctly:")
    print("  - Transient error detection (SQLState codes)")
    print("  - Exponential backoff (100ms, 400ms, 1600ms)")
    print("  - Jitter to prevent thundering herd")
    print("  - Max retry attempts limit")
    print("  - Sync and async operation support")
    print("  - Permanent vs transient error classification")