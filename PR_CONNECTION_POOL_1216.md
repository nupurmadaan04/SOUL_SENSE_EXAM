## PR: Connection Pool Exhaustion Mitigation (#1216)

Branch: con-pool

**Summary**
- Problem: Under burst traffic the database connection pool can saturate, causing request timeouts and degraded availability.
- Goal: Ensure stable connection reuse, detect leaks, and prevent pool starvation under high concurrency.

**Technical implementation (changes in this branch)**
- Configured conditional pool parameters for non-SQLite databases: `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle` (applied only when driver supports it).
- Added `SessionCleanupMiddleware` to guarantee request-scoped `AsyncSession` instances are closed if leaked by code paths.
- Enabled SQLAlchemy pool event logging hooks on primary and replica engines to monitor `connect`, `checkout`, and `checkin` events.

**Immediate testing recommendations**
- Run focused unit tests:

```bash
python -m pytest backend/fastapi/tests/unit/test_async_session_management.py -q
```

- For a stress test (recommended to run from a separate machine): use `locust` or a simple `asyncio` script to simulate 2000 concurrent connections targeting representative endpoints.

**Stress Test Harness**

A simple asyncio-based stress test script has been added at `tools/stress_test_pool.py`. It simulates concurrent connections to test pool stability.

**Usage:**
```bash
# Install dependencies
pip install aiohttp

# Run stress test (adjust URL and parameters as needed)
python tools/stress_test_pool.py --url http://localhost:8000 --concurrency 2000 --duration 60
```

**Runbook: Monitoring Connection Pool Health**

**1. Enable Debug Logging**
Before running tests, enable pool event logging by setting the environment variable:
```bash
export SQLALCHEMY_ECHO_POOL=true
# Or in config
pool_logging: true
```

**2. Monitor Application Logs**
Watch for pool events in logs:
```bash
# Tail application logs
tail -f logs/app.log | grep -E "(pool|connect|checkout|checkin)"

# Expected output during normal operation:
# [POOL] connect: created new connection
# [POOL] checkout: checked out connection from pool
# [POOL] checkin: returned connection to pool
```

**3. Database Connection Monitoring**
For PostgreSQL:
```sql
-- Check active connections
SELECT count(*) as active_connections FROM pg_stat_activity WHERE datname = 'your_db_name';

-- Check connection age (should recycle old connections)
SELECT pid, usename, client_addr, backend_start, state_change
FROM pg_stat_activity
WHERE datname = 'your_db_name'
ORDER BY backend_start;
```

For MySQL:
```sql
-- Show process list
SHOW PROCESSLIST;

-- Check connection count
SELECT COUNT(*) as connections FROM information_schema.processlist;
```

**4. Application Metrics**
Monitor these key metrics during stress tests:
- Response time percentiles (p50, p95, p99)
- Error rate (4xx/5xx responses)
- Database connection pool size vs active connections
- Session leak count (via middleware logs)

**5. Troubleshooting Pool Exhaustion**
If stress test shows high failure rates or slow responses:
- Check pool size: Ensure `pool_size + max_overflow` > expected concurrent requests
- Verify session cleanup: Look for "Session leaked" warnings in logs
- Monitor timeouts: Increase `pool_timeout` if checkouts are timing out
- Check for connection leaks: Use `pg_stat_activity` to find idle connections

**6. Post-Test Verification**
After stress test:
```bash
# Check for leaked sessions
grep "Session leaked" logs/app.log

# Verify pool recovery
python -c "
import asyncio
from backend.fastapi.api.services.db_service import get_db
async def test():
    async for session in get_db():
        result = await session.execute('SELECT 1')
        print('Pool healthy:', result.scalar())
        break
asyncio.run(test())
"
```

This runbook provides comprehensive monitoring to validate pool stability under load.