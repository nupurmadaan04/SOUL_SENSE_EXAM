## PR: Unreleased Locks in Async Transaction Scope (#1218)

Branch: fix-1218

**Summary**
- Problem: Transaction locks persist on exception, causing deadlocks in concurrent async operations.
- Goal: Guarantee deterministic rollback and lock release in async transaction scopes.

**Technical implementation**
- Added `transaction_scope()` async context manager for guaranteed transaction boundaries with automatic rollback on exceptions.
- Implemented `deadlock_retry()` decorator with exponential backoff for operations that fail due to database deadlocks.
- Updated UserService methods (`create_user`, `update_user`, `update_user_role`, `delete_user`, `reactivate_user`, `purge_deleted_users`) to use context-managed transactions instead of manual commit/rollback.
- Ensured nested savepoints are properly handled through SQLAlchemy's transaction context management.

**Edge cases & mitigations**
- Nested savepoints: SQLAlchemy's `begin()` context manager handles nested transactions correctly.
- Timeout during commit: Transaction scope ensures rollback occurs even if commit fails.
- Partial failures: All operations within a transaction scope are atomic - either all succeed or all rollback.
- Concurrent access: Deadlock retry decorator automatically retries failed operations with exponential backoff.

**Testing plan**
- Unit tests for transaction scope context manager and deadlock retry decorator.
- Force mid-transaction crash simulation using mock exceptions.
- Concurrent row update simulation to test deadlock scenarios.
- Integration tests with actual database to verify lock release.

**Test Cases**
```bash
# Run transaction scope tests
python -m pytest backend/fastapi/tests/unit/test_transaction_scope_1218.py -v

# Force mid-transaction failure simulation
python -m pytest backend/fastapi/tests/unit/test_transaction_scope_1218.py::TestTransactionScope::test_transaction_scope_rollback_on_exception -v

# Concurrent update simulation
python -m pytest backend/fastapi/tests/unit/test_transaction_scope_1218.py::TestConcurrentTransactionSimulation::test_simulated_concurrent_updates -v
```

**Monitoring & Verification**
- Database lock monitoring: Check `pg_locks` (PostgreSQL) or `information_schema.innodb_locks` (MySQL) during stress tests.
- Deadlock logging: Monitor application logs for deadlock retry attempts and success rates.
- Transaction success rate: Track commit vs rollback ratios in application metrics.

**Quick verification commands**
```bash
# Check for deadlock retry logs
tail -f logs/app.log | grep -i deadlock

# Monitor database locks (PostgreSQL)
watch -n 1 "psql -c 'SELECT * FROM pg_locks WHERE NOT granted;'"

# Run concurrent stress test
python -c "
import asyncio
from backend.fastapi.api.services.user_service import UserService
# Simulate concurrent operations that could deadlock
"
```

This implementation ensures that database locks are always released, preventing deadlock accumulation in high-concurrency async environments.