# 🚀 Pull Request: Foreign Key Integrity Orphan Scanner (#1414)

## 📝 Description

This PR implements a comprehensive foreign key integrity orphan scanner that detects and remediates orphaned database records - records with foreign keys referencing non-existent parent records. This tool helps maintain database referential integrity, improves data quality, and prevents application errors caused by invalid relationships.

- **Objective**: Deliver measurable improvement in database quality by automatically detecting and remediating orphaned records with clear ownership and safe rollout controls.
- **Context**: Addresses the gap in database practices where foreign key relationships may become inconsistent due to application bugs, manual data modifications, or incomplete transaction handling.

**Closes #1414**

---

## 🔧 Type of Change

Mark the relevant options:

- [ ] 🐛 **Bug Fix**: A non-breaking change which fixes an issue.
- [x] ✨ **New Feature**: A non-breaking change which adds functionality.
- [ ] 💥 **Breaking Change**: A fix or feature that would cause existing functionality to not work as expected.
- [ ] ♻️ **Refactor**: Code improvement (no functional changes).
- [x] 📝 **Documentation Update**: Changes to README, comments, or external docs.
- [x] 🚀 **Performance / Security**: Improvements to app speed and security posture.

---

## 🧪 How Has This Been Tested?

Describe the tests you ran to verify your changes. Include steps to reproduce if necessary.

- [x] **Unit Tests**: Ran comprehensive unit tests covering relationship discovery, scanning strategies, cleanup operations, and statistics tracking.
- [x] **Integration Tests**: Verified database operations and end-to-end orphan scanning workflows.
- [x] **Manual Verification**: Tested API endpoints and background task execution.

### Test Coverage

**Unit Tests** (`tests/unit/test_orphan_scanner.py`):
- ForeignKeyRelationship dataclass validation
- OrphanRecord creation and serialization
- ScanResult properties and error handling
- CleanupResult success/failure states
- DatabaseIntegrityReport integrity score calculation
- OrphanScanner initialization
- Relationship discovery
- Scan operations with different strategies
- Cleanup operations with all strategies
- Statistics and history tracking
- Callback registration

**Integration Tests** (`tests/integration/test_orphan_scanner_integration.py`):
- Scanner initialization with real database
- Relationship discovery from schema
- Table scanning operations
- Full database integrity scans
- Cleanup dry-run mode
- History tracking
- Statistics collection
- Global scanner instance handling

### Test Execution

```bash
# Run unit tests
cd backend/fastapi
python -m pytest tests/unit/test_orphan_scanner.py -v

# Run integration tests
python -m pytest tests/integration/test_orphan_scanner_integration.py -v

# Run all orphan scanner tests
python -m pytest tests/ -k "orphan" -v
```

---

## 📸 Screenshots / Recordings (if applicable)

### API Endpoints

```bash
# Get scanner status
GET /api/v1/admin/orphan-scanner/status

# Response:
{
  "status": "healthy",
  "relationships": [
    {
      "table_name": "responses",
      "column_name": "user_id",
      "referenced_table": "users",
      "referenced_column": "id",
      "constraint_name": "fk_responses_user",
      "on_delete": "CASCADE"
    }
  ],
  "statistics": {
    "total_scans": 150,
    "total_orphans_found": 2300,
    "total_orphans_processed": 2280,
    "scans_last_24h": 3,
    "relationships_discovered": 45
  }
}
```

### Scan Result

```bash
# Scan specific table
POST /api/v1/admin/orphan-scanner/scan
{
  "table_name": "notification_logs",
  "foreign_key_column": "user_id",
  "referenced_table": "users",
  "strategy": "not_exists"
}

# Response:
{
  "table_name": "notification_logs",
  "foreign_key_column": "user_id",
  "referenced_table": "users",
  "orphan_count": 150,
  "sample_orphans": [
    {
      "table_name": "notification_logs",
      "record_id": 12345,
      "foreign_key_column": "user_id",
      "foreign_key_value": "99999",
      "referenced_table": "users"
    }
  ],
  "scan_duration_ms": 1250.5,
  "has_orphans": true,
  "success": true
}
```

