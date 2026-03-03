# 🚀 Pull Request: Database Connection Pool Exhaustion Fix

## 📝 Description
This PR addresses potential database connection pool saturation under high load by implementing robust pool management, timeout enforcement, and resilient session handling.

- **Objective**: Prevent stuck DB connections and request blocking by configuring connection pooling and timeouts.
- **Context**: Missing timeout management can cause the pool to saturate, leading to application hangs and resource exhaustion.

---

## 🔧 Type of Change
- [ ] 🐛 **Bug Fix**
- [ ] ✨ **New Feature**
- [ ] 💥 **Breaking Change**
- [ ] ♻️ **Refactor**
- [ ] 📝 **Documentation Update**
- [x] 🚀 **Performance / Security**

---

## 🧪 How Has This Been Tested?
I have implemented automated tests to verify the behavior under simulated edge cases.

- [x] **Unit Tests**: Created `tests/test_db_pool_exhaustion.py` with the following tests:
  - `test_query_timeout_enforcement`: Verifies that SQLite locks/timeouts are respected.
  - `test_rollback_on_failure`: Confirms that `get_db` correctly rolls back transactions on exceptions.
- [ ] **Integration Tests**: N/A
- [x] **Manual Verification**: Verified engine creation parameters and pool status metrics via `get_pool_status()`.

---

## ✅ Checklist
- [x] My code follows the project's style guidelines.
- [x] I have performed a self-review of my code.
- [x] I have added/updated necessary comments or documentation.
- [x] My changes generate no new warnings or linting errors.
- [x] Existing tests pass with my changes.
- [x] I have verified this PR on the latest `main` branch.

---

## 📝 Additional Notes
- Added `pool_pre_ping=True` to handle DB node failures.
- Implemented `StaticPool` for SQLite to ensure thread-safety in local development.
- Added `statement_timeout` for PostgreSQL production environments.
- Introduced `get_pool_status()` for real-time monitoring of connection health.
