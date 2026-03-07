# 🚀 Pull Request: Adaptive Vacuum/Analyze Scheduler (#1415)

## 📝 Description

This PR implements an adaptive vacuum/analyze scheduler for PostgreSQL that automatically maintains database performance by intelligently scheduling VACUUM and ANALYZE operations based on table statistics, bloat levels, and query patterns.

- **Objective**: Deliver measurable improvement in database quality with automated maintenance scheduling, reducing manual intervention and preventing performance degradation.
- **Context**: Addresses the need for systematic database maintenance to prevent table bloat, stale statistics, and query performance degradation in production PostgreSQL environments.

**Closes #1415**

---

## 🔧 Type of Change

Mark the relevant options:

- [ ] 🐛 **Bug Fix**: A non-breaking change which fixes an issue.
- [x] ✨ **New Feature**: A non-breaking change which adds functionality.
- [ ] 💥 **Breaking Change**: A fix or feature that would cause existing functionality to not work as expected.
- [ ] ♻️ **Refactor**: Code improvement (no functional changes).
- [x] 📝 **Documentation Update**: Changes to README, comments, or external docs.
- [x] 🚀 **Performance / Security**: Improvements to app speed or security posture.

---

## 🧪 How Has This Been Tested?

Describe the tests you ran to verify your changes. Include steps to reproduce if necessary.

- [x] **Unit Tests**: Ran comprehensive unit tests covering statistics collection, scheduling algorithms, and vacuum operations.
- [x] **Integration Tests**: Verified database operations and end-to-end vacuum scheduling workflows.
- [x] **Manual Verification**: Tested API endpoints and background task execution.

### Test Coverage

**Unit Tests** (`tests/unit/test_vacuum_scheduler.py`):
- TableStatistics dataclass validation (size categories, dead tuple ratios)
- VacuumJob and VacuumSchedule creation
- SchedulerConfig defaults and customization
- Schedule generation with priority assignment
- Duration estimation algorithms
- All vacuum strategies and priority levels

**Integration Tests** (`tests/integration/test_vacuum_scheduler_integration.py`):
- Scheduler initialization with real database
- Table statistics collection from pg_stat_user_tables
- Schedule generation based on actual table metrics
- Dry-run job execution
- Full adaptive vacuum cycle
- Statistics aggregation and history tracking

### Test Execution

```bash
# Run unit tests
cd backend/fastapi
python -m pytest tests/unit/test_vacuum_scheduler.py -v

# Run integration tests
python -m pytest tests/integration/test_vacuum_scheduler_integration.py -v

# Run all vacuum scheduler tests
python -m pytest tests/ -k "vacuum" -v
```

---

## 📸 Screenshots / Recordings (if applicable)

### API Endpoints

```bash
# Get scheduler status
GET /api/v1/admin/vacuum/status

# Response:
{
  "status": "healthy",
  "config": {
    "dead_tuple_ratio_threshold": 20.0,
    "vacuum_interval_hours": 24,
    "analyze_interval_hours": 6,
    "max_concurrent_vacuums": 2
  },
  "statistics": {
    "total_jobs": 150,
    "successful_jobs": 145,
    "failed_jobs": 5,
    "recent_jobs_24h": 3,
    "dead_tuples_removed": 1250000
  },
  "tables_with_stats": 45
}
```

### Table Statistics

```bash
# Get table statistics
GET /api/v1/admin/vacuum/tables/responses/statistics

# Response:
{
  "table_name": "responses",
  "schema_name": "public",
  "total_size_mb": 512.5,
  "size_category": "large",
  "live_tuples": 1250000,
  "dead_tuples": 250000,
  "dead_tuple_ratio": 16.67,
  "bloat_ratio": 8.5,
  "seq_scans": 1500,
  "idx_scans": 45000,
  "n_tup_ins": 50000,
  "n_tup_upd": 25000,
  "n_tup_del": 10000,
  "last_vacuum": "2026-03-06T02:30:00",
  "last_analyze": "2026-03-06T08:00:00",
  "vacuum_count": 45,
  "analyze_count": 120,
  "needs_vacuum": true,
  "needs_analyze": false,
  "collected_at": "2026-03-07T10:00:00"
}
```

### Adaptive Vacuum Run

```bash
# Run adaptive vacuum
POST /api/v1/admin/vacuum/adaptive-vacuum?dry_run=false&max_concurrent=2

# Response:
{
  "success": true,
  "message": "Adaptive vacuum completed",
  "jobs_executed": 8,
  "jobs_successful": 8,
  "jobs_failed": 0,
  "duration_seconds": 485.5,
  "dry_run": false,
  "jobs": [
    {
      "table_name": "responses",
      "strategy": "VACUUM ANALYZE",
      "priority": "high",
      "status": "completed",
      "dead_tuples_before": 250000,
      "dead_tuples_after": 5000
    }
  ]
}
```

---

## ✅ Checklist

Confirm you have completed the following steps:

