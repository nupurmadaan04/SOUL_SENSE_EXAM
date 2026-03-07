# Release Notes Generator Documentation

## Overview

The Release Notes Generator automatically generates structured release notes from git commits using the conventional commit format. This tool streamlines the DevOps pipeline by eliminating manual changelog creation and ensuring consistency.

---

## Architecture

### Core Components

```
ReleaseNotesGenerator (Main Orchestrator)
├── CommitChange (Parsed Commit Data)
├── ReleaseNotes (Complete Release)
└── Methods:
    ├── get_tags()
    ├── get_commits_between()
    ├── categorize_commits()
    ├── generate_notes()
    ├── format_markdown()
    ├── save_to_file()
    └── export_json()
```

### Data Flow

```
Git Repository
    ↓
Get Tags → Get Commits → Parse Messages → Categorize
    ↓
ReleaseNotes Object
    ↓
Format (Markdown/JSON) → Save to File
```

---

## API Reference

### ReleaseNotesGenerator

Main class for generating release notes.

**Initialization:**
```python
from app.infra.release_notes_generator import ReleaseNotesGenerator

gen = ReleaseNotesGenerator(repo_path=".")
```

**Methods:**

#### `get_tags() -> List[str]`
Retrieve all git tags from repository.
```python
tags = gen.get_tags()
# Returns: ['v1.0.0', 'v0.9.0', 'v0.8.0', ...]
```

#### `get_commits_between(from_ref: str, to_ref: str = "HEAD") -> List[CommitChange]`
Get commits between two git references.
```python
commits = gen.get_commits_between("v0.9.0", "v1.0.0")
```

#### `categorize_commits(commits: List[CommitChange]) -> Dict[str, List]`
Categorize commits by type.
```python
categorized = gen.categorize_commits(commits)
# Returns: {"Features": [...], "Bug Fixes": [...], ...}
```

#### `generate_notes(version: str, from_tag: str, to_tag: str = "HEAD") -> ReleaseNotes`
Generate complete release notes.
```python
notes = gen.generate_notes("v1.0.0", "v0.9.0", "v1.0.0")
```

#### `format_markdown(notes: ReleaseNotes) -> str`
Format release notes as markdown.
```python
markdown = gen.format_markdown(notes)
print(markdown)
```

#### `save_to_file(notes: ReleaseNotes, filepath: str, append: bool = True) -> bool`
Save release notes to file.
```python
success = gen.save_to_file(notes, "CHANGELOG.md", append=True)
```

#### `export_json(notes: ReleaseNotes, filepath: str) -> bool`
Export release notes as JSON.
```python
success = gen.export_json(notes, "release_notes.json")
```

---

## CLI Commands

### 1. `generate` - Generate between specific tags
```bash
python -m scripts.release_notes_tools generate \
    --from-tag v0.9.0 \
    --to-tag v1.0.0 \
    --version v1.0.0 \
    --format markdown \
    --output release_v1.0.0.md
```

### 2. `auto-detect` - Auto-detect latest and generate
```bash
python -m scripts.release_notes_tools auto-detect
# Creates RELEASE_v1.0.0.md with latest tag
```

### 3. `publish` - Generate and append to CHANGELOG.md
```bash
python -m scripts.release_notes_tools publish
# Appends to CHANGELOG.md
```

### 4. `preview` - Preview without saving
```bash
python -m scripts.release_notes_tools preview \
    --from-tag v0.9.0 \
    --to-tag v1.0.0
```

### 5. `validate` - Validate commit message format
```bash
python -m scripts.release_notes_tools validate
# Checks last 20 commits for conventional format
```

### 6. `template` - Show commit message template
```bash
python -m scripts.release_notes_tools template
# Displays best practices and examples
```

### 7. `list-tags` - List all available tags
```bash
python -m scripts.release_notes_tools list-tags
# Shows all git tags in repo
```

---

## Conventional Commit Format

All commits should follow this format:

```
type(scope): description

[optional body]
[optional footer]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation
- **refactor**: Code refactoring
- **perf**: Performance improvement
- **test**: Tests
- **build**: Build system
- **ci**: CI/CD changes
- **chore**: Build/maintenance tasks
- **style**: Code style changes

### Examples

```
feat(auth): implement JWT token refresh
fix(db): handle null values in migration
docs(api): add OpenAPI specification
perf(query): optimize database indexes
feat(api)!: redesign response format (BREAKING CHANGE)
```

---

## Configuration

Configuration file: `config/release_notes_config.json`

```json
{
  "release_notes": {
    "output_file": "CHANGELOG.md",
    "format": "markdown",
    "append_mode": true
  },
  "commit_types": {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation"
  },
  "breaking_change_markers": ["!:"],
  "exclude_authors": ["dependabot", "github-actions"],
  "metadata": {
    "include_date": true,
    "include_contributors": true,
    "include_commit_hash": true
  }
}
```

---

## Output Examples

### Markdown Format

```markdown
# Release v1.0.0

