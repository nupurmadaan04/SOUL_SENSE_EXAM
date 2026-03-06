# Online Index Creation Policy Guard

**Version**: 1.0  
**Status**: Active  
**Created**: March 6, 2026

## Overview

The Online Index Creation Policy Guard is a safety mechanism that validates database indexes against production best practices before execution. It prevents regression risk by enforcing database-specific policies for zero-downtime index creation.

**Key Benefits**:
- ✅ Catches index creation issues before deployment
- ✅ Database-specific best practices enforced
- ✅ Zero-downtime recommendations for PostgreSQL & MySQL
- ✅ Actionable error messages with SQL syntax
- ✅ Structured logging for audit trails
- ✅ Minimal overhead, graceful degradation

---

## Quick Start

### 1. Basic Validation (Python)

```python
from app.infra.online_index_policy import validate_index_in_migration

# Validate a PostgreSQL index
result = validate_index_in_migration(
    db_type="postgresql",
    index_name="ix_users_email",
    table_name="users",
    columns=["email"],
    estimated_duration_seconds=45
)

if result.passed:
    print(f"✓ Safe to create: {result.index_name}")
else:
    for error in result.errors:
        print(f"✗ {error}")
```

### 2. CLI Validation

```bash
# Check a specific index
python scripts/index_policy_tools.py validate-index \
    --db-type postgresql \
    --index-name ix_users_email \
    --table-name users \
    --columns email \
    --duration 45

# Check database compatibility
python scripts/index_policy_tools.py check-compatibility postgresql
```

### 3. In Migrations (Auto-Enabled)

The policy guard is automatically integrated into Alembic migrations. When you run `alembic upgrade`, the system logs which index creation strategy to use:

```
INFO - ✓ Index Policy: PostgreSQL - using CREATE INDEX CONCURRENTLY for online creation
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────┐
│  Alembic Migration (env.py)             │
│  ├─ Detects database type               │
│  └─ Logs policy information             │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  OnlineIndexPolicyValidator             │
│  ├─ PostgreSQL Guard                    │
│  ├─ MySQL Guard                         │
│  └─ SQLite Handler                      │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  ValidationResult                       │
│  ├─ passed: bool                        │
│  ├─ checks: List[PolicyCheckResult]     │
│  ├─ errors/warnings/recommendations     │
│  └─ metrics: Dict                       │
└─────────────────────────────────────────┘
```

### Policy Classes

```python
# Define a policy to validate
from app.infra.online_index_policy import IndexDefinition, DatabaseType

index = IndexDefinition(
    name="ix_users_email",           # Index identifier
    table="users",                   # Target table
    columns=["email"],               # Column list
    is_unique=False,                 # Unique constraint?
    estimated_duration_seconds=45    # Expected time
)

# Validate it for a specific database
from app.infra.online_index_policy import OnlineIndexPolicyValidator

validator = OnlineIndexPolicyValidator(DatabaseType.POSTGRESQL)
result = validator.validate(index)

# Check result
assert result.passed          # All checks passed?
assert len(result.checks) > 0 # With details?
```

---

## Database-Specific Policies

### PostgreSQL: CREATE INDEX CONCURRENTLY

**What**: Online index creation without table locks  
**When**: Use for production, large tables, zero-downtime requirement

**Policy Checks**:
- ✓ CREATE INDEX CONCURRENTLY supported
- ✓ No write blocking (concurrent writes allowed)
- ⚠ Long duration (300+ seconds) needs monitoring

**Syntax**:
```sql
-- Create index
CREATE INDEX CONCURRENTLY ix_users_email ON users (email);

-- Drop index (in downgrade)
DROP INDEX CONCURRENTLY ix_users_email;

-- Monitor progress
SELECT * FROM pg_stat_progress_create_index;
```

**Example**:
```python
result = validate_index_in_migration(
    db_type="postgresql",
    index_name="ix_users_email",
    table_name="users",
    columns=["email"],
    estimated_duration_seconds=60
)

# Output: PASS - Safe, with CONCURRENT recommendation
```

---

### MySQL: ALGORITHM=INPLACE, LOCK=NONE

**What**: Online index creation with row-level locks only  
**When**: MySQL 5.6+, production, minimal blocking needed

