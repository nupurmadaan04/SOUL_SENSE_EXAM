"""
Test for AsyncWorkerManager integration in main.py (#1219)
Tests memory leak prevention for long-lived async workers.
"""
import asyncio
import pytest
import gc
import psutil
import os
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_worker_manager_integration():
    """Test that AsyncWorkerManager properly manages background workers."""
    # Import the worker manager
    from backend.fastapi.api.services.worker_manager import AsyncWorkerManager

    # Create worker manager
    manager = AsyncWorkerManager()

    # Mock worker function
    worker_calls = []

    async def mock_worker():
        worker_calls.append("started")
        await asyncio.sleep(0.1)  # Simulate work
        worker_calls.append("finished")

    # Register worker
    await manager.register_worker(
        name="test_worker",
        worker_func=mock_worker,
        restart_on_failure=True,
        memory_threshold_mb=10.0,
        cleanup_interval_seconds=1
    )

    # Start worker and wait briefly
    await asyncio.sleep(0.2)

    # Check that worker was called
    assert "started" in worker_calls
    assert "finished" in worker_calls

    # Shutdown manager
    await manager.shutdown_all_workers()

    # Verify cleanup
    assert len(manager._workers) == 0


@pytest.mark.asyncio
async def test_memory_monitoring():
    """Test memory monitoring functionality."""
    from backend.fastapi.api.services.worker_manager import WorkerHealthMonitor

    monitor = WorkerHealthMonitor(memory_threshold_mb=1.0)

    # Get initial memory
    initial_memory = monitor._get_memory_usage_mb()

    # Allocate some memory
    big_list = [0] * 100000  # ~800KB

    # Check memory increased
    current_memory = monitor._get_memory_usage_mb()
    assert current_memory >= initial_memory

    # Clean up
    del big_list
    gc.collect()


@pytest.mark.asyncio
async def test_weak_reference_cache():
    """Test WeakReferenceCache prevents memory leaks."""
    from backend.fastapi.api.services.worker_manager import WeakReferenceCache

    cache = WeakReferenceCache()

    # Create objects
    class TestObject:
        def __init__(self, value):
            self.value = value

    obj1 = TestObject("test1")
    obj2 = TestObject("test2")

    # Cache objects
    cache.set("key1", obj1)
    cache.set("key2", obj2)

    # Verify retrieval
    assert cache.get("key1") is obj1
    assert cache.get("key2") is obj2

    # Delete strong references
    del obj1

    # Force garbage collection
    gc.collect()

    # Weak reference should be gone
    assert cache.get("key1") is None
    assert cache.get("key2") is obj2

    # Clean up
    del obj2
    gc.collect()


if __name__ == "__main__":
    # Run basic tests
    asyncio.run(test_worker_manager_integration())
    asyncio.run(test_memory_monitoring())
    asyncio.run(test_weak_reference_cache())
    print("All AsyncWorkerManager tests passed!")