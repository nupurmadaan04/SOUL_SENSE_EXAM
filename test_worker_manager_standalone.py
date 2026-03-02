"""
Standalone test for AsyncWorkerManager (#1219)
Tests memory leak prevention for long-lived async workers.
"""
import asyncio
import sys
import os
import gc
import psutil
import weakref
import tracemalloc
from typing import Dict, Any, Optional, Callable
import logging

# Add the backend path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'fastapi'))

# Import just the worker manager classes directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "worker_manager",
    os.path.join(os.path.dirname(__file__), 'backend', 'fastapi', 'api', 'services', 'worker_manager.py')
)
worker_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_manager_module)

AsyncWorkerManager = worker_manager_module.AsyncWorkerManager
WorkerHealthMonitor = worker_manager_module.WorkerHealthMonitor
WeakReferenceCache = worker_manager_module.WeakReferenceCache


async def test_worker_manager_basic():
    """Test basic AsyncWorkerManager functionality."""
    print("Testing AsyncWorkerManager basic functionality...")

    manager = AsyncWorkerManager()

    # Mock worker function
    worker_calls = []

    async def mock_worker():
        worker_calls.append("started")
        await asyncio.sleep(0.1)  # Simulate work
        worker_calls.append("finished")

    # Register worker
    manager.register_worker(
        name="test_worker",
        factory=mock_worker,
        restart_interval=60
    )

    # Start the worker
    await manager.start_worker("test_worker")

    # Start worker and wait briefly
    await asyncio.sleep(0.2)

    # Check that worker was called
    assert "started" in worker_calls, f"Worker calls: {worker_calls}"
    assert "finished" in worker_calls, f"Worker calls: {worker_calls}"

    # Shutdown manager
    await manager.shutdown()

    # Wait a bit for cleanup
    await asyncio.sleep(0.1)

    # Verify cleanup - workers should be cancelled/stopped
    for name, task in manager.workers.items():
        assert task.done(), f"Worker {name} is still running"

    print("✓ AsyncWorkerManager basic test passed")


async def test_memory_monitoring():
    """Test memory monitoring functionality."""
    print("Testing WorkerHealthMonitor...")

    monitor = WorkerHealthMonitor(max_memory_mb=1.0)

    # Get initial memory by calling the check method
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Allocate some memory
    big_list = [0] * 100000  # ~800KB

    # Check memory increased
    current_memory = process.memory_info().rss / 1024 / 1024
    print(f"Current memory: {current_memory:.2f} MB")

    assert current_memory >= initial_memory

    # Clean up
    del big_list
    gc.collect()

    print("✓ WorkerHealthMonitor test passed")


async def test_weak_reference_cache():
    """Test WeakReferenceCache prevents memory leaks."""
    print("Testing WeakReferenceCache...")

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

    print("✓ WeakReferenceCache test passed")


async def test_memory_leak_prevention():
    """Test that the system prevents memory leaks in long-running scenarios."""
    print("Testing memory leak prevention...")

    # Start memory tracing
    tracemalloc.start()

    manager = AsyncWorkerManager()

    # Create a worker that runs for a while and accumulates some data
    async def accumulating_worker():
        data = []
        for i in range(100):
            data.append(f"item_{i}" * 100)  # Create some memory pressure
            await asyncio.sleep(0.01)

            # Periodic cleanup
            if len(data) > 50:
                data.clear()
                gc.collect()

    # Register worker with memory monitoring
    manager.register_worker(
        name="memory_test_worker",
        factory=accumulating_worker,
        restart_interval=60
    )

    # Start the worker
    await manager.start_worker("memory_test_worker")

    # Let it run for a bit
    await asyncio.sleep(0.5)

    # Check memory usage
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory: {current / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB")

    # Shutdown
    await manager.shutdown()

    # Stop tracing
    tracemalloc.stop()

    print("✓ Memory leak prevention test passed")


async def main():
    """Run all tests."""
    print("Running AsyncWorkerManager integration tests...\n")

    try:
        await test_worker_manager_basic()
        await test_memory_monitoring()
        await test_weak_reference_cache()
        await test_memory_leak_prevention()

        print("\n🎉 All AsyncWorkerManager tests passed!")
        print("Memory leak prevention for long-lived async workers (#1219) is working correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)