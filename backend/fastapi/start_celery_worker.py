"""
Celery Worker Startup Script with CPU Affinity Binding.

Starts Celery worker processes with automatic CPU core binding
to reduce context thrashing and improve scheduling efficiency.

Usage:
    python start_celery_worker.py --concurrency=4 --loglevel=info
"""

import sys
import os
import logging
from pathlib import Path

# Add paths
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from api.celery_app import celery_app
from api.config import get_settings_instance
from api.utils.cpu_affinity import (
    get_available_cores,
    get_optimal_worker_count,
    bind_process_to_cores,
    distribute_workers_across_cores,
    validate_affinity_support,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)


def bind_worker_to_cores(worker_id: int, num_workers: int, num_cores: int) -> bool:
    """
    Bind current worker process to its assigned CPU cores.
    
    Args:
        worker_id: ID of this worker (0-indexed)
        num_workers: Total number of workers
        num_cores: Total number of CPU cores available
        
    Returns:
        True if binding successful, False otherwise
    """
    # Distribute workers across cores
    distribution = distribute_workers_across_cores(num_workers, num_cores)
    
    if 0 <= worker_id < len(distribution):
        cores = distribution[worker_id]
        logger.info(f"Worker {worker_id}/{num_workers} binding to cores: {cores}")
        return bind_process_to_cores(cores)
    
    logger.warning(f"Invalid worker_id {worker_id} for {num_workers} workers")
    return False


def start_celery_worker(concurrency=None, loglevel='info'):
    """
    Start Celery worker with CPU affinity binding.
    
    Args:
        concurrency: Number of worker processes (auto-calculated if None)
        loglevel: Logging level (debug, info, warning, error, critical)
    """
    if concurrency is None:
        concurrency = get_optimal_worker_count()
    
    num_cores = get_available_cores()
    
    logger.info("=" * 70)
    logger.info("CELERY WORKER STARTUP - CPU AFFINITY BINDING (Issue #1192)")
    logger.info("=" * 70)
    logger.info(f"Available CPU cores: {num_cores}")
    logger.info(f"Optimal worker count: {get_optimal_worker_count()}")
    logger.info(f"Starting {concurrency} worker processes")
    logger.info(f"Affinity support: {validate_affinity_support()}")
    
    # Bind current process (main worker dispatcher) to cores
    if validate_affinity_support():
        # Main process gets first core(s) for coordination
        distribution = distribute_workers_across_cores(concurrency, num_cores)
        if distribution:
            main_cores = distribution[0]
            logger.info(f"Main worker process binding to cores: {main_cores}")
            bind_process_to_cores(main_cores)
    else:
        logger.warning("CPU affinity not supported on this platform")
    
    logger.info("=" * 70)

    settings = get_settings_instance()
    max_memory_per_child_kb = settings.celery_worker_max_memory_mb * 1024
    logger.info(f"Configured max memory per worker child: {settings.celery_worker_max_memory_mb} MB ({max_memory_per_child_kb} KB)")
    
    # Build worker command arguments
    worker_argv = [
        'worker',
        '--loglevel', loglevel,
        '--concurrency', str(concurrency),
        '--max-tasks-per-child', '50',
        '--max-memory-per-child', str(max_memory_per_child_kb),
        '--time-limit', '3600',
        '--soft-time-limit', '3300',
    ]
    
    logger.info(f"Starting Celery worker with args: {worker_argv}")
    logger.info("=" * 70)
    
    # Start Celery worker
    celery_app.worker_main(worker_argv)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Start Soul Sense Celery worker with CPU affinity binding"
    )
    parser.add_argument(
        '--concurrency', '-c',
        type=int,
        default=None,
        help='Number of worker processes (auto-detected if not specified)'
    )
    parser.add_argument(
        '--loglevel', '-l',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    try:
        start_celery_worker(
            concurrency=args.concurrency,
            loglevel=args.loglevel
        )
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker startup failed: {e}", exc_info=True)
        sys.exit(1)
