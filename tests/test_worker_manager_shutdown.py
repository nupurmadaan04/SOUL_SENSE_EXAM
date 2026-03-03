import asyncio
import sys
import os
import pytest

sys.path.append(os.getcwd())

from backend.fastapi.api.services.worker_manager import AsyncWorkerManager


@pytest.mark.asyncio
async def test_graceful_shutdown_waits_for_quick_worker():
    mgr = AsyncWorkerManager()

    async def quick_worker():
        # finishes quickly
        await asyncio.sleep(0.1)

    mgr.register_worker('quick', quick_worker)
    await mgr.start()
    await mgr.start_worker('quick')

    # Shutdown with drain_timeout should allow quick worker to finish
    await mgr.shutdown(drain_timeout=2)

    status = mgr.get_worker_status()
    assert status['quick']['running'] is False


@pytest.mark.asyncio
async def test_graceful_shutdown_cancels_long_running_worker():
    mgr = AsyncWorkerManager()

    stop_event = asyncio.Event()

    async def long_worker():
        # worker that waits until external event; simulates in-flight work
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            # propagate cancellation
            raise

    mgr.register_worker('long', long_worker)
    await mgr.start()
    await mgr.start_worker('long')

    # Shutdown with short drain timeout: worker should be cancelled
    await mgr.shutdown(drain_timeout=0.2)

    status = mgr.get_worker_status()
    assert status['long']['running'] is False
