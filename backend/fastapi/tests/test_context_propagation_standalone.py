"""
Standalone Test Cases for Request Context Propagation into Async Tasks
Issue #1363

This module provides standalone tests that don't depend on the full application.
"""

import asyncio
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, TypeVar
from unittest.mock import MagicMock

# Add parent directory to path for imports
sys.path.insert(0, 'c:\\Users\\abhij\\OneDrive\\Desktop\\SOUL_SENSE_EXAM\\backend\\fastapi')

# Import the context propagation module directly
from api.utils.context_propagation import (
    RequestContext,
    capture_request_context,
    propagate_context,
    propagate_context_sync,
    create_task_with_context,
    ContextPropagator,
    TracingContextFilter,
    request_id_ctx,
    user_id_ctx,
    correlation_id_ctx,
    get_request_id,
    get_user_id,
    get_correlation_id,
    get_full_context,
    set_context_vars,
    reset_context_vars,
)


# =============================================================================
# Helper Functions for Testing
# =============================================================================

async def async_task_function(data: str) -> dict:
    """Sample async task that checks context availability."""
    await asyncio.sleep(0.01)  # Simulate work
    return {
        "data": data,
        "request_id": get_request_id(),
        "user_id": get_user_id(),
        "correlation_id": get_correlation_id(),
    }


def sync_task_function(data: str) -> dict:
    """Sample sync task that checks context availability."""
    return {
        "data": data,
        "request_id": get_request_id(),
        "user_id": get_user_id(),
        "correlation_id": get_correlation_id(),
    }


async def task_with_retry_simulation(attempt: int = 0) -> dict:
    """Simulate a task that might retry."""
    context_data = get_full_context()
    context_data["attempt"] = attempt
    
    if attempt < 2:
        # Simulate retry
        await asyncio.sleep(0.01)
        return await task_with_retry_simulation(attempt + 1)
    
    return context_data


# =============================================================================
# Test Helper
# =============================================================================

def assert_equal(actual, expected, message=""):
    """Simple assertion helper."""
    if actual != expected:
        raise AssertionError(f"Expected {expected}, got {actual}. {message}")


def assert_true(value, message=""):
    """Assert that value is True."""
    if not value:
        raise AssertionError(f"Expected True, got {value}. {message}")


def assert_is_not_none(value, message=""):
    """Assert that value is not None."""
    if value is None:
        raise AssertionError(f"Expected non-None value. {message}")


def assert_is_none(value, message=""):
    """Assert that value is None."""
    if value is not None:
        raise AssertionError(f"Expected None, got {value}. {message}")


# =============================================================================
# Test Functions
# =============================================================================

async def test_request_context_creation():
    """Test RequestContext dataclass creation."""
    print("  - Testing RequestContext creation...")
    
    context = RequestContext(
        request_id="test-id-123",
        user_id=123,
        correlation_id="corr-12345",
        request_path="/api/v1/test",
        client_ip="192.168.1.1",
        trace_parent="00-trace-parent",
        metadata={"test_key": "test_value"}
    )
    
    assert_equal(context.request_id, "test-id-123")
    assert_equal(context.user_id, 123)
    assert_equal(context.correlation_id, "corr-12345")
    assert_equal(context.request_path, "/api/v1/test")
    print("    PASSED")


async def test_request_context_serialization():
    """Test RequestContext serialization and deserialization."""
    print("  - Testing RequestContext serialization...")
    
    original = RequestContext(
        request_id="test-id-123",
        user_id=123,
        correlation_id="corr-12345",
        request_path="/api/v1/test",
        metadata={"key": "value"}
    )
    
    # Serialize
    data = original.to_dict()
    assert_equal(data["request_id"], "test-id-123")
    assert_equal(data["user_id"], 123)
    assert_equal(data["metadata"]["key"], "value")
    
    # Deserialize
    restored = RequestContext.from_dict(data)
    assert_equal(restored.request_id, original.request_id)
    assert_equal(restored.user_id, original.user_id)
    assert_equal(restored.correlation_id, original.correlation_id)
    print("    PASSED")


async def test_capture_request_context():
    """Test context capture without request."""
    print("  - Testing capture_request_context...")
    
    context = capture_request_context()
    
    assert_is_not_none(context.request_id, "request_id should be generated")
    # Should be a valid UUID
    try:
        uuid.UUID(context.request_id)
    except ValueError:
        raise AssertionError("request_id should be a valid UUID")
    
    assert_is_none(context.user_id)
    assert_is_none(context.correlation_id)
    print("    PASSED")


async def test_propagate_context_to_async_function():
    """Test context propagation to async function."""
    print("  - Testing propagate_context to async function...")
    
    context = RequestContext(
        request_id="prop-test-id",
        user_id=42,
        correlation_id="prop-corr-id",
    )
    
    result = await propagate_context(context, async_task_function, "test_data")
    
    assert_equal(result["data"], "test_data")
    assert_equal(result["request_id"], "prop-test-id")
    assert_equal(result["user_id"], 42)
    assert_equal(result["correlation_id"], "prop-corr-id")
    print("    PASSED")


