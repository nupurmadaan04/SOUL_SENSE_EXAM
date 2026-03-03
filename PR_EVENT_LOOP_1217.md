## PR: Event Loop Blocking Fix (#1217)

Branch: event-loop-1217

**Summary**
- Problem: Synchronous file, DB, or third-party SDK calls inside async endpoints can block the event loop, causing high latency and request freezes.
- Goal: Eliminate blocking operations on async code paths, provide safe fallbacks via `run_in_executor`, and add tests to detect regressions.

**Technical implementation**
- Audit and identify hotspots: search for blocking I/O in `api/` (file reads/writes, sync DB drivers, blocking SDKs, logging handlers).
- File uploads/downloads: replace blocking file access with `aiofiles` and stream uploads to disk in chunks.
- Database: use async DB drivers (e.g., `asyncpg` / SQLAlchemy async) for request paths; where impossible, call blocking DB work with `asyncio.get_running_loop().run_in_executor()` and bound threadpool.
- Third-party SDKs: wrap blocking SDK calls in `run_in_executor` or replace with async alternatives where available.
- Logging: ensure handlers are non-blocking (use queue-based handlers or background writer threads) to avoid blocking request loop.
- Middleware: refactor any middleware performing sync I/O to async equivalents or delegate to executor.

**Edge cases & mitigations**
- Large file uploads (500MB): stream to disk using `aiofiles` and validate backpressure handling.
- Blocking SDKs: add timeouts and circuit-breaker wrappers; execute in bounded executor to avoid unbounded thread growth.
- Long-running CPU tasks: offload to worker processes or background tasks (Celery / RQ) rather than threads.

**Testing plan**
- Unit tests enabling `asyncio` debug mode to surface blocking calls.
- Latency profiling: instrument endpoints with timing and check for event-loop-blocking traces (e.g., `asyncio.get_running_loop().slow_callback_duration`).
- Stress test: upload a 500MB file to the upload endpoint and verify server stays responsive for concurrent requests.

**Quick verification commands**
```bash
# run async-mode unit tests (example)
python -m pytest backend/fastapi/tests/unit -q

# run a simple stress uploader (external host recommended)
python tools/stress/upload_500mb.py --concurrency 50 --url http://localhost:8000/api/v1/upload
```

If you want, I can add the audit script, `aiofiles` conversions for specific handlers, and the 500MB upload harness in this branch next—which would you prefer I do first? 
