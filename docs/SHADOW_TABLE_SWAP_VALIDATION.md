# Shadow Table Swap Validation Framework

Zero-downtime migration validation for shadow table pattern.



## Overview

**Shadow table swap** is a zero-downtime migration pattern:

1. Create new table (shadow) with desired schema
2. Backfill data from original table
3. **Validate consistency before swap** (this framework)
4. Swap tables atomically by renaming
5. Recover by restoring from backup if needed

Without validation, swaps can introduce data drift, schema mismatches, or FK violations. This framework **prevents** these issues.

---

## Quick Start

### 1. Create Shadow Table
```sql
CREATE TABLE users_new AS SELECT * FROM users WHERE FALSE;
ALTER TABLE users_new ADD COLUMN phone VARCHAR(20);
```

### 2. Backfill Data
```sql
INSERT INTO users_new (id, email, name, phone)
SELECT id, email, name, NULL FROM users;
```

### 3. Validate Before Swap
```bash
python scripts/shadow_table_tools.py pre-swap \
    --original users \
    --shadow users_new
```

Expected output:
```
🟢 Schema Validation: ✓ PASS
🟢 Data Integrity: ✓ PASS
🟢 Foreign Key Safety: ✓ PASS

✅ All validations passed - SAFE TO SWAP
```

### 4. Perform Swap
```sql
ALTER TABLE users RENAME TO users_old;
ALTER TABLE users_new RENAME TO users;
```

### 5. Validate Post-Swap
```bash
python scripts/shadow_table_tools.py post-swap \
    --backup users_old \
    --active users
```

---

## CLI Reference

### Pre-Swap Validation
```bash
python scripts/shadow_table_tools.py pre-swap \
    --original <table> \
    --shadow <table> \
    [--database-url <url>]
```
Validates schema, data integrity, and FK safety before swap.

### Post-Swap Validation
```bash
python scripts/shadow_table_tools.py post-swap \
    --backup <backup-table> \
    --active <active-table> \
    [--database-url <url>]
```
Confirms swap completed successfully.

### Compare Schemas
```bash
python scripts/shadow_table_tools.py compare-schema \
    --table1 <table> \
    --table2 <table>
```
Inspect schema differences between tables.

### Rollback Plan
```bash
python scripts/shadow_table_tools.py rollback-plan \
    --original <active-table> \
    --shadow <backup-table>
```
Generate rollback instructions.

---

## API Reference

### ShadowTableSwapValidator

```python
from sqlalchemy import create_engine
from app.infra.shadow_table_swap_validator import ShadowTableSwapValidator

engine = create_engine("postgresql://localhost/mydb")
validator = ShadowTableSwapValidator(engine)
```

**validate_pre_swap(original_table, shadow_table)**
- Returns: `SwapValidationResult`
- Validates schema, data integrity, FK safety
- Blocks swap if any check fails with recommendations

**validate_post_swap(original_table_old, new_active_table)**
- Returns: `SwapValidationResult`
- Confirms backup and active tables exist
- Use after swap to verify success

**compare_schemas(table1, table2)**
- Returns: `TableSchemaComparison`
- Detects missing/extra columns and type mismatches

---

## Troubleshooting

### Row Count Mismatch
```
Error: Row count mismatch: 1000 vs 950
Solution: Re-sync missing rows, then re-run validation
```

### Checksum Mismatch
```
Error: Data checksum mismatch - possible data divergence
Solution: Verify data matches, re-sync if needed
```

### Schema Mismatch
```
Error: Missing columns: ['phone']
Solution: Add missing columns to shadow table, re-validate
```

### Foreign Key Errors
```
Error: Foreign Key Safety: FAIL
Solution: Verify FK constraints on shadow table
```

---

## Best Practices

1. **Always validate before swap** - Never skip pre-swap validation
2. **Keep backups 24-48 hours** - Enables rollback if issues arise
3. **Validate post-swap** - Confirm swap completed successfully
4. **Test on staging first** - Run full migration process on staging before production
5. **Document swap plan** - Timestamp, rollback procedure, owner

---

## Architecture

```
ShadowTableSwapValidator
├── Schema Validation: Column definitions, types, nullability
├── Data Integrity: Row counts, SHA-256 checksums
└── FK Safety: Foreign key constraint validation
```

**Validation Phases:**
- **Pre-swap**: Run before renaming tables (prevents bad swaps)
- **Post-swap**: Run after swap (confirms success)

---

**Last Updated:** March 7, 2026  
**Framework Version:** 1.0  
**Status:** Production Ready