async def test_propagate_context_to_sync_function():
    """Test context propagation to sync function."""
    print("  - Testing propagate_context to sync function...")
    
    context = RequestContext(
        request_id="sync-test-id",
        user_id=99,
        correlation_id="sync-corr-id",
    )
    
    result = await propagate_context(context, sync_task_function, "sync_data")
    
    assert_equal(result["data"], "sync_data")
    assert_equal(result["request_id"], "sync-test-id")
    assert_equal(result["user_id"], 99)
    assert_equal(result["correlation_id"], "sync-corr-id")
    print("    PASSED")


async def test_propagate_context_sync():
    """Test synchronous context propagation."""
    print("  - Testing propagate_context_sync...")
    
    context = RequestContext(
        request_id="sync-prop-id",
        user_id=77,
    )
    
    result = propagate_context_sync(context, sync_task_function, "data")
    
    assert_equal(result["request_id"], "sync-prop-id")
    assert_equal(result["user_id"], 77)
    print("    PASSED")


async def test_context_isolation_between_tasks():
    """Test that contexts are isolated between concurrent tasks."""
    print("  - Testing context isolation between tasks...")
    
    context1 = RequestContext(request_id="id-1", user_id=1, correlation_id="corr-1")
    context2 = RequestContext(request_id="id-2", user_id=2, correlation_id="corr-2")
    
    async def run_task(delay):
        await asyncio.sleep(delay)
        return {
            "request_id": get_request_id(),
            "user_id": get_user_id(),
            "correlation_id": get_correlation_id(),
        }
    
    # Run tasks concurrently
    task1 = propagate_context(context1, run_task, 0.02)
    task2 = propagate_context(context2, run_task, 0.01)
    
    result1, result2 = await asyncio.gather(task1, task2)
    
    # Verify isolation
    assert_equal(result1["request_id"], "id-1")
    assert_equal(result1["user_id"], 1)
    assert_equal(result1["correlation_id"], "corr-1")
    
    assert_equal(result2["request_id"], "id-2")
    assert_equal(result2["user_id"], 2)
    assert_equal(result2["correlation_id"], "corr-2")
    print("    PASSED")


async def test_context_propagator_context_manager():
    """Test ContextPropagator context manager."""
    print("  - Testing ContextPropagator context manager...")
    
    context = RequestContext(request_id="ctx-mgr-id", user_id=55)
    
    # Before entering
    assert_is_none(get_request_id())
    
    async with ContextPropagator(context):
        assert_equal(get_request_id(), "ctx-mgr-id")
        assert_equal(get_user_id(), 55)
    
    # After exiting
    assert_is_none(get_request_id())
    print("    PASSED")


async def test_context_cleanup_on_exception():
    """Test that context is cleaned up even when task raises exception."""
    print("  - Testing context cleanup on exception...")
    
    context = RequestContext(request_id="exc-test-id", user_id=33)
    
    async def failing_task():
        assert_equal(get_request_id(), "exc-test-id")
        raise ValueError("Task failed")
    
    try:
        await propagate_context(context, failing_task)
    except ValueError:
        pass
    
    # Context should be cleaned up
    assert_is_none(get_request_id())
    print("    PASSED")


async def test_timeout_cancellation():
    """Test context handling with timeout/cancellation."""
    print("  - Testing timeout/cancellation handling...")
    
    context = RequestContext(request_id="timeout-test-id")
    
    async def slow_task():
        await asyncio.sleep(10)  # Will timeout
        return {"request_id": get_request_id()}
    
    try:
        await asyncio.wait_for(
            propagate_context(context, slow_task),
            timeout=0.1
        )
    except asyncio.TimeoutError:
        pass
    
    # Context should be cleaned up
    assert_is_none(get_request_id())
    print("    PASSED")


async def test_task_retry_preserves_context():
    """Test that context is preserved across task retries."""
    print("  - Testing context preservation across retries...")
    
    context = RequestContext(
        request_id="retry-test-id",
        user_id=88,
        correlation_id="retry-corr",
    )
    
    result = await propagate_context(context, task_with_retry_simulation, 0)
    
    # Verify context was preserved through retries
    assert_equal(result["request_id"], "retry-test-id")
    assert_equal(result["user_id"], 88)
    assert_equal(result["correlation_id"], "retry-corr")
    assert_equal(result["attempt"], 2)  # Reached final attempt
    print("    PASSED")


async def test_tracing_context_filter():
    """Test TracingContextFilter."""
    print("  - Testing TracingContextFilter...")
    
    filter_obj = TracingContextFilter()
    
    context = RequestContext(
        request_id="log-test-id",
        user_id=66,
        correlation_id="log-corr-id",
        trace_parent="00-log-trace",
    )
    
    # Set context
    set_context_vars(context)
    
    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply filter
    result = filter_obj.filter(record)
    assert_true(result, "Filter should return True")
    
    # Verify context was injected
    assert_equal(record.request_id, "log-test-id")
    assert_equal(record.user_id, 66)
    assert_equal(record.correlation_id, "log-corr-id")
    assert_equal(record.trace_parent, "00-log-trace")
    
    # Cleanup
    reset_context_vars(set_context_vars(context))
    print("    PASSED")