**Policy Checks**:
- ✓ ALGORITHM=INPLACE supported
- ✓ LOCK=NONE available (no table locks)
- ⚠ Long duration monitoring recommended

**Syntax**:
```sql
-- Create index
ALTER TABLE users ADD INDEX ix_email (email),
  ALGORITHM=INPLACE, LOCK=NONE;

-- Drop index (in downgrade)
DROP INDEX ix_email ON users;

-- Monitor progress
SELECT * FROM performance_schema.events_stages_current 
WHERE event_name LIKE '%index%';
```

**Example**:
```python
result = validate_index_in_migration(
    db_type="mysql",
    index_name="ix_users_email",
    table_name="users",
    columns=["email"],
    estimated_duration_seconds=120
)

# Output: PASS - Safe, with INPLACE + LOCK=NONE recommendation
```

---

### SQLite: Full Table Lock (Maintenance Window Required)

**What**: No online index creation (full table lock during CREATE INDEX)  
**When**: SQLite only, maintenance window necessary

**Policy Checks**:
- ⚠ No online mode - full table lock
- ⚠ All reads/writes blocked during creation
- ⚠ Must schedule during maintenance window

**Syntax**:
```sql
-- Create index (requires maintenance window)
CREATE INDEX ix_users_email ON users (email);

-- Analyze for optimizer (recommended)
ANALYZE;

-- Drop index (in downgrade)
DROP INDEX ix_users_email;
```

**Example**:
```python
result = validate_index_in_migration(
    db_type="sqlite",
    index_name="ix_users_email",
    table_name="users",
    columns=["email"]
)

# Output: PASSES but with WARNINGS
# - "SQLite requires maintenance window for index creation"
# - Recommendation: "Schedule during off-peak hours"
```

---

## API Reference

### IndexDefinition

Represents metadata about a database index.

```python
@dataclass
class IndexDefinition:
    name: str                           # e.g., 'ix_users_email'
    table: str                          # e.g., 'users'
    columns: List[str]                  # e.g., ['email']
    is_unique: bool = False             # Unique constraint?
    estimated_duration_seconds: int = 30  # Expected creation time
    
    def validate() -> Tuple[bool, str]:
        """Validate the index definition."""
```

### OnlineIndexPolicyValidator

Main validator class.

```python
class OnlineIndexPolicyValidator:
    def __init__(self, db_type: DatabaseType):
        """Initialize with target database type."""
    
    def validate(self, index: IndexDefinition) -> ValidationResult:
        """Validate index against policies."""
        # Returns detailed ValidationResult
```

### ValidationResult

Result of index validation.

```python
@dataclass
class ValidationResult:
    passed: bool                        # All checks passed?
    index_name: str
    database_type: str
    checks: List[PolicyCheckResult]     # Individual checks
    errors: List[str]                   # Blocking issues
    warnings: List[str]                 # Non-blocking concerns
    recommendations: List[str]          # Actionable fixes
    metrics: Dict[str, Any]             # Statistics
    timestamp: str                      # ISO format timestamp
    
    def to_dict() -> Dict:
        """Convert to dictionary for logging."""
```

### Convenience Function

```python
def validate_index_in_migration(
    db_type: str,                       # 'postgresql', 'mysql', 'sqlite'
    index_name: str,                    # Index name
    table_name: str,                    # Table name
    columns: List[str],                 # Column list
    estimated_duration_seconds: int = 30,
    is_unique: bool = False
) -> ValidationResult:
    """Simple function to validate a single index."""
```

---

## CLI Tools

### Command: validate-index

Validate a specific index against policies.

**Usage**:
```bash
python scripts/index_policy_tools.py validate-index \
    --db-type <type> \
    --index-name <name> \
    --table-name <table> \
    --columns <col1,col2,...> \
    [--duration <seconds>] \
    [--unique]
```

**Examples**:
```bash
# Simple index
python scripts/index_policy_tools.py validate-index \
    --db-type postgresql \
    --index-name ix_users_email \
    --table-name users \
    --columns email

# Unique constraint, custom duration
python scripts/index_policy_tools.py validate-index \
    --db-type mysql \
    --index-name ix_account_number \
    --table-name accounts \
    --columns account_number \
    --unique \
    --duration 180

# Multi-column index
python scripts/index_policy_tools.py validate-index \
    --db-type postgresql \
    --index-name ix_user_date \
    --table-name events \
    --columns user_id,created_at \
    --duration 90
```

