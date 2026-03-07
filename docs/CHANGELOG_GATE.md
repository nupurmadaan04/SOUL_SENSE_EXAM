# Changelog Gate for Breaking Changes

## Overview

The **Changelog Gate** is an automated CI/CD check that ensures PRs marked as breaking changes include proper CHANGELOG updates. This prevents breaking changes from being merged without documentation, reducing regression risk and improving pipeline quality.

## When It Applies

The gate **only activates** when your PR is marked as:
```
- [x] 💥 **Breaking Change**: A fix or feature that would cause existing functionality to not work as expected.
```

✅ **Non-breaking PRs bypass this check entirely.**

## How It Works

The gate validates:
1. ✅ CHANGELOG.md exists
2. ✅ `## [Unreleased]` section exists
3. ✅ Entry describing breaking change is present
4. ✅ Entry uses at least one indicator: "breaking", "removed", "deprecated", "incompatible"

## Fixing Failures

### Error: "CHANGELOG not found"
**Add the file**: Create `docs/CHANGELOG.md` if it doesn't exist.

### Error: "CHANGELOG missing [Unreleased]"
**Add the section** after the header:
```markdown
# Changelog

All notable changes...

## [Unreleased]

### Added
### Changed
### Removed

## [0.1.0] - 2026-01-01
```

### Error: "CHANGELOG [Unreleased] section has no breaking change entry"
**Add a breaking change entry** under `Changed`, `Removed`, or `Fixed`:

```markdown
## [Unreleased]

### Removed
- Removed deprecated `/api/v1/users` endpoint (#1437)
  Users must migrate to `/api/v2/users`

### Changed
- Modified `/database/schema` to use new partitioning (#1437)
  Requires running migration: `python scripts/migrate_db.py`
```

## Good Examples ✅

```markdown
## [Unreleased]

### Removed
- Removed `User.legacy_field` column (#1437)
  Migration required: run `python migrate.py`

### Changed
- API response format changed from JSON-RPC to REST (#1437)
  Clients must update parsers accordingly
```

## Common Issues

| Issue | Solution |
|-------|----------|
| "Entry exists but still fails" | Ensure entry is **above** the next version header (`## [0.x.x]`) |
| "Multiple breaking changes" | Add entry for each change under relevant section |
| "PR number not referenced" | Optional - entry valid without PR number |
| "Test fails locally" | Run: `pytest tests/test_changelog_gate.py -v` |

## Testing Locally

```bash
# Run unit tests
pytest tests/test_changelog_gate.py -v

# Test the gate manually
python scripts/changelog_gate.py \
  --pr-body "Fixes #1437\n- [x] 💥 Breaking Change" \
  --project-root .
```

## See Also

- [CHANGELOG.md](../docs/CHANGELOG.md) - The actual changelog
- [Keep a Changelog Format](https://keepachangelog.com/) - Full specification
- [Semantic Versioning](https://semver.org/) - Version numbering
- [PR Template](.github/PULL_REQUEST_TEMPLATE.md) - Breaking change checkbox
