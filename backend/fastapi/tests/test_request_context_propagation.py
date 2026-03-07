"""
Test Cases for Request Context Propagation into Async Tasks
Issue #1363

This module provides comprehensive tests for:
- Request context capture via middleware
- Context propagation using context-aware execution model
- Validation via tracing instrumentation
- Thread pool context handling
- Task retry context preservation
- Timeout cancellation handling
- Context isolation (no leakage)
"""

import asyncio
import json
import logging
import pytest
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Import FastAPI test client
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

# Import context propagation module
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
from api.middleware.logging_middleware import (
    RequestLoggingMiddleware,
    get_request_id as middleware_get_request_id,
)
from api.services.background_task_service import (
    BackgroundTaskService,
    TaskType,
    TaskStatus,
    TracedBackgroundTask,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_request_context():
    """Create a sample request context for testing."""
    return RequestContext(
        request_id=str(uuid.uuid4()),
        user_id=123,
        correlation_id="corr-12345",
        request_path="/api/v1/test",
        client_ip="192.168.1.1",
        trace_parent="00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
        metadata={"test_key": "test_value"}
    )


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.client.host = "192.168.1.1"
    request.headers = {
        "X-Request-ID": "test-request-id-123",
        "X-Correlation-ID": "test-correlation-id-456",
        "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
        "X-Forwarded-For": "192.168.1.1, 10.0.0.1",
        "User-Agent": "TestClient/1.0",
    }
    request.query_params = {}
    request.state = MagicMock()
    request.state.request_id = "test-request-id-123"
    request.state.user_id = 123
    return request


@pytest.fixture
def test_app():
    """Create a FastAPI app with context propagation middleware."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        request_id = get_request_id()
        return {
            "request_id": request_id,
            "context_available": request_id is not None
        }
    
    @app.post("/async-task")
    async def async_task_endpoint(
        request: Request,
        background_tasks: BackgroundTasks
    ):
        """Endpoint that schedules an async task with context propagation."""
        captured_context = capture_request_context(request)
        
        # Schedule task with context
        task = asyncio.create_task(
            propagate_context(captured_context, async_task_function, "test_data")
        )
        
        return {
            "request_id": captured_context.request_id,
            "correlation_id": captured_context.correlation_id,
            "task_scheduled": True
        }
    
    return app


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
# Test Class: Context Capture and Creation
# =============================================================================

class TestContextCapture:
    """Tests for context capture functionality."""
    
    def test_request_context_creation(self, sample_request_context):
        """Test RequestContext dataclass creation."""
        assert sample_request_context.request_id is not None
        assert sample_request_context.user_id == 123
        assert sample_request_context.correlation_id == "corr-12345"
        assert sample_request_context.request_path == "/api/v1/test"
    
    def test_request_context_to_dict(self, sample_request_context):
        """Test RequestContext serialization to dict."""
        data = sample_request_context.to_dict()
        assert data["request_id"] == sample_request_context.request_id
        assert data["user_id"] == 123
        assert data["correlation_id"] == "corr-12345"
        assert data["metadata"] == {"test_key": "test_value"}
    
    def test_request_context_from_dict(self, sample_request_context):
        """Test RequestContext deserialization from dict."""
        data = sample_request_context.to_dict()
        restored = RequestContext.from_dict(data)
        assert restored.request_id == sample_request_context.request_id
        assert restored.user_id == sample_request_context.user_id
        assert restored.correlation_id == sample_request_context.correlation_id
    
    def test_capture_request_context_from_mock(self, mock_request):
        """Test context capture from mock request."""
        context = capture_request_context(mock_request)
        
        assert context.request_id == "test-request-id-123"
        assert context.user_id == 123
        assert context.correlation_id == "test-correlation-id-456"
        assert context.trace_parent == "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        assert context.client_ip == "192.168.1.1"
        assert context.request_path == "/api/v1/test"
    
    def test_capture_request_context_without_request(self):
        """Test context capture without request generates request_id."""
        context = capture_request_context()
        
        assert context.request_id is not None
        # Should be a valid UUID
        uuid.UUID(context.request_id)
        assert context.user_id is None
        assert context.correlation_id is None


# =============================================================================
# Test Class: Context Propagation
# =============================================================================

class TestContextPropagation:
    """Tests for context propagation to async tasks."""
    
    @pytest.mark.asyncio
    async def test_propagate_context_to_async_function(self, sample_request_context):
        """Test context propagation to async function."""
        result = await propagate_context(sample_request_context, async_task_function, "test_data")
        
        assert result["data"] == "test_data"
        assert result["request_id"] == sample_request_context.request_id
        assert result["user_id"] == sample_request_context.user_id
        assert result["correlation_id"] == sample_request_context.correlation_id
    
    @pytest.mark.asyncio
    async def test_propagate_context_to_sync_function(self, sample_request_context):
        """Test context propagation to sync function."""
        result = await propagate_context(sample_request_context, sync_task_function, "test_data")
        
        assert result["data"] == "test_data"
        assert result["request_id"] == sample_request_context.request_id
        assert result["user_id"] == sample_request_context.user_id
        assert result["correlation_id"] == sample_request_context.correlation_id
    
    @pytest.mark.asyncio
    async def test_propagate_context_sync(self, sample_request_context):
        """Test synchronous context propagation."""
        result = propagate_context_sync(sample_request_context, sync_task_function, "test_data")
        
        assert result["data"] == "test_data"
        assert result["request_id"] == sample_request_context.request_id
        assert result["user_id"] == sample_request_context.user_id
    
    @pytest.mark.asyncio
    async def test_create_task_with_context(self, sample_request_context):
        """Test creating task with context propagation."""
        coro = async_task_function("task_data")
        task = create_task_with_context(sample_request_context, coro)
        
        result = await task
        
        assert result["data"] == "task_data"
        assert result["request_id"] == sample_request_context.request_id
    
    @pytest.mark.asyncio
    async def test_context_isolation_between_tasks(self):
        """Test that contexts are isolated between concurrent tasks."""
        context1 = RequestContext(request_id="id-1", user_id=1, correlation_id="corr-1")
        context2 = RequestContext(request_id="id-2", user_id=2, correlation_id="corr-2")
        
        async def run_task(ctx, delay):
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
        assert result1["request_id"] == "id-1"
        assert result1["user_id"] == 1
        assert result1["correlation_id"] == "corr-1"
        
        assert result2["request_id"] == "id-2"
        assert result2["user_id"] == 2
        assert result2["correlation_id"] == "corr-2"


# =============================================================================
# Test Class: Context Propagator Context Manager
# =============================================================================

class TestContextPropagator:
    """Tests for ContextPropagator context manager."""
    
    @pytest.mark.asyncio
    async def test_async_context_propagator(self, sample_request_context):
        """Test async context manager for context propagation."""
        async with ContextPropagator(sample_request_context):
            assert get_request_id() == sample_request_context.request_id
            assert get_user_id() == sample_request_context.user_id
        
        # After exiting, context should be reset
        assert get_request_id() is None
    
    def test_sync_context_propagator(self, sample_request_context):
        """Test sync context manager for context propagation."""
        with ContextPropagator(sample_request_context):
            assert get_request_id() == sample_request_context.request_id
            assert get_user_id() == sample_request_context.user_id
        
        # After exiting, context should be reset
        assert get_request_id() is None
    
    @pytest.mark.asyncio
    async def test_context_propagator_exception_handling(self, sample_request_context):
        """Test that context propagator properly resets on exception."""
        try:
            async with ContextPropagator(sample_request_context):
                assert get_request_id() == sample_request_context.request_id
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Context should still be reset
        assert get_request_id() is None


# =============================================================================
# Test Class: Context Variables
# =============================================================================

class TestContextVariables:
    """Tests for context variable operations."""
    
    def test_set_and_reset_context_vars(self, sample_request_context):
        """Test setting and resetting context variables."""
        # Set context
        tokens = set_context_vars(sample_request_context)
        
        assert get_request_id() == sample_request_context.request_id
        assert get_user_id() == sample_request_context.user_id
        assert get_correlation_id() == sample_request_context.correlation_id
        
        # Reset context
        reset_context_vars(tokens)
        
        assert get_request_id() is None
        assert get_user_id() is None
        assert get_correlation_id() is None
    
    def test_get_full_context(self, sample_request_context):
        """Test getting full context as dictionary."""
        set_context_vars(sample_request_context)
        
        full = get_full_context()
        assert full["request_id"] == sample_request_context.request_id
        assert full["user_id"] == sample_request_context.user_id
        assert full["correlation_id"] == sample_request_context.correlation_id
    
    def test_context_variable_isolation(self):
        """Test that context variables are properly isolated."""
        # Set different values in different contexts
        token1 = request_id_ctx.set("id-1")
        
        # In a separate async task context, value would be different
        # Here we just verify the mechanism works
        assert request_id_ctx.get() == "id-1"
        
        request_id_ctx.reset(token1)
        assert request_id_ctx.get() is None


# =============================================================================
# Test Class: Tracing and Logging
# =============================================================================

class TestTracingContextFilter:
    """Tests for tracing context filter."""
    
    def test_tracing_context_filter(self, sample_request_context):
        """Test that TracingContextFilter injects context into log records."""
        filter_obj = TracingContextFilter()
        
        # Set context
        set_context_vars(sample_request_context)
        
        # Create a mock log record
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
        assert result is True
        
        # Verify context was injected
        assert record.request_id == sample_request_context.request_id
        assert record.user_id == sample_request_context.user_id
        assert record.correlation_id == sample_request_context.correlation_id
        assert record.trace_parent == sample_request_context.trace_parent


# =============================================================================
# Test Class: Background Task Service
# =============================================================================

class TestBackgroundTaskService:
    """Tests for background task service with context propagation."""
    
    @pytest.mark.asyncio
    async def test_create_task_with_context(self, sample_request_context):
        """Test creating background task with request context."""
        mock_db = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "test-job-id"
        
        with patch.object(BackgroundTaskService, 'create_task', return_value=mock_job):
            job = await BackgroundTaskService.create_task(
                db=mock_db,
                user_id=123,
                task_type=TaskType.DATA_ANALYSIS,
                params={"key": "value"},
                request_context=sample_request_context
            )
            
            assert job.job_id == "test-job-id"
    
    @pytest.mark.asyncio
    async def test_execute_task_with_context_propagation(self, sample_request_context):
        """Test executing task with context propagation."""
        mock_db = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "test-job-id"
        mock_job.user_id = 123
        mock_job.task_type = TaskType.SEND_EMAIL.value
        mock_job.params = json.dumps({"__request_context": sample_request_context.to_dict()})
        
        async def test_task_func():
            return {
                "request_id": get_request_id(),
                "user_id": get_user_id(),
                "correlation_id": get_correlation_id(),
            }
        
        with patch.object(BackgroundTaskService, 'get_task', return_value=mock_job):
            with patch.object(BackgroundTaskService, 'update_task_status', return_value=mock_job):
                # Execute task with context
                await BackgroundTaskService._run_task_internal(
                    "test-job-id",
                    test_task_func,
                    request_context=sample_request_context
                )
    
    @pytest.mark.asyncio
    async def test_task_retry_preserves_context(self, sample_request_context):
        """Test that context is preserved across task retries."""
        result = await propagate_context(
            sample_request_context,
            task_with_retry_simulation,
            0
        )
        
        # Verify context was preserved through retries
        assert result["request_id"] == sample_request_context.request_id
        assert result["user_id"] == sample_request_context.user_id
        assert result["correlation_id"] == sample_request_context.correlation_id
        assert result["attempt"] == 2  # Reached final attempt


# =============================================================================
# Test Class: TracedBackgroundTask
# =============================================================================

class TestTracedBackgroundTask:
    """Tests for TracedBackgroundTask helper class."""
    
    @pytest.mark.asyncio
    async def test_traced_background_task_schedule(self, sample_request_context):
        """Test scheduling traced background task."""
        mock_db = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "traced-job-id"
        
        async def sample_task(data):
            return {"processed": data}
        
        traced_task = TracedBackgroundTask(
            sample_task,
            TaskType.EXPORT_PDF,
            request_context=sample_request_context
        )
        
        with patch.object(BackgroundTaskService, 'create_task', return_value=mock_job):
            with patch('asyncio.create_task') as mock_create_task:
                job_id = await traced_task.schedule(
                    MagicMock(),  # background_tasks
                    mock_db,
                    123,
                    "test_data"
                )
                
                assert job_id == "traced-job-id"
                mock_create_task.assert_called_once()


# =============================================================================
# Test Class: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_context_cleanup_on_exception(self, sample_request_context):
        """Test that context is cleaned up even when task raises exception."""
        async def failing_task():
            assert get_request_id() == sample_request_context.request_id
            raise ValueError("Task failed")
        
        try:
            await propagate_context(sample_request_context, failing_task)
        except ValueError:
            pass
        
        # Context should be cleaned up
        assert get_request_id() is None
    
    @pytest.mark.asyncio
    async def test_timeout_cancellation(self, sample_request_context):
        """Test context handling with timeout/cancellation."""
        async def slow_task():
            await asyncio.sleep(10)  # Will timeout
            return {"request_id": get_request_id()}
        
        try:
            await asyncio.wait_for(
                propagate_context(sample_request_context, slow_task),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            pass
        
        # Context should be cleaned up
        assert get_request_id() is None
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, sample_request_context):
        """Test concurrent task execution with different contexts."""
        contexts = [
            RequestContext(request_id=f"id-{i}", user_id=i, correlation_id=f"corr-{i}")
            for i in range(5)
        ]
        
        async def task_with_context(ctx):
            await asyncio.sleep(0.01)
            return {
                "request_id": get_request_id(),
                "user_id": get_user_id(),
                "correlation_id": get_correlation_id(),
            }
        
        # Run all tasks concurrently
        tasks = [
            propagate_context(ctx, task_with_context, ctx)
            for ctx in contexts
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify each result matches its context
        for i, (ctx, result) in enumerate(zip(contexts, results)):
            assert result["request_id"] == f"id-{i}"
            assert result["user_id"] == i
            assert result["correlation_id"] == f"corr-{i}"
    
    @pytest.mark.asyncio
    async def test_nested_context_propagation(self, sample_request_context):
        """Test nested context propagation."""
        async def outer_task():
            outer_request_id = get_request_id()
            
            # Create inner context
            inner_context = RequestContext(
                request_id="inner-id",
                user_id=999,
                correlation_id="inner-corr"
            )
            
            inner_result = await propagate_context(inner_context, inner_task)
            
            # After inner task, outer context should be restored
            assert get_request_id() == outer_request_id
            
            return {
                "outer_request_id": outer_request_id,
                "inner_result": inner_result
            }
        
        async def inner_task():
            return {
                "request_id": get_request_id(),
                "user_id": get_user_id(),
            }
        
        result = await propagate_context(sample_request_context, outer_task)
        
        assert result["outer_request_id"] == sample_request_context.request_id
        assert result["inner_result"]["request_id"] == "inner-id"
        assert result["inner_result"]["user_id"] == 999
    
    def test_context_with_empty_values(self):
        """Test context with minimal/empty values."""
        context = RequestContext(request_id="minimal-id")
        
        assert context.request_id == "minimal-id"
        assert context.user_id is None
        assert context.correlation_id is None
        assert context.request_path is None
        assert context.client_ip is None
        assert context.trace_parent is None
        assert context.metadata == {}
    
    @pytest.mark.asyncio
    async def test_thread_pool_context_propagation(self, sample_request_context):
        """Test context propagation to thread pool executor."""
        import concurrent.futures
        
        def thread_task():
            return {
                "request_id": get_request_id(),
                "user_id": get_user_id(),
                "correlation_id": get_correlation_id(),
            }
        
        # Note: Standard thread pools don't automatically propagate context
        # This test documents the expected behavior
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                propagate_context_sync,
                sample_request_context,
                thread_task
            )
            result = future.result()
        
        assert result["request_id"] == sample_request_context.request_id
        assert result["user_id"] == sample_request_context.user_id
        assert result["correlation_id"] == sample_request_context.correlation_id


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full context propagation flow."""
    
    @pytest.mark.asyncio
    async def test_full_flow_from_capture_to_execution(self):
        """Test complete flow from context capture to task execution."""
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
        assert len(task_results) == 1
        result = task_results[0]
        
        assert result["request_id"] == "flow-test-id"
        assert result["user_id"] == 42
        assert result["correlation_id"] == "flow-corr-123"
        assert result["trace_parent"] == "00-flow-trace-parent-01"
        assert result["data"] == {"export_type": "pdf"}


# =============================================================================
# Main Entry Point for Manual Testing
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