**Output**:
```
======================================================================
Index Policy Validation Report
======================================================================
Index:       ix_users_email
Database:    postgresql
Status:      ✓ PASS
Timestamp:   2026-03-06T10:30:45.123456

Policy Checks (2):
  ✓ must_use_concurrent
     PostgreSQL supports CREATE INDEX CONCURRENTLY
     → Use: CREATE INDEX CONCURRENTLY ix_name ON table (columns)
  ✓ must_have_rollback
     Concurrent index creation allows concurrent writes
     → Ensure corresponding DROP INDEX CONCURRENTLY in updown

Metrics:
  table: users
  columns: 1
  estimated_duration_seconds: 30
  is_unique: False
======================================================================
```

---

### Command: check-compatibility

Check if a database supports online index creation.

**Usage**:
```bash
python scripts/index_policy_tools.py check-compatibility <database>
```

**Examples**:
```bash
python scripts/index_policy_tools.py check-compatibility postgresql
python scripts/index_policy_tools.py check-compatibility mysql
python scripts/index_policy_tools.py check-compatibility sqlite
```

**Output**:
```
======================================================================
Online Index Creation Compatibility Check
======================================================================

✓ PostgreSQL - Online index creation supported
  Method:   CREATE INDEX CONCURRENTLY
  Feature:  No table locks, concurrent writes allowed
  Syntax:   CREATE INDEX CONCURRENTLY ix_name ON table (columns)
  Downgrade: DROP INDEX CONCURRENTLY ix_name

======================================================================
```

---

## Integration with Alembic

The policy guard is automatically integrated into migration execution.

### In migrations/env.py

```python
# Import is automatic
from app.infra.online_index_policy import validate_index_in_migration

# Function detects database type and logs policy info
log_index_policy_info(database_url)
```

### When Running Migrations

```bash
$ alembic upgrade head
INFO - ✓ Migration integrity verified: 27/27
INFO - ✓ Index Policy: PostgreSQL - using CREATE INDEX CONCURRENTLY for online creation

# Proceeds with migrations...
```

---

## Examples

### Example 1: PostgreSQL Large Table Index

```python
from app.infra.online_index_policy import validate_index_in_migration

# Validate index on large table
result = validate_index_in_migration(
    db_type="postgresql",
    index_name="ix_orders_user_id",
    table_name="orders",
    columns=["user_id"],
    estimated_duration_seconds=120
)

if result.passed:
    print("✓ Safe to create with:")
    print(result.recommendations[0])  
    # Output: Use: CREATE INDEX CONCURRENTLY ix_orders_user_id ON orders (user_id)
```

### Example 2: MySQL Unique Email Index

```python
result = validate_index_in_migration(
    db_type="mysql",
    index_name="ix_email_unique",
    table_name="users",
    columns=["email"],
    is_unique=True,
    estimated_duration_seconds=90
)

if result.passed:
    # Safe to create with ALGORITHM=INPLACE, LOCK=NONE
    print("✓ Unique index safe with:")
    print(result.recommendations[0])
    # Output: ALTER TABLE users ADD INDEX ix_email_unique (email),
    #         ALGORITHM=INPLACE, LOCK=NONE
```

### Example 3: SQLite Migration Window Planning

```python
result = validate_index_in_migration(
    db_type="sqlite",
    index_name="ix_journal_user_id",
    table_name="journal_entries",
    columns=["user_id"]
)

if result.warnings:
    print("⚠ Schedule during maintenance window:")
    for warning in result.warnings:
        print(f"  - {warning}")
    # Output:
    #   - SQLite requires maintenance window for index creation
    #   - Recommendation: Schedule index creation during off-peak hours
```

---

## Troubleshooting

### Issue: "Index validation failed: Invalid input"

**Cause**: Index definition is missing required fields  
**Solution**: Ensure `name`, `table`, and `columns` are all set

```python
# Wrong
result = validate_index_in_migration(
    db_type="postgresql",
    index_name="",           # ✗ Empty
    table_name="users",
    columns=[]               # ✗ Empty
)

# Correct
result = validate_index_in_migration(
    db_type="postgresql",
    index_name="ix_users_email",
    table_name="users",
    columns=["email"]
)
```