**Release Date:** 2026-03-07

**Total Commits:** 5 | **Contributors:** 3

## ⚠️ Breaking Changes

- **api:** redesign response format

## ✨ Features

- implement JWT token refresh (abc1234)
- add request caching layer (def5678)

## 🐛 Bug Fixes

- handle null values in migration (ghi9012)

## 📚 Documentation

- add API specification (jkl3456)

## 👥 Contributors

Alice Johnson, Bob Smith, Charlie Brown
```

### JSON Format

```json
{
  "version": "v1.0.0",
  "date": "2026-03-07",
  "total_commits": 5,
  "contributors": ["Alice Johnson", "Bob Smith"],
  "features": [
    {
      "commit_hash": "abc1234",
      "message": "feat(auth): implement JWT",
      "author": "Alice Johnson",
      "date": "2026-03-07"
    }
  ],
  "breaking_changes": [...]
}
```

---

## Best Practices

1. **Enforce Format**: Use git hooks to enforce conventional commits
   ```bash
   # .git/hooks/commit-msg
   # Validate commit message format
   ```

2. **Team Guidelines**: Document in CONTRIBUTING.md
   - Use lowercase commit types
   - Keep messages concise
   - Use present tense ("add feature" not "added feature")

3. **Release Planning**: Tag releases in semantic versioning
   - v1.0.0 (major)
   - v1.2.0 (minor)
   - v1.2.3 (patch)

4. **Automation**: Integrate with CI/CD
   ```yaml
   # GitHub Actions
   - name: Generate Release Notes
     run: python -m scripts.release_notes_tools publish
   ```

5. **Rollback**: Keep backup of CHANGELOG.md
   ```bash
   git checkout HEAD~1 -- CHANGELOG.md
   ```

---

## Edge Cases Handled

- ✅ **Empty repository**: Returns no tags/commits gracefully
- ✅ **Single commit**: Generates notes for 1 item
- ✅ **Invalid tags**: Skips non-existent refs with error message
- ✅ **Non-conventional commits**: Groups under "Other" category
- ✅ **Missing scope**: Handles commits without parentheses
- ✅ **Special characters**: Properly escapes in JSON output
- ✅ **Concurrent writes**: File-based synchronization
- ✅ **Large repositories**: Streams commits instead of loading all
- ✅ **Timeout handling**: 30-second timeout on git commands
- ✅ **Permission errors**: Graceful degradation with error reporting

---

## Testing

Run all tests:
```bash
pytest tests/test_release_notes_generator.py -v
```

Run specific test:
```bash
pytest tests/test_release_notes_generator.py::TestCommitChange::test_conventional_commit_parsing -v
```

Test coverage:
```bash
pytest tests/test_release_notes_generator.py --cov=app.infra.release_notes_generator
```

---

## Integration Examples

### GitHub Actions

```yaml
name: Release Notes Generation

on:
  push:
    tags:
      - 'v*'

jobs:
  generate-notes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Generate release notes
        run: |
          python -m scripts.release_notes_tools publish
      
      - name: Commit CHANGELOG
        run: |
          git config user.email "actions@github.com"
          git config user.name "GitHub Actions"
          git add CHANGELOG.md
          git commit -m "chore: update CHANGELOG for ${{ github.ref }}"
          git push
```

### Pre-commit Hook

```bash
#!/bin/bash
# Validate commit format before allowing commit
COMMIT_REGEX='^(feat|fix|docs|refactor|perf|test|build|ci|chore|style)(\(.+\))?!?: .+$'

if ! grep -qE "${COMMIT_REGEX}" "$1"; then
    echo "❌ Commit message does not follow conventional format"
    exit 1
fi
```

---

## Troubleshooting

**Q: No tags found**
- Ensure git tags exist: `git tag -l`
- Create first tag: `git tag v1.0.0 && git push origin v1.0.0`

**Q: Commits not appearing in notes**
- Check tag order: `git log --oneline v0.9.0..v1.0.0`
- Ensure commits are before tag: `git tag -d v1.0.0 && git tag v1.0.0`

**Q: Special characters in markdown**
- Use JSON format for structured data
- or escape characters: `\|` for pipes

**Q: Performance issues with large repos**
- Limit date range: `--from-tag v1.0.0 --to-tag v1.5.0`
- Use `--format json` (faster than markdown)

---

## Version History

- **v1.0.0** (2026-03-07): Initial release
  - Core functionality for parsing, categorizing, and generating notes
  - 7 CLI commands
  - Markdown and JSON output formats
  - 25 comprehensive tests