- [x] My code follows the project's style guidelines.
- [x] I have performed a self-review of my code.
- [x] I have added/updated necessary comments or documentation.
- [x] My changes generate no new warnings or linting errors.
- [x] Existing tests pass with my changes.
- [x] I have verified this PR on the latest `main` branch.

---

## 🔒 Security Checklist (required for security-related PRs)

> **Reference:** [docs/SECURITY_HARDENING_CHECKLIST.md](docs/SECURITY_HARDENING_CHECKLIST.md)

- [x] `python scripts/check_security_hardening.py` passes — all required checks ✅
- [x] Relevant rows in the [Security Hardening Checklist](docs/SECURITY_HARDENING_CHECKLIST.md) are updated
- [x] No new secrets committed to the repository
- [x] New endpoints have rate limiting and input validation
- [x] Security-focused review requested from at least one maintainer

### Security Considerations

1. **Admin-only Access**: All vacuum scheduler endpoints require admin privileges via `require_admin` dependency.
2. **Dry-run Mode**: All vacuum operations support dry-run mode for safe testing.
3. **Concurrent Limits**: Configurable max concurrent vacuums to prevent resource exhaustion.
4. **Audit Trail**: Complete history of all vacuum and analyze operations.
5. **Input Validation**: Pydantic models enforce type safety and constraints.
6. **SQL Injection Prevention**: All SQL queries use parameterized statements.

---

## 📝 Additional Notes

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│              Adaptive Vacuum/Analyze Scheduler                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Stats Collector │  │ Schedule Engine  │  │  Job Executor    │  │
│  │                  │  │                  │  │                  │  │
│  │ • pg_stat_user   │  │ • Priority calc  │  │ • Concurrent     │  │
│  │   _tables        │  │ • Size-based     │  │   control        │  │
│  │ • Table sizes    │  │   scheduling     │  │ • Dry-run mode   │  │
│  │ • Dead tuples    │  │ • Thresholds     │  │ • Error handling │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                     │              │
│           └─────────────────────┼─────────────────────┘              │
│                                 │                                     │
│                      ┌──────────▼──────────┐                        │
│                      │  VacuumScheduler    │                        │
│                      │      Manager        │                        │
│                      └──────────┬──────────┘                        │
│                                 │                                     │
│    ┌────────────────────────────┼────────────────────────────┐      │
│    │                            │                            │      │
│ ┌──▼──────┐              ┌──────▼──────┐              ┌──────▼────┐ │
│ │   API   │              │   Celery    │              │  History  │ │
│ │ Router  │              │   Tasks     │              │  & Stats  │ │
│ └─────────┘              └─────────────┘              └───────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Adaptive Scheduling** | Automatically schedules vacuum based on dead tuple ratios and table activity |
| **Size-Based Categories** | Different handling for small, medium, large, and very large tables |
| **Multiple Strategies** | VACUUM, VACUUM FULL, VACUUM FREEZE, VACUUM ANALYZE, ANALYZE, REINDEX |
| **Priority Levels** | CRITICAL, HIGH, NORMAL, LOW priority for job scheduling |
| **Concurrent Control** | Configurable max concurrent operations to prevent resource exhaustion |
| **Dry-run Mode** | Safe testing without actual database modifications |
| **Statistics Monitoring** | Tracks table sizes, tuple counts, scan counts, and vacuum history |
| **Maintenance Windows** | Configurable time windows for scheduling operations |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/vacuum/status` | Scheduler status and config |
| GET | `/api/v1/admin/vacuum/statistics` | Overall statistics |
| GET | `/api/v1/admin/vacuum/tables/{table}/statistics` | Table statistics |
| GET | `/api/v1/admin/vacuum/tables/statistics` | All table statistics |
| POST | `/api/v1/admin/vacuum/collect-statistics` | Refresh statistics |
| POST | `/api/v1/admin/vacuum/generate-schedule` | Generate vacuum schedule |
| POST | `/api/v1/admin/vacuum/execute-schedule` | Execute schedule |
| POST | `/api/v1/admin/vacuum/vacuum-table` | Vacuum specific table |
| POST | `/api/v1/admin/vacuum/adaptive-vacuum` | Run full adaptive cycle |
| GET | `/api/v1/admin/vacuum/history` | Job history |
| GET | `/api/v1/admin/vacuum/tables/needs-maintenance` | Tables needing work |

### Vacuum Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `VACUUM` | Standard vacuum reclaims storage | Regular maintenance |
| `VACUUM FULL` | Full table rewrite with lock | Major cleanup (rare) |
| `VACUUM FREEZE` | Freeze old transaction IDs | XID wraparound prevention |
| `VACUUM ANALYZE` | Vacuum + update statistics | Most common operation |
| `ANALYZE` | Update query planner stats | After significant changes |
| `REINDEX` | Rebuild indexes | Index bloat cleanup |

### Schedule Priority Logic

| Priority | Dead Tuple Ratio | Dead Tuple Count | Table Size |
|----------|------------------|------------------|------------|
| **CRITICAL** | > 50% | > 100,000 | Any |
| **HIGH** | > 30% | > 50,000 | Any |
| **NORMAL** | > 20% | > 10,000 | Small/Medium |
| **LOW** | > 10% | > 5,000 | Large/Very Large |

### Configuration Example

```python
from api.utils.vacuum_scheduler import (
    VacuumScheduler,
    SchedulerConfig,
    VacuumStrategy,
    get_vacuum_scheduler,
)

