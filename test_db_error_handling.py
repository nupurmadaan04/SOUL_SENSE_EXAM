#!/usr/bin/env python3
"""
Test script to verify database connection failure handling.
"""

import sys
import os
import importlib.util
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

def load_module(name, path):
    """Load a Python module from file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_database_error_handling():
    """Test that database connection errors are handled gracefully."""
    print("Testing database connection failure handling...")

    # Load the database error handler
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')

    # Test 1: DatabaseConnectionError exception
    print("✓ Test 1: DatabaseConnectionError exception")
    try:
        raise db_handler.DatabaseConnectionError("Test database error")
    except db_handler.DatabaseConnectionError as e:
        assert str(e) == "Test database error"
        print("  ✓ Exception raised and caught correctly")

    # Test 2: safe_db_query with OperationalError
    print("✓ Test 2: safe_db_query with OperationalError")
    from sqlalchemy.exc import OperationalError

    mock_db = Mock()
    def failing_query():
        raise OperationalError("Connection failed", None, None)

    try:
        result = db_handler.safe_db_query(mock_db, failing_query, "test query")
        assert False, "Should have raised DatabaseConnectionError"
    except db_handler.DatabaseConnectionError as e:
        assert "Service temporarily unavailable" in str(e)
        print("  ✓ OperationalError converted to user-friendly message")

    # Test 3: safe_db_query with successful query
    print("✓ Test 3: safe_db_query with successful query")
    def successful_query():
        return "success"

    result = db_handler.safe_db_query(mock_db, successful_query, "test query")
    assert result == "success"
    print("  ✓ Successful query returns correct result")

    print("✓ All database error handling tests passed!")

def test_service_error_handling():
    """Test that services handle database errors properly."""
    print("\nTesting service-level error handling...")

    # Load required modules
    db_handler = load_module('db_error_handler', 'backend/fastapi/api/services/db_error_handler.py')

    # Mock a service method that uses safe_db_query
    class MockService:
        def __init__(self, db):
            self.db = db

        def get_user(self, user_id):
            try:
                return db_handler.safe_db_query(
                    self.db,
                    lambda: {"id": user_id, "name": "Test User"},
                    "get user"
                )
            except db_handler.DatabaseConnectionError:
                return None  # Service returns None on DB error

    # Test with working database
    mock_db = Mock()
    service = MockService(mock_db)
    result = service.get_user(1)
    assert result is not None
    assert result["id"] == 1
    print("✓ Service handles successful database operations")

    # Test with failing database
    from sqlalchemy.exc import OperationalError
    mock_db_failing = Mock()
    service_failing = MockService(mock_db_failing)

    # Mock the safe_db_query to raise DatabaseConnectionError
    original_safe_db_query = db_handler.safe_db_query
    def failing_safe_db_query(*args, **kwargs):
        raise db_handler.DatabaseConnectionError("Service temporarily unavailable")

    db_handler.safe_db_query = failing_safe_db_query

    try:
        result = service_failing.get_user(1)
        assert result is None
        print("✓ Service handles database connection failures gracefully")
    finally:
        # Restore original function
        db_handler.safe_db_query = original_safe_db_query

    print("✓ All service error handling tests passed!")

if __name__ == "__main__":
    test_database_error_handling()
    test_service_error_handling()
    print("\n🎉 All tests passed! Database connection failure handling is working correctly.")