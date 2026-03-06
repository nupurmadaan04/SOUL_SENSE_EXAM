
import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import socket
import uuid

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.ml.scheduler_service import AnalyticsScheduler
from backend.fastapi.api.utils.distributed_lock import DistributedLock

class TestLeaderElectionFailover(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for scheduler leader election and failover.
    Ensures that only one leader exists and failover works when leader stops.
    """

    async def asyncSetUp(self):
        # Mock Redis to avoid actual connection
        self.redis_patcher = patch('redis.asyncio.from_url')
        self.mock_redis_factory = self.redis_patcher.start()
        self.mock_redis = AsyncMock()
        self.mock_redis_factory.return_value = self.mock_redis
        
        # Default redis.set to succeed (acquire lock)
        self.mock_redis.set.return_value = True
        # Default eval to succeed (release/extend lock)
        self.mock_redis.eval.return_value = 1

    async def asyncTearDown(self):
        self.redis_patcher.stop()

    async def test_single_leader_election(self):
        """Test that only one instance becomes leader when multiple start."""
        # Instance 1 should win
        inst1 = AnalyticsScheduler()
        # Instance 2 should fail to get lock initially
        inst2 = AnalyticsScheduler()
        
        # Mock redis.set for inst2 to return False (fail to acquire)
        # Using side_effect to behave differently for different calls if needed
        # but for simplicity we'll just test sequentially or with controlled mocks
        
        with patch('app.ml.scheduler_service.DistributedLock') as MockLock:
            # First lock acquisition succeeds, second fails
            lock1 = AsyncMock(spec=DistributedLock)
            lock1.__aenter__.return_value = lock1
            lock1.extend.return_value = True
            
            lock2 = AsyncMock(spec=DistributedLock)
            lock2.__aenter__.side_effect = RuntimeError("Lock busy")
            
            MockLock.side_effect = [lock1, lock2]
            
            # Start both
            inst1.start()
            inst2.start()
            
            # Yield to event loop to allow leader election tasks to run
            await asyncio.sleep(0.1)
            
            self.assertTrue(inst1.is_leader(), "Instance 1 should be leader")
            self.assertFalse(inst2.is_leader(), "Instance 2 should NOT be leader")
            
            # Cleanup
            inst1.stop()
            inst2.stop()

    async def test_failover_mechanism(self):
        """Test that leadership fails over when the leader instance stops."""
        inst1 = AnalyticsScheduler()
        inst2 = AnalyticsScheduler()
        
        with patch('app.ml.scheduler_service.DistributedLock') as MockLock:
            lock1 = AsyncMock(spec=DistributedLock)
            lock1.__aenter__.return_value = lock1
            lock1.extend.return_value = True
            
            lock2 = AsyncMock(spec=DistributedLock)
            # lock2 fails first try, then succeeds after inst1 stops
            lock2.__aenter__.side_effect = [RuntimeError("Lock busy"), lock2]
            lock2.extend.return_value = True
            
            MockLock.side_effect = [lock1, lock2, lock2] # 1st for inst1, 2nd & 3rd for inst2
            
            inst1.start()
            await asyncio.sleep(0.05)
            self.assertTrue(inst1.is_leader())
            
            inst2.start()
            await asyncio.sleep(0.05)
            self.assertFalse(inst2.is_leader(), "inst2 should not be leader while inst1 is active")
            
            # Simulate leader stopping
            inst1.stop()
            logger.info("Leader (inst1) stopped, waiting for failover...")
            
            # inst2 loop should retry according to sleep in _leader_election_loop
            # We might need to shorten the sleep in the code or mock asyncio.sleep
            
            # Wait for inst2 to retry and win
            # In our implementation it waits 15s after failure, let's wait a bit
            # For testing purposes we might want to monkeypatch the sleep interval
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                # Let's manually trigger a few iterations of the loop if sleep is mocked
                await asyncio.sleep(0.5) 
                
            # After inst1 stops and releases lock (or mocked to allow next), inst2 should win
            self.assertTrue(inst2.is_leader(), "Failover failed: inst2 never became leader")
            
            inst2.stop()

if __name__ == '__main__':
    unittest.main()