async def test_nested_context_propagation():
    """Test nested context propagation."""
    print("  - Testing nested context propagation...")
    
    outer_context = RequestContext(
        request_id="outer-id",
        user_id=100,
        correlation_id="outer-corr"
    )
    
    async def outer_task():
        outer_request_id = get_request_id()
        
        # Create inner context
        inner_context = RequestContext(
            request_id="inner-id",
            user_id=999,
            correlation_id="inner-corr"
        )
        
        async def inner_task():
            return {
                "request_id": get_request_id(),
                "user_id": get_user_id(),
            }
        
        inner_result = await propagate_context(inner_context, inner_task)
        
        # After inner task, outer context should be restored
        assert_equal(get_request_id(), outer_request_id)
        
        return {
            "outer_request_id": outer_request_id,
            "inner_result": inner_result
        }
    
    result = await propagate_context(outer_context, outer_task)
    
    assert_equal(result["outer_request_id"], "outer-id")
    assert_equal(result["inner_result"]["request_id"], "inner-id")
    assert_equal(result["inner_result"]["user_id"], 999)
    print("    PASSED")


async def test_concurrent_task_execution():
    """Test concurrent task execution with different contexts."""
    print("  - Testing concurrent task execution...")
    
    contexts = [
        RequestContext(request_id=f"id-{i}", user_id=i, correlation_id=f"corr-{i}")
        for i in range(5)
    ]
    
    async def task_with_context():
        await asyncio.sleep(0.01)
        return {
            "request_id": get_request_id(),
            "user_id": get_user_id(),
            "correlation_id": get_correlation_id(),
        }
    
    # Run all tasks concurrently
    tasks = [
        propagate_context(ctx, task_with_context)
        for ctx in contexts
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify each result matches its context
    for i, (ctx, result) in enumerate(zip(contexts, results)):
        assert_equal(result["request_id"], f"id-{i}")
        assert_equal(result["user_id"], i)
        assert_equal(result["correlation_id"], f"corr-{i}")
    
    print("    PASSED")


async def test_full_flow():
    """Test complete flow from context capture to task execution."""
    print("  - Testing full flow...")
    
    # 1. Capture context (simulating middleware)
    original_context = RequestContext(
        request_id="flow-test-id",
        user_id=42,
        correlation_id="flow-corr-123",
        request_path="/api/v1/export",
        client_ip="10.0.0.1",
        trace_parent="00-flow-trace-parent-01",
        metadata={"trigger": "user_action"}
    )
    
    # 2. Create task with context
    task_results = []
    
    async def background_processing_task(data):
        task_results.append({
            "data": data,
            "request_id": get_request_id(),
            "user_id": get_user_id(),
            "correlation_id": get_correlation_id(),
            "trace_parent": get_full_context().get("trace_parent"),
        })
        return {"status": "completed"}
    
    # 3. Execute task with context propagation
    await propagate_context(
        original_context,
        background_processing_task,
        {"export_type": "pdf"}
    )
    
    # 4. Verify context was propagated
    assert_equal(len(task_results), 1)
    result = task_results[0]
    
    assert_equal(result["request_id"], "flow-test-id")
    assert_equal(result["user_id"], 42)
    assert_equal(result["correlation_id"], "flow-corr-123")
    assert_equal(result["trace_parent"], "00-flow-trace-parent-01")
    assert_equal(result["data"], {"export_type": "pdf"})
    print("    PASSED")


# =============================================================================
# Main Test Runner
# =============================================================================

async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("REQUEST CONTEXT PROPAGATION TESTS - Issue #1363")
    print("=" * 70 + "\n")
    
    tests = [
        ("Context Creation", test_request_context_creation),
        ("Context Serialization", test_request_context_serialization),
        ("Capture Request Context", test_capture_request_context),
        ("Propagate to Async Function", test_propagate_context_to_async_function),
        ("Propagate to Sync Function", test_propagate_context_to_sync_function),
        ("Propagate Context Sync", test_propagate_context_sync),
        ("Context Isolation", test_context_isolation_between_tasks),
        ("Context Propagator", test_context_propagator_context_manager),
        ("Context Cleanup on Exception", test_context_cleanup_on_exception),
        ("Timeout/Cancellation", test_timeout_cancellation),
        ("Task Retry Preserves Context", test_task_retry_preserves_context),
        ("Tracing Context Filter", test_tracing_context_filter),
        ("Nested Context Propagation", test_nested_context_propagation),
        ("Concurrent Task Execution", test_concurrent_task_execution),
        ("Full Flow", test_full_flow),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"    FAILED: {e}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