### Issue: "Unsupported database type: oracle"

**Cause**: Database type not in supported list  
**Solution**: Use one of: postgresql, mysql, sqlite

```bash
# Wrong
python scripts/index_policy_tools.py validate-index \
    --db-type oracle \              # ✗ Not supported
    --index-name ix_test \
    --table-name users \
    --columns id

# Correct
python scripts/index_policy_tools.py validate-index \
    --db-type postgresql \          # ✓ Supported
    --index-name ix_test \
    --table-name users \
    --columns id
```

### Issue: Index passes but has warnings (SQLite)

**Cause**: SQLite doesn't support online index creation  
**Solution**: Schedule index creation during maintenance window

```python
# SQLite warnings are normal
result = validate_index_in_migration(
    db_type="sqlite",
    index_name="ix_data",
    table_name="analytics",
    columns=["timestamp"]
)

# Result passes but has warnings:
# - "SQLite requires maintenance window for index creation"
# - "Recommendation: Schedule during off-peak hours"

# Action: Schedule migration during planned maintenance
```

---

## Best Practices

### 1. Always Validate Before Deployment

```python
# In your migration file or CI/CD pipeline:
from app.infra.online_index_policy import validate_index_in_migration

def validate_all_indexes():
    """Validate all new indexes before deployment."""
    indexes = [
        ("ix_users_email", "users", ["email"], 45),
        ("ix_orders_date", "orders", ["order_date", "user_id"], 180),
    ]
    
    for name, table, cols, duration in indexes:
        result = validate_index_in_migration(
            db_type="postgresql",
            index_name=name,
            table_name=table,
            columns=cols,
            estimated_duration_seconds=duration
        )
        assert result.passed, f"Index {name} validation failed"
```

### 2. Schedule SQLite Indexes During Maintenance Windows

```python
# For SQLite, always check for warnings
result = validate_index_in_migration(
    db_type="sqlite",
    index_name="ix_large_table",
    table_name="huge_data",
    columns=["important_column"]
)

if result.warnings:
    # Request maintenance window
    print("Maintenance window required for index creation")
```

### 3. Monitor Long Index Creation

```python
# For PostgreSQL, monitor progress if duration > 300s
if index_duration > 300:
    # Monitor with: SELECT * FROM pg_stat_progress_create_index
    print("Monitor index creation progress in PostgreSQL")

# For MySQL, monitor progress if duration > 300s
if index_duration > 300:
    # Monitor with: SELECT * FROM performance_schema.events_stages_current
    print("Monitor index creation progress in MySQL")
```

### 4. Include Drop/Downgrade in Migrations

```python
# Always include the reverse operation:

def upgrade():
    # PostgreSQL
    op.create_index('ix_users_email', 'users', ['email'], 
                    postgresql_using='CONCURRENTLY')

def downgrade():
    # Must match the upgrade method
    op.drop_index('ix_users_email', table_name='users',
                  postgresql_using='CONCURRENTLY')
```

---

## Metrics & Monitoring

Validation results include metrics for logging:

```json
{
  "table": "users",
  "columns": 1,
  "estimated_duration_seconds": 45,
  "is_unique": false,
  "timestamp": "2026-03-06T10:30:45.123456Z"
}
```

Structured logs allow integration with monitoring systems:

```
2026-03-06 10:30:45 INFO - Index validation: ix_users_email on postgresql - PASS
{result: {passed: true, checks: [{...}], metrics: {...}}}
```

---

## Performance

**Overhead**: < 10ms per index validation  
**Memory**: < 1MB for policy validation  
**Graceful Degradation**: If module unavailable, migrations continue with warning log

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-06 | Initial release - PostgreSQL, MySQL, SQLite support |

---

## Related Issues

- #1382: Migration Checksum Registry Enforcement
- #1381: Zero-downtime Column Type Change Playbook
- #1384: Backfill Job Observability Standard

---

## Contributing

To extend the policy guard:

1. Add new database type to `DatabaseType` enum
2. Implement checks in `OnlineIndexPolicyValidator._check_<db>()`
3. Add tests to `tests/test_online_index_policy.py`
4. Update CLI tools in `scripts/index_policy_tools.py`
5. Document in this file
