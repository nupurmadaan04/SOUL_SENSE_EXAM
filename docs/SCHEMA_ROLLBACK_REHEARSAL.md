# Schema Rollback Rehearsal Pipeline

## Overview

The **Schema Rollback Rehearsal Pipeline** validates that database migrations can be safely reversed before production deployment. It tests every migration's reversibility, detects non-reversible operations, and provides operators with clear guidance before rollouts.

### Why This Matters

In production environments, migrations can fail for many reasons:
- Database changes that can't be easily undone
- Constraint violations on rollback
- Data loss due to DROP/DELETE operations
- Partial execution due to timeouts

**This pipeline prevents catastrophic failures** by rehearsing every migration's down path before it reaches production.

---

## Quick Start (2 minutes)

### 1. Basic Usage

```bash
# Test all pending migrations
python scripts/rollback_rehearsal_tools.py rehearse-pending

# Check a single migration
python scripts/rollback_rehearsal_tools.py check-safety 001_create_users

# View metrics
python scripts/rollback_rehearsal_tools.py metrics
```

### 2. Interpret the Output

```
✓ 001_create_users
  Status: PASSED (reversible)
  Reversibility Score: 100%
  Duration: 45ms

⚠ 002_drop_legacy_field
  Status: WARNING (has issues)
  Reversibility Score: 50%
  Warnings: DROP COLUMN is non-reversible; data cannot be restored
  Recommendation: Use soft delete instead

❌ 003_alter_pk_type
  Status: FAILED
  Error: Cannot safely reverse - no rollback equivalent defined
  Recommendation: Add explicit down() migration
```

**Legend:**
- ✓ = Safe to deploy
- ⚠ = Review before deployment
- ❌ = Redesign migration before deploying

---

## Architecture

### Components

#### 1. **RollbackRehearsalPipeline** (`app/infra/schema_rollback_rehearsal.py`)
- Discovers pending migrations
- Executes migration rehearsals
- Validates reversibility
- Provides detailed reports

#### 2. **RollbackSafetyValidator**
- Detects non-reversible operations in migration code
- Calculates reversibility scores (0-100%)
- Identifies dangerous patterns (DROP, DELETE, TRUNCATE)

#### 3. **RollbackRehearsalRegistry** (`app/infra/rollback_rehearsal_registry.py`)
- Persists rehearsal results as audit trail
- Tracks metrics over time
- Calculates aggregate statistics

#### 4. **CLI Tools** (`scripts/rollback_rehearsal_tools.py`)
- Operator-friendly commands
- Professional formatted output
- Integration with CI/CD pipelines

### How It Works

```
1. Discover pending migrations (migrations with both upgrade + downgrade)
2. For each migration:
   - Scan code for non-reversible operations (DROP, DELETE, etc.)
   - Calculate reversibility score based on patterns detected
   - Generate warnings and recommendations
   - Record results in registry
3. Display results with actionable guidance
4. Exit with status 0 (safe) or 1 (has issues)
```

---

## Concepts

### Reversibility Score

A **0-100% score** indicating how safely a migration can be reversed:

| Score | Meaning | Examples |
|-------|---------|----------|
| **100%** | Fully reversible | Adding columns with defaults, renaming tables safely |
| **75-99%** | Mostly reversible | Index creation, constraint addition |
| **50-74%** | Risky | Operations that require careful data handling |
| **<50%** | Non-reversible | DROP, DELETE, TRUNCATE operations |

### Non-Reversible Operations

Operations that **cannot be safely undone**:

| Operation | Risk | Solution |
|-----------|------|----------|
| `DROP TABLE` | Complete data loss | Use soft deletes or archival |
| `DROP COLUMN` | Data loss | Use soft deletes, migration flags |
| `DELETE FROM` | Data loss | Archive data first, use backups |
| `TRUNCATE` | All data lost | Use DELETE with WHERE clause |
| `ALTER TYPE` | Data conversion failure | Test conversion thoroughly |

### Warnings vs Failures

**Warnings** (⚠):
- Indicate potential issues
- Can sometimes be deployed with careful monitoring
- Score 50-75%
- Require manual review

**Failures** (❌):
- Block deployment
- Score <50%
- Require redesign before proceeding

---

## Database-Specific Patterns

### PostgreSQL Considerations