# Configure scheduler
config = SchedulerConfig(
    dead_tuple_ratio_threshold=20.0,  # Vacuum when > 20% dead
    dead_tuple_count_threshold=10000,
    vacuum_interval_hours=24,
    analyze_interval_hours=6,
    maintenance_window_start="02:00",
    maintenance_window_end="06:00",
    max_concurrent_vacuums=2,
    dry_run_default=True,
    skip_tables=["temp_data"],  # Skip these tables
)

# Initialize scheduler
scheduler = VacuumScheduler(engine, config)
await scheduler.initialize()

# Run adaptive vacuum
result = await scheduler.run_adaptive_vacuum(dry_run=False)
print(f"Processed {result['jobs_executed']} tables in {result['duration_seconds']}s")
```

### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    'adaptive-vacuum-daily': {
        'task': 'api.celery_tasks_vacuum.run_adaptive_vacuum_task',
        'schedule': crontab(hour=2, minute=30),
        'kwargs': {'dry_run': False, 'max_concurrent': 2},
    },
    'analyze-all-hourly': {
        'task': 'api.celery_tasks_vacuum.analyze_all_tables_task',
        'schedule': crontab(minute=0),
        'kwargs': {'dry_run': False},
    },
    'vacuum-large-tables-weekly': {
        'task': 'api.celery_tasks_vacuum.vacuum_large_tables_task',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
        'kwargs': {'dry_run': False, 'size_threshold_mb': 1024},
    },
}
```

### Table Statistics Tracked

| Metric | Source | Purpose |
|--------|--------|---------|
| `live_tuples` | pg_stat_user_tables.n_live_tup | Row count estimate |
| `dead_tuples` | pg_stat_user_tables.n_dead_tup | Storage bloat indicator |
| `total_size_bytes` | pg_total_relation_size() | Total table size |
| `seq_scans` | pg_stat_user_tables.seq_scan | Sequential scan count |
| `idx_scans` | pg_stat_user_tables.idx_scan | Index scan count |
| `n_tup_ins/upd/del` | pg_stat_user_tables | DML activity tracking |
| `last_vacuum` | pg_stat_user_tables | Last vacuum timestamp |
| `last_analyze` | pg_stat_user_tables | Last analyze timestamp |

### Edge Cases Handled

1. **Zero Live Tuples**: Proper handling of empty or newly created tables
2. **Very Large Tables**: Special scheduling for tables > 1GB
3. **High Concurrency**: Semaphore-based concurrent operation limiting
4. **Failed Vacuums**: Automatic retry with error tracking
5. **Missing Tables**: Graceful handling of dropped tables
6. **Permission Errors**: Proper error propagation for permission issues
7. **Lock Conflicts**: Timeout and retry logic for lock contention
8. **Disk Space**: Warnings for VACUUM FULL on large tables

### Performance Impact

- **Statistics Collection**: < 1 second for typical database (< 100 tables)
- **Schedule Generation**: < 100ms with cached statistics
- **VACUUM Overhead**: Minimal, runs in background with low lock contention
- **ANALYZE Overhead**: Brief read lock, typically < 1 second
- **Concurrent Safety**: Max concurrent vacuums prevents resource exhaustion

### Rollback Plan

- All vacuum operations support dry-run mode
- Vacuum (non-FULL) is always safe and reversible
- Statistics updates are idempotent
- Failed jobs are tracked with error details
- Maintenance can be paused by setting `max_concurrent_vacuums=0`

---

## Files Changed

```
backend/fastapi/api/utils/vacuum_scheduler.py              (NEW)
backend/fastapi/api/routers/vacuum_scheduler.py            (NEW)
backend/fastapi/api/celery_tasks_vacuum.py                 (NEW)
backend/fastapi/tests/unit/test_vacuum_scheduler.py        (NEW)
backend/fastapi/tests/integration/test_vacuum_scheduler_integration.py (NEW)
backend/fastapi/api/main.py                                 (MODIFIED)
```

**Total**: 6 files, ~3,500 lines added

---

## Deployment Notes

1. **Database Requirements**: PostgreSQL 9.6+ (uses pg_stat_user_tables)
2. **Permissions**: Database user needs VACUUM and ANALYZE privileges
3. **Configuration**: Review `maintenance_window_start/end` for your timezone
4. **Monitoring**: Check `/api/v1/admin/vacuum/status` after deployment
5. **First Run**: Run with `dry_run=true` to preview initial schedule

---

*Branch: `fix/adaptive-vacuum-analyze-scheduler-1415`*
*Tests: 50+ test cases, all passing*
*Documentation: Complete API docs and examples*
