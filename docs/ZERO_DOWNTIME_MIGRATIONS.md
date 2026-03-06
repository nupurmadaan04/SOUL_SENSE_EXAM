# Zero-Downtime Column Type Change Playbook

## Overview

The **Zero-Downtime Playbook** automates safe column type changes with minimal downtime. It uses a 6-stage workflow to migrate columns from one type to another without blocking concurrent reads and writes.

**Key Benefits:**
- ✅ Zero data loss
- ✅ Minimal downtime (<1 second for cutover)
- ✅ Handles concurrent application traffic
- ✅ Automatic rollback on failure
- ✅ Observability and progress tracking

---

## How It Works

### 6-Stage Workflow

```
1. PREFLIGHT       → Validate table, column, transformation
2. SHADOW          → Create new column with target type
3. BACKFILL        → Copy and transform data (batched)
4. VALIDATION      → Verify data integrity
5. CUTOVER         → Swap columns (brief lock)
6. CLEANUP         → Remove backup column
```

### Timeline for a 1M Row Table

| Stage | Duration | Downtime | Impact |
|-------|----------|----------|--------|
| Preflight | 100ms | None | Validation only |
| Shadow | 50ms | None | DDL (no lock) |
| Backfill | ~30 seconds | None | Batched updates, concurrent traffic OK |
| Validation | 200ms | None | SELECT COUNT(*) |
| Cutover | 500ms | <1s | Brief table lock |
| Cleanup | 50ms | None | DDL |
| **Total** | **~30 seconds** | **<1s** | **Mostly non-blocking** |

---

## Usage Example

### Simple Type Change (INTEGER → VARCHAR)

```python
from sqlalchemy import create_engine
from app.infra.zero_downtime_playbook import ZeroDowntimePlaybook, ColumnTypeChange

# Setup
engine = create_engine("postgresql://user:pass@localhost/mydb")
playbook = ZeroDowntimePlaybook(engine)

# Define the change
change = ColumnTypeChange(
    table_name="users",
    column_name="age",
    new_type="VARCHAR"
)

# Execute
result = playbook.execute(change)

# Check result
if result.passed:
    print(f"✅ Success! Time: {result.total_duration_ms}ms")
    print(f"Rows migrated: {result.metrics['rows_backfilled']}")
else:
    print(f"❌ Failed: {result.error_message}")
```

### Custom Transformation

If you need special logic during transformation:

```python
def age_to_string(val):
    """Convert age integer to formatted string."""
    if val is None:
        return None
    if val < 0:
        raise ValueError(f"Invalid age: {val}")
    return f"AGE_{val:03d}"

change = ColumnTypeChange(
    table_name="users",
    column_name="age",
    new_type="VARCHAR",
    transformation_func=age_to_string
)

result = playbook.execute(change)
```

---

## Configuration

### PlaybookConfig Options

```python
from app.infra.zero_downtime_playbook import PlaybookConfig

config = PlaybookConfig(
    enable_preflight_checks=True,      # Always validate (recommended)
    enable_dry_run_mode=False,         # Set True to test without committing
    batch_size=10000,                  # Rows per batch during backfill
    timeout_seconds=3600,              # Max 1 hour per migration
    require_approval=False              # Can add approval gates later
)

playbook = ZeroDowntimePlaybook(engine, config=config)
```

### Dry-Run Mode

Test a migration without committing changes:

```python
config = PlaybookConfig(enable_dry_run_mode=True)
playbook = ZeroDowntimePlaybook(engine, config=config)
result = playbook.execute(change)
# Migration is rolled back automatically (shadows created but not committed)
```

---

## Edge Cases Handled

### 1. **Degraded Database**
- Slow queries during backfill? → Batching prevents lock contention
- Connection timeouts? → Each batch is a separate transaction

### 2. **Invalid Inputs**
- Missing table? → Caught at preflight ✅
- Column doesn't exist? → Caught at preflight ✅
- Bad transformation function? → Tested at preflight ✅

### 3. **Concurrency Race Conditions**
- Concurrent writes to old column during migration?
  - Shadow column backfill ignores new writes
  - Cutover swaps atomically (no partial state)
  - Old and new columns never both active simultaneously

### 4. **Data Type Incompatibility**
- VARCHAR has stricter width limits than TEXT?
  - Validation stage catches mismatches → rollback
  - Sample validation checks first 100 rows

### 5. **Timeouts**
- Backfill exceeds configured timeout?
  - Batching prevents long-running transactions
  - If timeout hits → automatic rollback

### 6. **Rollback Scenarios**

| Failure Point | Action |
|---------------|--------|
| Preflight fails | No changes made |
| Shadow creation fails | No data touching |
| Backfill fails | Shadow column dropped |
| Validation fails | Shadow column dropped, old data intact |
| Cutover fails | Old column retained, cleanup skipped |

---

## Output & Observability

### Result Object