Safe patterns:
```python
# ADD COLUMN with DEFAULT (safe)
def upgrade():
    op.add_column('users', sa.Column('status', sa.String, default='active'))
def downgrade():
    op.drop_column('users', 'status')

# CREATE INDEX CONCURRENTLY (safe, no lock)
def upgrade():
    op.execute("CREATE INDEX CONCURRENTLY idx_status ON users(status)")
def downgrade():
    op.execute("DROP INDEX CONCURRENTLY idx_status")
```

Risky patterns:
```python
# DROP COLUMN (data loss)
def upgrade():
    op.drop_column('users', 'legacy_field')  # ❌ Dangerous

# ALTER COLUMN TYPE without careful casting
def upgrade():
    op.alter_column('users', 'age', type_=sa.String)  # ⚠ Risky
```

### MySQL Considerations

Safe patterns:
```python
# INPLACE operations (fast, no lock)
def upgrade():
    op.add_column('users', sa.Column('email', sa.String(100)))

# Online index creation
def upgrade():
    op.create_index('idx_email', 'users', ['email'], algorithm='INPLACE')
```

---

## CLI Reference

### Command: `rehearse-pending`

Test all pending migrations.

```bash
python scripts/rollback_rehearsal_tools.py rehearse-pending
```

**Output:**
- Table of all migrations with status, score, duration
- Detailed warnings for each migration with issues
- Summary statistics
- Exit code: 0 if all passed, 1 if any failed

### Command: `check-safety`

Check reversibility of a specific migration.

```bash
python scripts/rollback_rehearsal_tools.py check-safety 001_create_users
```

**Output:**
- Status (PASSED/WARNING/FAILED)
- Reversibility score
- Warnings and recommendations
- Non-reversible operations detected

**Use case:** Before deploying a specific migration, verify it can be safely rolled back.

### Command: `metrics`

View aggregate statistics.

```bash
python scripts/rollback_rehearsal_tools.py metrics
```

**Output:**
- Total rehearsals run
- Pass/warning/failure rates
- Average reversibility score
- List of non-reversible migrations

**Use case:** Dashboard view of overall migration rollback safety health.

### Command: `history`

Show past rehearsals for a migration.

```bash
python scripts/rollback_rehearsal_tools.py history 001_create_users
```

**Output:**
- Timestamp, status, score, duration for each past rehearsal
- Track how reversibility changes over time

**Use case:** Audit trail showing when migrations were tested and results.

### Command: `help`

Show CLI documentation.

```bash
python scripts/rollback_rehearsal_tools.py help
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Migration Safety Check

on: [pull_request, push]

jobs:
  rehearse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Rehearse migrations
        run: python scripts/rollback_rehearsal_tools.py rehearse-pending
        env:
          DATABASE_URL: sqlite:///test.db
      
      - name: Check metrics
        run: python scripts/rollback_rehearsal_tools.py metrics
```

### Pre-deployment Checklist

Before deploying to production:

```bash
# 1. Rehearse all pending migrations
python scripts/rollback_rehearsal_tools.py rehearse-pending

# 2. Check if any have low scores
python scripts/rollback_rehearsal_tools.py metrics

# 3. Review problematic migrations
python scripts/rollback_rehearsal_tools.py check-safety <migration-version>

# 4. Only proceed if all pass ✓
```

---

## Best Practices

### 1. Always Include Reversible Down Methods

```python
# ✓ Good - down() reverses up()
def upgrade():
    op.add_column('users', sa.Column('status', sa.String))

def downgrade():
    op.drop_column('users', 'status')

# ❌ Bad - down() is empty
def upgrade():
    op.add_column('users', sa.Column('status', sa.String))

def downgrade():
    pass  # Can't reverse!
```

### 2. Avoid Destructive Operations

```python
# ❌ Avoid
def upgrade():
    op.drop_column('users', 'old_field')
    op.execute("DELETE FROM users WHERE status='inactive'")

# ✓ Use soft deletes instead
def upgrade():
    op.add_column('users', sa.Column('deleted_at', sa.DateTime))

def downgrade():
    op.drop_column('users', 'deleted_at')
```

### 3. Test Large Data Migrations

```python
# For large backfills, test reversibility
def test_large_backfill():
    # Generate test data
    # Execute upgrade
    # Verify data is updated
    # Execute downgrade
    # Verify original state
    pass
```

### 4. Document Migration Intent

```python
def upgrade():
    """Add email field for new auth system (PR #123)."""
    op.add_column('users', sa.Column('email', sa.String(100)))

def downgrade():
    """Rollback to original schema."""
    op.drop_column('users', 'email')
```

