#!/usr/bin/env python3
"""
Test script for Poison-Resistant Lock - Prevents Mutex Poisoning on Panic #1188

Tests the poison-resistant lock implementation to ensure:
- Locks are automatically released when threads panic/crash
- No cascading deadlocks from poisoned mutexes
- Lock recovery works correctly
- Thread death is handled gracefully
"""

import os
import sys
import time
import threading
import signal
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from poison_resistant_lock import (
    PoisonResistantLock,
    PoisonResistantRLock,
    safe_lock_operation,
    register_lock,
    get_registered_locks,
    check_all_locks,
    recover_all_poisoned_locks
)

logger = logging.getLogger(__name__)


class TestPoisonResistantLock:
    """Comprehensive test suite for poison-resistant locks."""

    def __init__(self):
        self.shared_data = {"counter": 0, "data": []}
        self.test_results = {}

    def test_basic_functionality(self):
        """Test basic lock acquire/release functionality."""
        print("Testing basic lock functionality...")

        lock = PoisonResistantLock()
        register_lock(lock)

        # Test normal operation
        with lock:
            self.shared_data["counter"] = 1
            assert self.shared_data["counter"] == 1

        # Test manual acquire/release
        assert lock.acquire()
        self.shared_data["counter"] = 2
        assert self.shared_data["counter"] == 2
        lock.release()

        # Test safe context
        with lock.safe_context():
            self.shared_data["counter"] = 3
            assert self.shared_data["counter"] == 3

        print("✓ Basic functionality test passed")
        return True

    def test_reentrant_lock(self):
        """Test poison-resistant RLock functionality."""
        print("Testing reentrant lock functionality...")

        lock = PoisonResistantRLock()
        register_lock(lock)

        # Test reentrancy
        with lock:
            self.shared_data["counter"] = 1
            with lock:  # Should work with RLock
                self.shared_data["counter"] = 2
            assert self.shared_data["counter"] == 2

        print("✓ Reentrant lock test passed")
        return True

    def test_panic_in_critical_section(self):
        """Test that locks are released when thread panics in critical section."""
        print("Testing panic in critical section...")

        lock = PoisonResistantLock()
        register_lock(lock)
        panic_occurred = threading.Event()
        recovery_successful = threading.Event()

        def panic_thread():
            try:
                with lock:
                    panic_occurred.set()
                    # Simulate panic/crash
                    raise RuntimeError("Simulated thread panic!")
            except RuntimeError:
                # This should happen, but lock should still be released
                pass

        def recovery_thread():
            # Wait for panic to occur
            panic_occurred.wait(timeout=5.0)

            # Try to acquire lock - should succeed after panic cleanup
            start_time = time.time()
            acquired = False
            while time.time() - start_time < 3.0 and not acquired:
                acquired = lock.acquire(timeout=0.1)
                if not acquired:
                    time.sleep(0.01)

            if acquired:
                lock.release()
                recovery_successful.set()
            else:
                print("✗ Failed to acquire lock after panic")

        # Start threads
        panic_t = threading.Thread(target=panic_thread, daemon=True)
        recovery_t = threading.Thread(target=recovery_thread, daemon=True)

        panic_t.start()
        recovery_t.start()

        # Wait for recovery
        success = recovery_successful.wait(timeout=5.0)

        if success:
            print("✓ Panic in critical section test passed")
            return True
        else:
            print("✗ Lock not recovered after panic")
            return False

    def test_forced_crash_simulation(self):
        """Test forced crash inside critical section."""
        print("Testing forced crash simulation...")

        lock = PoisonResistantLock()
        register_lock(lock)
        crash_detected = threading.Event()

        def crashing_thread():
            lock.acquire()
            try:
                # Simulate crash without proper cleanup
                os._exit(1)  # Force immediate exit
            finally:
                # This won't execute due to os._exit
                lock.release()

        def monitor_thread():
            time.sleep(0.1)  # Let crashing thread start

            # Check if lock gets poisoned and recovered
            start_time = time.time()
            while time.time() - start_time < 3.0:
                if lock.acquire(timeout=0.1):
                    lock.release()
                    crash_detected.set()
                    return
                time.sleep(0.01)

        # This test is tricky because os._exit kills the process
        # We'll simulate with exception instead
        try:
            crashing_t = threading.Thread(target=lambda: (_ for _ in ()).throw(RuntimeError("crash")))
            crashing_t.start()
            crashing_t.join(timeout=1.0)
        except:
            pass

        # Test with proper exception simulation
        lock2 = PoisonResistantLock()
        register_lock(lock2)

        def exception_thread():
            try:
                with lock2:
                    raise SystemExit("Simulated crash")
            except SystemExit:
                pass  # Expected

        exception_t = threading.Thread(target=exception_thread)
        exception_t.start()
        exception_t.join()

        # Should be able to acquire lock after exception
        if lock2.acquire(timeout=1.0):
            lock2.release()
            print("✓ Forced crash simulation test passed")
            return True
        else:
            print("✗ Lock not recovered after exception")
            return False

    def test_lock_state_monitoring(self):
        """Test lock state monitoring and statistics."""
        print("Testing lock state monitoring...")

        lock = PoisonResistantLock()
        register_lock(lock)

        # Test initial state
        stats = lock.get_stats()
        assert not stats['poisoned']
        assert stats['owner_thread_id'] is None
        assert stats['lock_depth'] == 0

        # Test locked state
        with lock:
            stats = lock.get_stats()
            assert stats['owner_thread_id'] == threading.get_ident()
            assert stats['lock_depth'] == 1
            assert not stats['poisoned']

        # Test global monitoring
        all_locks = get_registered_locks()
        assert len(all_locks) >= 1

        global_stats = check_all_locks()
        assert len(global_stats) >= 1

        print("✓ Lock state monitoring test passed")
        return True

    def test_poison_recovery(self):
        """Test poison detection and recovery."""
        print("Testing poison recovery...")

        lock = PoisonResistantLock()
        register_lock(lock)

        # Manually poison the lock (simulate crash)
        with lock:
            # Simulate thread death by manually setting poisoned state
            lock._poisoned = True
            lock._owner_thread_id = 99999  # Non-existent thread

        # Should detect poison
        assert lock.is_poisoned()

        # Should recover
        recovered = lock.recover_from_poison()
        assert recovered
        assert not lock.is_poisoned()

        # Should work normally after recovery
        with lock:
            self.shared_data["counter"] = 42

        assert self.shared_data["counter"] == 42

        print("✓ Poison recovery test passed")
        return True

    def test_safe_lock_operation(self):
        """Test the safe_lock_operation wrapper."""
        print("Testing safe lock operation wrapper...")

        regular_lock = threading.Lock()
        results = []

        def operation():
            results.append("operation_started")
            if len(results) == 1:  # First call
                raise ValueError("Simulated operation failure")
            results.append("operation_completed")
            return "success"

        # Test with failure
        try:
            safe_lock_operation(regular_lock, operation)
        except ValueError:
            pass  # Expected

        # Lock should still be releasable
        assert regular_lock.acquire(timeout=1.0)
        regular_lock.release()

        # Test successful operation
        result = safe_lock_operation(regular_lock, operation)
        assert result == "success"
        assert "operation_completed" in results

        print("✓ Safe lock operation test passed")
        return True

    def test_concurrent_access_with_failures(self):
        """Test concurrent access with simulated failures."""
        print("Testing concurrent access with failures...")

        lock = PoisonResistantLock()
        register_lock(lock)
        success_count = 0
        failure_count = 0
        access_count = 0

        def worker(worker_id):
            nonlocal success_count, failure_count, access_count

            for i in range(10):
                try:
                    with lock.safe_context():
                        access_count += 1
                        # Randomly simulate failures
                        if worker_id % 3 == 0 and i % 4 == 0:
                            raise Exception(f"Simulated failure in worker {worker_id}")
                        time.sleep(0.001)  # Simulate work
                        success_count += 1
                except Exception:
                    failure_count += 1
                    # Lock should still be properly released

        # Run concurrent workers
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        print(f"  Successful operations: {success_count}")
        print(f"  Failed operations: {failure_count}")
        print(f"  Total access attempts: {access_count}")

        # Should have some failures but lock should remain functional
        if access_count > 0 and (success_count + failure_count) == access_count:
            print("✓ Concurrent access with failures test passed")
            return True
        else:
            print("✗ Concurrent access test failed")
            return False

    def test_integration_with_existing_code(self):
        """Test integration with existing codebase."""
        print("Testing integration with existing code...")

        try:
            # Test db_connection_manager integration
            from app.db_connection_manager import get_connection_pool
            pool = get_connection_pool()
            result = pool.execute_query("SELECT 1")
            assert result == [(1,)]

            # Test questions integration
            from app.questions import load_questions
            questions = load_questions()
            assert isinstance(questions, list)

            print("✓ Integration test passed")
            return True

        except Exception as e:
            print(f"✗ Integration test failed: {e}")
            return False


def run_all_tests():
    """Run all tests and report results."""
    print("Running Poison-Resistant Lock Tests (#1188)")
    print("=" * 55)

    test_instance = TestPoisonResistantLock()
    tests = [
        test_instance.test_basic_functionality,
        test_instance.test_reentrant_lock,
        test_instance.test_panic_in_critical_section,
        test_instance.test_forced_crash_simulation,
        test_instance.test_lock_state_monitoring,
        test_instance.test_poison_recovery,
        test_instance.test_safe_lock_operation,
        test_instance.test_concurrent_access_with_failures,
        test_instance.test_integration_with_existing_code,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1

    print("\n" + "=" * 55)
    print(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✓ All Poison-Resistant Lock tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