```python
result = playbook.execute(change)

# Access results
print(f"Passed: {result.passed}")
print(f"Status: {result.status.value}")  # success, failed, rolled_back, timeout
print(f"Error: {result.error_message}")
print(f"Duration: {result.total_duration_ms}ms")

# Stage-by-stage breakdown
for stage in result.stages:
    print(f"{stage.stage.value}: {stage.passed} ({stage.duration_ms}ms)")

# Metrics
print(f"Rows migrated: {result.metrics['rows_backfilled']}")
print(f"Cutover downtime: {result.metrics['cutover_downtime_ms']}ms")

# JSON for logging
import json
print(json.dumps(result.to_dict(), indent=2))
```

### Sample Output

```json
{
  "passed": true,
  "status": "success",
  "table": "users",
  "column": "age",
  "new_type": "VARCHAR",
  "stages": [
    {"stage": "preflight", "passed": true, "duration_ms": 45.3, "rows_affected": 0},
    {"stage": "shadow", "passed": true, "duration_ms": 32.1, "rows_affected": 0},
    {"stage": "backfill", "passed": true, "duration_ms": 28543.2, "rows_affected": 1000000},
    {"stage": "validation", "passed": true, "duration_ms": 156.8, "rows_affected": 1000000},
    {"stage": "cutover", "passed": true, "duration_ms": 0.8, "rows_affected": 0},
    {"stage": "cleanup", "passed": true, "duration_ms": 35.1, "rows_affected": 0}
  ],
  "total_duration_ms": 28813.3,
  "metrics": {
    "shadow_column": "age_new",
    "rows_backfilled": 1000000,
    "cutover_downtime_ms": 0.8
  }
}
```

---

## Testing the Playbook

### Run Unit Tests

```bash
pytest tests/test_zero_downtime_playbook.py -v
```

### Test Coverage

- ✅ Preflight validation (table/column/shadow checks)
- ✅ Shadow column creation
- ✅ Backfill with and without transformation
- ✅ NULL handling
- ✅ Data integrity validation
- ✅ Cutover column swap
- ✅ Cleanup
- ✅ End-to-end success flow
- ✅ Failure scenarios (preflight, backfill, validation)
- ✅ Automatic rollback
- ✅ Edge cases (large datasets, timeouts, bad transforms)

---

## When to Use Zero-Downtime vs. Maintenance Window

### Use Zero-Downtime Playbook When:
- Table has concurrent traffic you can't pause
- Type change is simple (e.g., INTEGER → VARCHAR)
- Transformation function is simple
- Table fits in available disk space (shadow column)

### Use Maintenance Window When:
- Large table (>10M rows) + small disk space
- Complex transformation with dependencies
- Adding NOT NULL constraints (safety)
- Coordinating with cache invalidation

---

## Troubleshooting

### "Shadow column already exists"
- Previous migration failed partway through
- Manually drop the `{column}_new` column and retry

### "Data mismatch: 100 rows in old, 95 in shadow"
- Concurrent deletes happened during backfill
- This is probably OK (data was deleted)
- Check application logs for DELETE statements

### "Cutover downtime exceeded 1 second"
- Table has many columns/indexes
- Index maintenance slowed the swap
- Consider defragmentation before retry

### "Transformation function failed"
- Invalid test case in preflight (e.g., convert NULL)
- Fix transformation function logic and retry

---

## API Reference

### `ZeroDowntimePlaybook`

```python
class ZeroDowntimePlaybook:
    def __init__(self, engine: Engine, config: PlaybookConfig = None)
    def execute(self, change: ColumnTypeChange) -> PlaybookResult
```

### `ColumnTypeChange`

```python
@dataclass
class ColumnTypeChange:
    table_name: str                              # Required: table to modify
    column_name: str                             # Required: column to change
    new_type: str                                # Required: new SQL type (e.g., "VARCHAR")
    transformation_func: Callable[[Any], Any]   # Optional: data transform logic
    batch_size: int = 10000                      # Rows per batch during backfill
    timeout_seconds: int = 3600                  # Max 1 hour per migration
```

### `PlaybookResult`

```python
@dataclass
class PlaybookResult:
    passed: bool                                 # Did migration succeed?
    status: PlaybookStatus                       # success | failed | rolled_back | timeout
    change: ColumnTypeChange                     # Original change request
    stages: List[StageResult]                    # Breakdown by stage
    error_message: str                           # Reason for failure (if failed)
    total_duration_ms: float                     # Total execution time
    metrics: Dict[str, Any]                      # shadow_column, rows_backfilled, cutover_downtime_ms
```

---

## Future Enhancements

- [ ] Support for PostgreSQL-specific features (ADD CONSTRAINT)
- [ ] Parallel backfill across multiple workers
- [ ] Approval gates before cutover
- [ ] Metrics integration (Prometheus, DataDog)
- [ ] CLI tool: `soul-sense migrate-column --table users --column age --type VARCHAR`
- [ ] Web dashboard showing migration progress

---

## Questions?

Refer to the inline comments in `app/infra/zero_downtime_playbook.py` or run the test suite:

```bash
pytest tests/test_zero_downtime_playbook.py -v --tb=short
```
