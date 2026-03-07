# Cross-Region Migration Sequencing Controller

**Issue**: #1387  
**Status**: Implementation Complete  
**Date**: March 7, 2026

## Overview

The Cross-Region Migration Sequencing Controller orchestrates safe database migrations across multiple geographic regions. It ensures migrations execute in correct dependency order, validates region health, tracks execution state, and enables graceful rollback on failures.

### Key Features

✅ **Dependency Resolution**: Topological sort of regions based on replica relationships  
✅ **Health Validation**: Pre-migration checks for region connectivity and readiness  
✅ **Sequential Execution**: Prevents concurrent migrations, stops cascade on failure  
✅ **State Tracking**: Persistent JSON registry for audit trail and resumption  
✅ **Observable**: Structured logging with progress updates per region  
✅ **Safe Rollback**: Tracks failed regions for rollback capability  
✅ **Graceful Degradation**: Works independently, integrates with existing migration infrastructure

---

## Architecture

### Component Overview

```
CrossRegionMigrationSequencer (Orchestrator)
    ├─ Validates region health
    ├─ Resolves execution order
    ├─ Executes migrations sequentially
    └─ Tracks completion/failure per region

CrossRegionMigrationRegistry (Audit Trail)
    ├─ Persists to migrations/cross_region_registry.json
    ├─ Tracks execution history
    ├─ Records regional step status
    └─ Enables resumption after failures

CLI Tools (Operator Interface)
    ├─ plan: Generate execution plan
    ├─ execute: Run migrations with safety checks
    ├─ status: Monitor progress
    ├─ history: View past executions
    └─ rollback: Reverse failed migrations
```

### Data Model

**CrossRegionMigrationPlan**
```python
{
  "migration_version": "20260307_001",
  "regions": ["us-east-1", "us-west-2", "eu-west-1"],
  "execution_order": ["us-east-1", "us-west-2", "eu-west-1"],
  "dependencies": {
    "us-east-1": [],
    "us-west-2": ["us-east-1"],
    "eu-west-1": []
  },
  "status": "completed",
  "created_at": "2026-03-07T10:00:00",
  "started_at": "2026-03-07T10:00:05",
  "completed_at": "2026-03-07T10:02:30",
  "initiated_by": "operations_team"
}
```

**RegionalMigrationStep** (per region)
```python
{
  "region_name": "us-east-1",
  "migration_version": "20260307_001",
  "status": "completed",
  "sequence_order": 1,
  "start_time": "2026-03-07T10:00:05",
  "end_time": "2026-03-07T10:00:45",
  "duration_seconds": 40.2,
  "error_message": null,
  "checksum": "abc123...",
  "backfill_job_id": "job_001"
}
```

---

## Quick Start

### 1. Configure Regions

Edit `config/cross_region_migrations.yaml`:

```yaml
regions:
  - name: us-east-1
    database_url: ${DATABASE_URL_USEAST}
    environment: production
    priority: 1
    replica_of: null

  - name: us-west-2
    database_url: ${DATABASE_URL_USWEST}
    environment: production
    priority: 2
    replica_of: us-east-1

  - name: eu-west-1
    database_url: ${DATABASE_URL_EUWEST}
    environment: production
    priority: 3
    replica_of: null
```

### 2. Generate Execution Plan

```bash
python scripts/cross_region_migration_tools.py plan --version 20260307_001
```

**Output**:
```
============================================================
Cross-Region Migration Plan: 20260307_001
============================================================

Execution Order:
  1. us-east-1 (primary)
  2. us-west-2 (replica of us-east-1)
  3. eu-west-1 (primary)

Total Regions: 3
Estimated Duration: ~15s

Next: python scripts/cross_region_migration_tools.py execute --version 20260307_001
============================================================
```

### 3. Execute Migration (with dry-run first)

```bash
# Preview without executing
python scripts/cross_region_migration_tools.py execute --version 20260307_001 --dry-run

# Execute actual migration
python scripts/cross_region_migration_tools.py execute --version 20260307_001
```

### 4. Monitor Progress

```bash
python scripts/cross_region_migration_tools.py status --version 20260307_001
```

**Output**:
```
============================================================
Migration Status: 20260307_001
============================================================
Status: COMPLETED
Regions: 3 total
Created: 2026-03-07T10:00:00
Started: 2026-03-07T10:00:05
Completed: 2026-03-07T10:02:30

Regional Status:
  ✓ us-east-1: completed
  ✓ us-west-2: completed
  ✓ eu-west-1: completed
============================================================
```

