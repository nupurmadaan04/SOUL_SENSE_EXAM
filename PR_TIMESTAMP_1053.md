# Fix: Inconsistent `created_at` timestamp format (#1053)

## Summary
This PR standardizes `created_at` handling to **UTC ISO 8601** across write paths, API responses, and legacy data migration.

It resolves mixed timestamp formats (naive datetime, timezone-unaware strings, and inconsistent ISO outputs) that caused sorting inconsistencies, parsing issues on frontend clients, and timezone-related bugs.

---

## Problem
Different endpoints and model paths were emitting/storing `created_at` using mixed patterns:
- `datetime.utcnow()` / naive `datetime`
- direct raw string values from legacy records
- ad-hoc `.isoformat()` usage without timezone normalization

This led to:
- incorrect ordering when sorting by `created_at`
- frontend parse variability
- UTC drift / timezone ambiguity

---

## What changed

### 1) Centralized timestamp normalization utilities
Added shared utility module:
- `backend/fastapi/api/utils/timestamps.py`

Key helpers:
- `utc_now()`
- `utc_now_iso()`
- `parse_timestamp(value)`
- `normalize_utc_iso(value, fallback_now=False)`

Behavior:
- accepts `datetime` or string input
- normalizes naive values as UTC
- supports `Z` suffix and common legacy datetime formats
- always returns UTC ISO 8601 string when normalization succeeds

### 2) Enforced UTC defaults and normalization in models
Updated model defaults to use UTC-aware helpers and added guardrails:
- `backend/fastapi/api/models/__init__.py`

Highlights:
- `User.created_at` default now uses `utc_now_iso`
- several `DateTime created_at` defaults switched from `datetime.utcnow` to `utc_now`
- SQLAlchemy event hooks added for `User`:
  - `before_insert`
  - `before_update`
  - normalize `created_at` via `normalize_utc_iso(..., fallback_now=True)`

### 3) Normalized API serialization output
Ensured response payloads consistently return UTC ISO strings:
- `backend/fastapi/api/routers/auth.py`
- `backend/fastapi/api/routers/users.py`
- `backend/fastapi/api/routers/tasks.py`
- `backend/fastapi/api/services/profile_service.py`

### 4) Standardized user creation paths
Replaced direct timestamp creation with shared utility in service flows:
- `backend/fastapi/api/services/user_service.py`
- `backend/fastapi/api/services/auth_service.py`

### 5) Legacy data normalization migration
Added migration to normalize existing `users.created_at` records:
- `migrations/versions/20260301_093000_normalize_users_created_at_utc_iso.py`

Migration behavior:
- reads all `users.created_at`
- normalizes each value to UTC ISO 8601
- if value is invalid/null, falls back to current UTC ISO timestamp
- intentionally non-reversible data transformation (`downgrade` is no-op)

### 6) Migration chain fix discovered while validating
Fixed an existing Alembic revision reference typo that blocked migration graph resolution:
- `migrations/versions/f0e1d2c3b4a5_add_environment_separation_columns.py`
  - corrected `down_revision` from `20260227_160145_add_performance_indexes` to `20260227_160145`

### 7) Tests
Added/updated tests to validate normalization behavior:
- **New**: `backend/fastapi/tests/unit/test_timestamps.py`
- **Updated**: `backend/fastapi/tests/integration/test_tasks_api.py`
- **Updated**: `backend/fastapi/tests/unit/test_background_task_service.py`

---

## Acceptance criteria mapping
- [x] All new `created_at` writes are UTC-normalized
- [x] Timestamp format is normalized to ISO 8601 UTC in key API responses
- [x] Naive datetime handling is normalized through shared utility + model event hooks
- [x] Legacy `users.created_at` data normalized via migration
- [x] Frontend-facing task/user/auth payloads emit consistent parseable ISO timestamps

---

## Verification performed

### Passed
```bash
python -m pytest backend/fastapi/tests/unit/test_timestamps.py -q
# 6 passed
```

### Note on broader suite
A pre-existing unrelated model/index mismatch currently blocks full task test collection in this branch context:
- `scores` index references missing `environment` column during import/collection.

This issue is outside the timestamp-format fix itself.

---

## Risk assessment
- **Data risk**: low-medium (one-time normalization of historical `users.created_at`)
- **Runtime risk**: low (centralized formatting helper + additive normalization)
- **API compatibility**: maintained (`created_at` remains string-like ISO output, now consistent UTC)

---

## Rollback plan
1. Revert code changes in routers/services/models.
2. If needed, skip the normalization migration in downgrade workflow (data transformation is non-reversible by design).
3. Restore previous behavior by removing normalization event hooks and utility calls.

---

## Checklist
- [x] Centralized timestamp utility added
- [x] Model defaults updated to UTC-aware paths
- [x] API response normalization applied
- [x] Legacy normalization migration added
- [x] Targeted tests added/updated
- [x] Unit test verification executed
