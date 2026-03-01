import unittest
from unittest.mock import MagicMock, patch
import time
import threading
import redis
from backend.fastapi.api.utils.distributed_lock import DistributedLock, DistributedLockError

class TestDistributedLock(unittest.TestCase):
    def setUp(self):
        # Mock settings for testing
        self.mock_settings = MagicMock()
        self.mock_settings.redis_host = "localhost"
        self.mock_settings.redis_port = 6379
        self.mock_settings.redis_password = None
        self.mock_settings.redis_db = 0
        self.mock_settings.redis_url = None
        
        # Patch the settings instance
        self.settings_patcher = patch('backend.fastapi.api.utils.distributed_lock.get_settings_instance', return_value=self.mock_settings)
        self.settings_patcher.start()

        # Mock Redis client
        self.mock_redis_patcher = patch('backend.fastapi.api.utils.distributed_lock.redis.Redis')
        self.mock_redis = self.mock_redis_patcher.start()
        self.mock_redis_instance = self.mock_redis.return_value
        
        # Mock redis.from_url just in case
        self.mock_redis_url_patcher = patch('backend.fastapi.api.utils.distributed_lock.redis.from_url')
        self.mock_redis_url = self.mock_redis_url_patcher.start()
        self.mock_redis_url.return_value = self.mock_redis_instance

        # Mock Redlock manager
        self.mock_redlock_patcher = patch('backend.fastapi.api.utils.distributed_lock.Redlock')
        self.mock_redlock = self.mock_redlock_patcher.start()
        self.mock_redlock_manager = self.mock_redlock.return_value

    def tearDown(self):
        self.settings_patcher.stop()
        self.mock_redis_patcher.stop()
        self.mock_redis_url_patcher.stop()
        self.mock_redlock_patcher.stop()

    def test_acquire_lock_success(self):
        """Test successful lock acquisition."""
        lock_key = {"resource": "lock:resource1", "key": "random_val"}
        self.mock_redlock_manager.lock.return_value = lock_key
        self.mock_redis_instance.incr.return_value = 1
        
        lock = DistributedLock("resource1")
        acquired = lock.acquire()
        
        self.assertTrue(acquired)
        self.assertEqual(lock.get_fencing_token(), 1)
        self.mock_redlock_manager.lock.assert_called_with("lock:resource1", 30000)
        self.mock_redis_instance.incr.assert_called_with("fencing:lock:resource1")

    def test_acquire_lock_failure(self):
        """Test failed lock acquisition."""
        self.mock_redlock_manager.lock.return_value = None
        
        lock = DistributedLock("resource1")
        acquired = lock.acquire()
        
        self.assertFalse(acquired)
        self.assertIsNone(lock.get_fencing_token())

    def test_lock_release(self):
        """Test lock release."""
        lock_key = {"resource": "lock:resource1", "key": "random_val"}
        self.mock_redlock_manager.lock.return_value = lock_key
        
        lock = DistributedLock("resource1")
        lock.acquire()
        lock.release()
        
        self.mock_redlock_manager.unlock.assert_called_with(lock_key)
        self.assertIsNone(lock._lock)
        self.assertIsNone(lock.get_fencing_token())

    def test_fencing_token_persistence(self):
        """Test that fencing token is available through the lock object."""
        lock_key = {"resource": "lock:res1", "key": "val1"}
        self.mock_redlock_manager.lock.return_value = lock_key
        self.mock_redis_instance.incr.return_value = 100
        
        lock = DistributedLock("res1")
        lock.acquire()
        
        self.assertEqual(lock.get_fencing_token(), 100)

    def test_redis_downtime_during_acquisition(self):
        """Test handling of Redis downtime during acquisition."""
        # During Redis initialization or locking
        self.mock_redlock_manager.lock.side_effect = redis.ConnectionError("Redis is down")
        
        lock = DistributedLock("res1")
        acquired = lock.acquire()
        
        self.assertFalse(acquired)

    def test_redis_downtime_during_fencing(self):
        """Test handling of Redis downtime during fencing token generation."""
        lock_key = {"resource": "lock:res1", "key": "val1"}
        self.mock_redlock_manager.lock.return_value = lock_key
        self.mock_redis_instance.incr.side_effect = redis.ConnectionError("Redis is down")
        
        lock = DistributedLock("res1")
        # According to our design, if fencing fails, then acquisition fails
        acquired = lock.acquire()
        self.assertFalse(acquired)

    def test_distributed_lock_context_manager(self):
        """Test the context manager interface."""
        lock_key = {"resource": "lock:ctx", "key": "val"}
        self.mock_redlock_manager.lock.return_value = lock_key
        self.mock_redis_instance.incr.return_value = 5
        
        with DistributedLock("ctx") as lock:
            self.assertEqual(lock.get_fencing_token(), 5)
            
        self.mock_redlock_manager.unlock.assert_called_once()

    def test_concurrenc_with_threads(self):
        """Test basic thread behavior (not really contention testing but sanity check)."""
        lock_key = {"resource": "lock:thread", "key": "val"}
        self.mock_redlock_manager.lock.return_value = lock_key
        self.mock_redis_instance.incr.return_value = 10
        
        def run_lock():
            with DistributedLock("thread") as lock:
                time.sleep(0.1)
                
        t1 = threading.Thread(target=run_lock)
        t1.start()
        t1.join()
        
        self.mock_redlock_manager.lock.assert_called()
        self.mock_redlock_manager.unlock.assert_called()

if __name__ == '__main__':
    unittest.main()