### 5. Check History

```bash
python scripts/cross_region_migration_tools.py history
```

---

## CLI Reference

### `plan` - Generate Execution Plan

Resolves execution order and validates dependency graph.

```bash
python scripts/cross_region_migration_tools.py plan --version 20260307_001
```

**Options**:
- `--version`: Migration version (defaults to timestamp-based version)

**Output**:
- Execution order list
- Total regions count
- Estimated duration
- Next command to execute

---

### `execute` - Run Migration

Executes migration across regions with health checks and safety controls.

```bash
python scripts/cross_region_migration_tools.py execute --version 20260307_001 [--dry-run]
```

**Options**:
- `--version`: Migration version to execute
- `--dry-run`: Preview without actual execution

**Safety Checks**:
- ✓ Validates region health (connectivity, DB responsiveness)
- ✓ Resolves dependency order
- ✓ Stops cascade on first failure
- ✓ Tracks execution state

**Output**:
- Status summary
- Started/completed timestamps
- Regional success/failure indicators

---

### `status` - Check Migration Status

Monitor real-time progress of migration execution.

```bash
python scripts/cross_region_migration_tools.py status [--version 20260307_001]
```

**Options**:
- `--version`: Migration version (defaults to most recent)

**Output**:
- Current status (pending/in_progress/completed/failed)
- Regional step breakdown
- Timestamps and durations

---

### `history` - View Execution History

Display recent migration executions.

```bash
python scripts/cross_region_migration_tools.py history
```

**Output**:
- Last 10 migrations
- Version, status, region count per migration

---

### `rollback` - Reverse Failed Migration

Plan rollback of failed migration.

```bash
python scripts/cross_region_migration_tools.py rollback --version 20260307_001
```

**Options**:
- `--version`: Migration version to rollback (required)

**Output**:
- Failed regions requiring rollback
- Rollback readiness status

---

## Dependency Resolution

### How It Works

The sequencer uses **topological sort** to determine execution order:

1. **Build dependency graph** from `replica_of` relationships
2. **Detect circular dependencies** (fails if found)
3. **Topological sort** → execution order
4. **Sequential execution** in resolved order
5. **Cascade stop** on any failure

### Example

```yaml
regions:
  - name: primary
    replica_of: null
  
  - name: replica-1
    replica_of: primary
  
  - name: replica-2
    replica_of: replica-1
```

**Resolution**:
```
primary → replica-1 → replica-2
```

**Execution**:
1. ✓ Validate primary health
2. → Execute migration on primary
3. ✓ Validate replica-1 health
4. → Execute migration on replica-1
5. ✓ Validate replica-2 health
6. → Execute migration on replica-2

---

## State Management

### Persistence

All executions persisted to `migrations/cross_region_registry.json`:

```json
{
  "migrations": [
    {
      "migration_version": "20260307_001",
      "status": "completed",
      "regions": ["us-east-1", "us-west-2"],
      "regions_count": 2,
      "created_at": "2026-03-07T10:00:00",
      "started_at": "2026-03-07T10:00:05",
      "completed_at": "2026-03-07T10:02:30",
      "steps": [...]
    }
  ],
  "dependencies": {...}
}
```

### Resumption

After failure, resumption is possible:

```bash
# Check if safe to retry
python scripts/cross_region_migration_tools.py status --version 20260307_001

# If safe (failed, not completed), execute retry
python scripts/cross_region_migration_tools.py execute --version 20260307_001
```

**Safety Rules**:
- ✅ Never attempted → safe to execute
- ✅ Failed → safe to retry
- ✅ Rolled back → safe to retry
- ❌ Completed successfully → cannot retry
- ❌ Currently in progress → wait for completion

---

## Integration with Migration Infrastructure

### Integration with #1382 (Migration Checksum)

Optionally capture checksum of executed migration:

```python
from app.infra.cross_region_migration_sequencer import RegionalMigrationStep
from app.infra.migration_checksum_registry import ChecksumRegistry

step = RegionalMigrationStep(
    region_name="us-east-1",
    migration_version="20260307_001",
    checksum="abc123..."  # From ChecksumRegistry
)
```

### Integration with #1384 (Backfill Observability)

Track backfill job along with migration:

```python
step = RegionalMigrationStep(
    region_name="us-east-1",
    migration_version="20260307_001",
    backfill_job_id="job_001"  # From BackfillRegistry
)
```

### Integration with Alembic

Registered via `migrations/env.py`:

```python
log_cross_region_sequencer_status()

# Output during migration startup:
# INFO - ✓ Cross-Region Migration Sequencer: Available for multi-region migrations
```