### Full Integrity Report

```bash
# Full database scan
POST /api/v1/admin/orphan-scanner/scan-all

# Response:
{
  "scan_time": "2026-03-07T10:00:00",
  "tables_scanned": 25,
  "relationships_checked": 45,
  "total_orphans_found": 2300,
  "integrity_score": 94.2,
  "duration_ms": 15000,
  "table_results": [...]
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

1. **Admin-only Access**: All orphan scanner endpoints require admin privileges via `require_admin` dependency.
2. **Dry-run Mode**: All cleanup operations support dry-run mode for safe testing.
3. **Backup Creation**: Optional backup table creation before destructive operations.
4. **Audit Trail**: Complete history of all scans and cleanup operations.
5. **Input Validation**: Pydantic models enforce type safety and constraints.
6. **SQL Injection Prevention**: All SQL queries use parameterized statements.
7. **Batch Processing**: Large operations are processed in batches to prevent timeouts.

---

## 📝 Additional Notes

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              Foreign Key Integrity Orphan Scanner                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  FK Discovery    │  │   Scan Engine    │                   │
│  │                  │  │                  │                   │
│  │ • Schema intros  │  │ • NOT EXISTS     │                   │
│  │ • Constraint map │  │ • LEFT JOIN      │                   │
│  │ • Relationship   │  │ • EXCEPT query   │                   │
│  │   tracking       │  │ • Batch scanning │                   │
│  └────────┬─────────┘  └────────┬─────────┘                   │
│           │                     │                              │
│           └───────────┬─────────┘                              │
│                       │                                         │
│              ┌────────▼────────┐                               │
│              │  OrphanScanner  │                               │
│              │    Manager      │                               │
│              └────────┬────────┘                               │
│                       │                                         │
│    ┌──────────────────┼──────────────────┐                    │
│    │                  │                  │                    │
│ ┌──▼────┐       ┌────▼────┐       ┌────▼────┐               │
│ │  API  │       │ Cleanup │       │ History │               │
│ │Router │       │ Engine  │       │ & Stats │               │
│ └──┬────┘       └────┬────┘       └────┬────┘               │
│    │                 │                 │                      │
│    │  ┌───────────┐  │  ┌───────────┐  │                     │
│    └──┤  DELETE   ├──┴──┤  SOFT     ├──┘                     │
│       │  NULLIFY  │     │  DELETE   │                        │
│       │  ARCHIVE  │     │  REPORT   │                        │
│       └───────────┘     └───────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Automatic Discovery** | Discovers FK relationships from database schema |
| **Multiple Scan Strategies** | NOT EXISTS, LEFT JOIN, EXCEPT query support |
| **Cleanup Strategies** | DELETE, SOFT_DELETE, NULLIFY, ARCHIVE_THEN_DELETE |
| **Dry-run Mode** | Safe testing without data modification |
| **Backup Creation** | Automatic backup before destructive operations |
| **Integrity Score** | Database health metric (0-100%) |
| **Comprehensive Logging** | Complete audit trail of all operations |
| **Batch Processing** | Configurable batch sizes for large datasets |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/orphan-scanner/status` | System status and relationships |
| POST | `/api/v1/admin/orphan-scanner/discover` | Discover FK relationships |
| POST | `/api/v1/admin/orphan-scanner/scan` | Scan specific table |
| POST | `/api/v1/admin/orphan-scanner/scan-all` | Full database scan |
| POST | `/api/v1/admin/orphan-scanner/cleanup` | Clean up orphans |
| GET | `/api/v1/admin/orphan-scanner/scan-history` | Scan history |
| GET | `/api/v1/admin/orphan-scanner/cleanup-history` | Cleanup history |
| GET | `/api/v1/admin/orphan-scanner/statistics` | Overall statistics |

### Configuration Example

