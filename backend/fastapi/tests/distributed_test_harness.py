import time
import logging
import multiprocessing
import random
import os
import sys
from typing import List
import redis

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.fastapi.api.utils.distributed_lock import DistributedLock, DistributedLockError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def worker_task(worker_id: int, lock_resource: str, duration: float, iterations: int):
    """
    Simulation of a worker task that needs a distributed lock to perform work.
    """
    success_count = 0
    failure_count = 0
    
    for i in range(iterations):
        logger.info(f"Iteration {i+1}/{iterations}: Attempting to acquire lock on {lock_resource}")
        
        try:
            lock = DistributedLock(lock_resource)
            if lock.acquire(ttl_ms=5000): # 5s TTL
                token = lock.get_fencing_token()
                logger.info(f"Successfully acquired lock on {lock_resource}. Fencing token: {token}")
                
                try:
                    # Simulate work
                    work_time = random.uniform(0.1, 1.0)
                    logger.debug(f"Working for {work_time:.2f}s...")
                    time.sleep(work_time)
                finally:
                    lock.release()
                    logger.info(f"Work completed and lock released.")
                    
                success_count += 1
            else:
                failure_count += 1
                logger.warning(f"Could not acquire lock (contention). Retrying soon...")
                # Backoff before retry
                time.sleep(random.uniform(0.1, 0.5))
        except Exception as e:
            logger.error(f"Error in worker {worker_id}: {e}")
            failure_count += 1
            
    return success_count, failure_count

def run_distributed_test(num_workers: int = 5, iterations: int = 5):
    """
    Runs a distributed test with multiple workers.
    """
    resource = "shared_resource_alpha"
    
    logger.info(f"Starting distributed lock contention test with {num_workers} workers.")
    
    with multiprocessing.Pool(processes=num_workers) as pool:
        results = [pool.apply_async(worker_task, (i, resource, 1.0, iterations)) for i in range(num_workers)]
        
        final_results = [r.get() for r in results]
        
    total_success = sum(r[0] for r in final_results)
    total_failures = sum(r[1] for r in final_results)
    
    logger.info("Test results summary:")
    logger.info(f"Total Successful Acquisitions: {total_success}")
    logger.info(f"Total Failed/Timed-out Acquisitions: {total_failures}")
    logger.info(f"Success Rate: {(total_success / (total_success + total_failures)) * 100:.2f}%")

if __name__ == '__main__':
    # You might need a local Redis running to actually execute this properly
    # This script is meant to be run as an integration test harness
    run_distributed_test()