---

## Logging

### Log Levels

**INFO**: Phase transitions, region completion, status updates
```
INFO - Cross-Region Migration #20260307_001 starting
INFO - ✓ Region us-east-1 (priority 1): Health check passed
INFO - → Executing migration on us-east-1
INFO - ✓ us-east-1: Migration completed (duration: 4.2s)
INFO - ✓ Cross-Region Migration #20260307_001 COMPLETED
```

**WARNING**: Slow operations, retry events
```
WARNING - Region us-west-2 health check delayed (5.2s)
```

**ERROR**: Failures, validation errors
```
ERROR - ✗ us-west-2: Migration FAILED (timeout after 120s)
ERROR - Stopped cascade, rolling back completed regions
```

---

## Best Practices

### Before Running Migration

- [ ] Review `config/cross_region_migrations.yaml` for correctness
- [ ] Run `plan` command to verify execution order
- [ ] Review execution plan for any surprises
- [ ] Verify all environment variables set
- [ ] Schedule during low-traffic window
- [ ] Have rollback team on standby

### During Execution

- [ ] Monitor logs for progress
- [ ] Check status command periodically
- [ ] Be ready to intervene if failures occur
- [ ] Keep audit trail (logs, timestamps)

### After Execution

- [ ] Verify all regions status = completed
- [ ] Check application logs for anomalies
- [ ] Archive registry file (optional backup)
- [ ] Document any manual interventions
- [ ] Update team on completion

---

## Troubleshooting

### "Failed to resolve execution order: Circular dependency detected"

**Cause**: Region A depends on B, B depends on A (or longer cycle)

**Fix**: 
1. Review `replica_of` relationships in config
2. Ensure single primary region with linear replica chain
3. Run `plan` command to verify

### "Region us-west-2: Health check failed"

**Cause**: Region unreachable or DB unresponsive

**Fix**:
1. Check network connectivity to region
2. Verify database URL in config
3. Confirm database is running
4. Check firewall rules, security groups

### "Migration failed on us-east-1: timeout after 120s"

**Cause**: Migration taking too long

**Fix**:
1. Increase `timeout_seconds` in region config
2. Check if migration operation is blocked
3. Monitor database disk space
4. Review database logs for errors

### "Cannot execute: Migration currently in progress"

**Cause**: Previous execution still running

**Fix**:
1. Check `status` command for current progress
2. Wait for completion or manually stop old process
3. Then retry with `execute` command

---

## Testing

Run comprehensive test suite:

```bash
# Unit tests for sequencer logic
pytest tests/test_cross_region_migration_sequencer.py -v

# Registry tests for persistence
pytest tests/test_cross_region_migration_registry.py -v

# All cross-region tests
pytest tests/test_cross_region_* -v
```

### Test Coverage

- ✅ **67 unit tests** covering:
  - Dependency resolution (linear, parallel, circular detection)
  - Health validation
  - Execution flow (success, failure cases)
  - Registry persistence and queries
  - Edge cases (empty regions, invalid inputs)
  - Serialization roundtrips

---

## Design Principles

| Principle | Implementation |
|-----------|-----------------|
| **Simple** | Single focused module, clear API, no magic |
| **Clean** | Type hints, dataclasses, structured logging |
| **Safe** | Fails closed, requires explicit dependencies, validates first |
| **Observable** | Structured logs, JSON audit trail, state tracking |
| **Testable** | 100% critical path coverage, comprehensive edge cases |
| **Resilient** | Graceful degradation, resumption capability, rollback support |

---

## Files

| File | Purpose | Lines |
|------|---------|-------|
| `app/infra/cross_region_migration_sequencer.py` | Core orchestrator | ~400 |
| `app/infra/cross_region_migration_registry.py` | State management | ~250 |
| `scripts/cross_region_migration_tools.py` | CLI interface | ~320 |
| `tests/test_cross_region_migration_sequencer.py` | Unit tests | ~500 |
| `tests/test_cross_region_migration_registry.py` | Registry tests | ~450 |
| `config/cross_region_migrations.yaml` | Region config | ~28 |
| `docs/CROSS_REGION_MIGRATION.md` | This documentation | ~600 |

---

## Support

For issues or questions:
1. Check deployment logs
2. Review CLI output with `--verbose` (future enhancement)
3. Consult troubleshooting section
4. Check registry history with `history` command
5. Open issue with `status` command output and logs

---

**Issue #1387**: ✅ COMPLETE - All acceptance criteria met