```python
from api.utils.orphan_scanner import (
    OrphanScanner,
    CleanupStrategy,
    ScanStrategy,
    get_orphan_scanner,
)

# Get scanner instance
scanner = await get_orphan_scanner(engine)

# Scan for orphans
result = await scanner.scan_table(
    table_name="responses",
    foreign_key_column="user_id",
    referenced_table="users",
    strategy=ScanStrategy.NOT_EXISTS,
)

if result.has_orphans:
    # Clean up with dry-run first
    cleanup = await scanner.cleanup_orphans(
        table_name="responses",
        foreign_key_column="user_id",
        referenced_table="users",
        strategy=CleanupStrategy.SOFT_DELETE,
        dry_run=True,  # Test first
    )
    
    if cleanup.success:
        # Run actual cleanup
        await scanner.cleanup_orphans(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            strategy=CleanupStrategy.SOFT_DELETE,
            dry_run=False,
        )
```

### Celery Beat Schedule

```python
CELERY_BEAT_SCHEDULE = {
    'orphan-scan-weekly': {
        'task': 'api.celery_tasks_orphan_scanner.run_full_orphan_scan_task',
        'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),
    },
    'orphan-auto-cleanup-daily': {
        'task': 'api.celery_tasks_orphan_scanner.auto_cleanup_known_orphans_task',
        'schedule': crontab(hour=4, minute=0),
    },
}
```

### Scan Strategies

| Strategy | SQL Approach | Best For |
|----------|--------------|----------|
| `NOT_EXISTS` | `WHERE NOT EXISTS (SELECT 1 FROM parent)` | General purpose, most compatible |
| `LEFT_JOIN` | `LEFT JOIN parent WHERE parent.id IS NULL` | Large datasets with indexes |
| `EXCEPT` | `SELECT fk EXCEPT SELECT pk` | PostgreSQL, set operations |

### Cleanup Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `DELETE` | Hard delete orphans | Non-critical data, backups exist |
| `SOFT_DELETE` | Mark as deleted | Need recovery capability |
| `NULLIFY` | Set FK to NULL | Optional relationships |
| `ARCHIVE_THEN_DELETE` | Archive before delete | Audit requirements |
| `REPORT_ONLY` | No action taken | Investigation mode |

### Edge Cases Handled

1. **Circular References**: Detected and reported during discovery
2. **Self-Referencing Tables**: Properly handled with recursive detection
3. **Composite Keys**: Full support for multi-column foreign keys
4. **Nullable FKs**: NULL values excluded from orphan detection
5. **Large Datasets**: Batch processing prevents memory issues
6. **Concurrent Modifications**: Transaction-safe operations
7. **Missing Parent Tables**: Graceful handling of schema changes
8. **Database Errors**: Proper rollback and error reporting

### Rollback Plan

- All cleanup operations support dry-run mode
- Backup tables created before destructive operations
- SOFT_DELETE strategy allows data recovery
- Complete history of all operations
- Optional NULLIFY for reversible changes

### Performance Impact

- **Minimal Overhead**: Scans run during off-peak hours
- **Batch Processing**: Configurable batch sizes (default 1000)
- **Indexed Queries**: Efficient SQL using foreign key indexes
- **Async Operations**: Non-blocking scan execution
- **Parallel Scanning**: Multiple tables can be scanned concurrently

---

## Files Changed

```
backend/fastapi/api/utils/orphan_scanner.py                    (NEW)
backend/fastapi/api/routers/orphan_scanner.py                  (NEW)
backend/fastapi/api/celery_tasks_orphan_scanner.py             (NEW)
backend/fastapi/tests/unit/test_orphan_scanner.py              (NEW)
backend/fastapi/tests/integration/test_orphan_scanner_integration.py (NEW)
backend/fastapi/api/main.py                                     (MODIFIED)
```

**Total**: 6 files, ~3,800 lines added

---

## Deployment Notes

1. **Database Migrations**: Automatic table creation on first startup
2. **Configuration**: No required configuration changes
3. **Monitoring**: New metrics available at `/api/v1/admin/orphan-scanner/statistics`
4. **Scheduling**: Configure Celery beat for automated scanning
5. **First Run**: Run full scan to establish baseline integrity score

---

*Branch: `fix/foreign-key-orphan-scanner-1414`*
*Tests: 50+ test cases, all passing*
*Documentation: Complete API docs and examples*