---

## API Reference

### RollbackRehearsalPipeline

```python
from app.infra.schema_rollback_rehearsal import RollbackRehearsalPipeline

pipeline = RollbackRehearsalPipeline(database_url="postgresql://...")

# Discover migrations
migrations = pipeline.discover_pending_migrations()
# Returns: List[MigrationInfo]

# Rehearse single migration
result = pipeline.rehearse_migration("001_create_users")
# Returns: RehearsalResult

# Rehearse all
results, summary = pipeline.rehearse_all_pending()
# Returns: (List[RehearsalResult], Dict)
```

### RollbackSafetyValidator

```python
from app.infra.schema_rollback_rehearsal import RollbackSafetyValidator

code = open("migration.py").read()

warnings, score = RollbackSafetyValidator.detect_non_reversible_operations(code)
# Returns: (List[str], int 0-100)
```

### RollbackRehearsalRegistry

```python
from app.infra.rollback_rehearsal_registry import get_rollback_rehearsal_registry

registry = get_rollback_rehearsal_registry()

# Record results
registry.record_rehearsal(result)
registry.record_batch([result1, result2])

# Query results
history = registry.get_rehearsal_history("001_create_users")
latest = registry.get_latest_rehearsal("001_create_users")

# Get metrics
metrics = registry.get_aggregate_metrics()
```

---

## Troubleshooting

### "Rehearsal failed with timeout"

**Cause:** Large migrations took too long to validate.

**Solution:**
```bash
# Run with longer timeout (if implemented)
# Or split large migration into smaller steps
```

### "Non-reversible operations detected"

**Cause:** Migration uses DROP, DELETE, or other dangerous operations.

**Solution:**
1. Review the migration design
2. Use soft deletes or shadow tables instead
3. Ensure data is archived before deletion
4. Split into smaller, reversible steps

### "No downgrade equivalent defined"

**Cause:** Migration file has `upgrade()` but no `downgrade()` method.

**Solution:**
```python
# Add downgrade function
def downgrade():
    """Revert changes from upgrade()."""
    # Reverse the operations here
    pass
```

### "Registry corruption"

**Cause:** JSON registry file is malformed.

**Solution:**
```bash
# Delete corrupted registry (new one will be created)
rm migrations/rollback_rehearsal_registry.json

# Rehearse again
python scripts/rollback_rehearsal_tools.py rehearse-pending
```

---

## Examples

### Example 1: Safe Migration (Score: 100%)

```python
# migrations/versions/001_create_users.py
"""Create users table"""

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), unique=True)
    )

def downgrade():
    op.drop_table('users')
```

**Rehearsal Result:**
```
✓ 001_create_users
  Status: PASSED
  Reversibility Score: 100%
  Warnings: None
  Duration: 15ms (up) + 12ms (down)
```

### Example 2: Migration with Concerns (Score: 65%)

```python
# migrations/versions/002_drop_legacy_field.py
"""Remove legacy column"""

def upgrade():
    # ❌ This is destructive
    op.drop_column('users', 'legacy_phone')

def downgrade():
    # Can't recover deleted data!
    op.add_column('users', sa.Column('legacy_phone', sa.String(20)))
```

**Rehearsal Result:**
```
⚠ 002_drop_legacy_field
  Status: WARNING
  Reversibility Score: 65%
  Warnings:
    - DROP COLUMN - data loss
  Recommendation: Use soft delete or shadow table swap
  Duration: 8ms (up) + 10ms (down)
```

---

## Files

| File | Purpose |
|------|---------|
| `app/infra/schema_rollback_rehearsal.py` | Core pipeline logic |
| `app/infra/rollback_rehearsal_registry.py` | Result persistence |
| `scripts/rollback_rehearsal_tools.py` | Operator CLI |
| `tests/test_schema_rollback_rehearsal.py` | Comprehensive tests |
| `migrations/rollback_rehearsal_registry.json` | Audit trail |

---

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest tests/test_schema_rollback_rehearsal.py -v

# Specific test category
pytest tests/test_schema_rollback_rehearsal.py::TestSafetyValidation -v

# With coverage
pytest tests/test_schema_rollback_rehearsal.py --cov=app.infra
```

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review migration examples
3. Consult the CLI help: `python scripts/rollback_rehearsal_tools.py help`
4. Check repository documentation
