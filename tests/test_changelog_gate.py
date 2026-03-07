"""
Unit tests for Changelog Gate

Tests for breaking change detection and CHANGELOG validation.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from scripts.changelog_gate import ChangelogGate


@pytest.fixture
def temp_project():
    """Create temporary project structure for testing."""
    temp_dir = tempfile.mkdtemp()
    docs_dir = Path(temp_dir) / "docs"
    docs_dir.mkdir()
    
    yield temp_dir
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def changelog_gate(temp_project):
    """Create ChangelogGate instance with temp project."""
    return ChangelogGate(temp_project)


@pytest.fixture
def valid_changelog():
    """Valid CHANGELOG with [Unreleased] section."""
    return """# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- Removed deprecated `/api/v1/users` endpoint (#1437)
  - Users must migrate to `/api/v2/users`

### Added
- New `/api/v2/users` endpoint with improved schema

## [0.1.0] - 2026-01-01

### Added
- Initial release
"""


class TestBreakingChangeDetection:
    """Test breaking change marker detection."""

    def test_breaking_change_detected_when_marked(self, changelog_gate):
        """Should detect breaking change when PR has 💥 and [x]."""
        pr_body = "## Description\n- [x] 💥 **Breaking Change**: Breaking the API"
        assert changelog_gate.is_breaking_change_pr(pr_body) is True

    def test_breaking_change_not_detected_without_checkbox(self, changelog_gate):
        """Should not detect breaking change if checkbox not checked."""
        pr_body = "## Description\n- [ ] 💥 **Breaking Change**: Breaking the API"
        assert changelog_gate.is_breaking_change_pr(pr_body) is False

    def test_breaking_change_not_detected_without_marker(self, changelog_gate):
        """Should not detect breaking change without emoji."""
        pr_body = "## Description\n- [x] **New Feature**: Adding new feature"
        assert changelog_gate.is_breaking_change_pr(pr_body) is False

    def test_empty_pr_body(self, changelog_gate):
        """Should handle empty PR body gracefully."""
        assert changelog_gate.is_breaking_change_pr("") is False
        assert changelog_gate.is_breaking_change_pr(None) is False


class TestChangelogValidation:
    """Test CHANGELOG file validation."""

    def test_changelog_exists(self, temp_project, changelog_gate, valid_changelog):
        """Should detect when CHANGELOG exists."""
        changelog_path = Path(temp_project) / "docs" / "CHANGELOG.md"
        changelog_path.write_text(valid_changelog)
        assert changelog_gate.changelog_exists() is True

    def test_changelog_missing(self, changelog_gate):
        """Should detect when CHANGELOG is missing."""
        assert changelog_gate.changelog_exists() is False

    def test_has_unreleased_section(self, changelog_gate, valid_changelog):
        """Should detect [Unreleased] section."""
        assert changelog_gate.has_unreleased_section(valid_changelog) is True

    def test_missing_unreleased_section(self, changelog_gate):
        """Should detect missing [Unreleased] section."""
        changelog = "# Changelog\n\n## [0.1.0] - 2026-01-01"
        assert changelog_gate.has_unreleased_section(changelog) is False


class TestBreakingChangeEntry:
    """Test breaking change entry detection."""

    def test_breaking_entry_found_with_removed(self, changelog_gate):
        """Should find breaking entry marked as 'Removed'."""
        changelog = """
## [Unreleased]
### Removed
- Deprecated the old function (#1437)
"""
        assert changelog_gate.has_breaking_entry(changelog, 1437) is True

    def test_breaking_entry_found_with_changed(self, changelog_gate):
        """Should find breaking entry marked as 'Changed'."""
        changelog = """
## [Unreleased]
### Changed
- Breaking: API endpoint signature changed (#1437)
"""
        assert changelog_gate.has_breaking_entry(changelog, 1437) is True

    def test_breaking_entry_not_found(self, changelog_gate):
        """Should not find breaking entry if missing."""
        changelog = """
## [Unreleased]
### Added
- New feature
"""
        assert changelog_gate.has_breaking_entry(changelog) is False

    def test_pr_number_referenced(self, changelog_gate):
        """Should find PR number reference in entry."""
        changelog = """
## [Unreleased]
### Removed
- Old API removed (#1437)
"""
        # Should pass without error even if PR num check gives warning
        result = changelog_gate.has_breaking_entry(changelog, 1437)
        assert result is True


class TestPRNumberExtraction:
    """Test PR number extraction from PR body."""

    def test_extract_pr_number_from_fixes(self, changelog_gate):
        """Should extract PR number from 'Fixes' syntax."""
        pr_body = "Fixes #1437\n\nDescription here"
        assert changelog_gate.extract_pr_number(pr_body) == 1437

    def test_extract_pr_number_from_closes(self, changelog_gate):
        """Should extract PR number from 'Closes' syntax."""
        pr_body = "Closes #999\n\nDescription here"
        assert changelog_gate.extract_pr_number(pr_body) == 999

    def test_extract_pr_number_case_insensitive(self, changelog_gate):
        """Should handle case-insensitive 'Fixes' and 'Closes'."""
        pr_body1 = "fixes #1437"
        pr_body2 = "CLOSES #1437"
        assert changelog_gate.extract_pr_number(pr_body1) == 1437
        assert changelog_gate.extract_pr_number(pr_body2) == 1437

    def test_extract_pr_number_not_found(self, changelog_gate):
        """Should return None if PR number not found."""
        pr_body = "Description without issue reference"
        assert changelog_gate.extract_pr_number(pr_body) is None


class TestFullValidation:
    """Test complete validation workflow."""

    def test_validation_passes_for_non_breaking_pr(self, changelog_gate):
        """Should pass validation if PR is not marked as breaking."""
        pr_body = "## Description\nAdding new feature"
        passed, message = changelog_gate.validate(pr_body)
        assert passed is True
        assert "Not marked as breaking change" in message

    def test_validation_fails_if_changelog_missing(self, changelog_gate):
        """Should fail if CHANGELOG doesn't exist."""
        pr_body = "## Description\n- [x] 💥 **Breaking Change**: Breaking API"
        passed, message = changelog_gate.validate(pr_body)
        assert passed is False
        assert "CHANGELOG not found" in message

    def test_validation_fails_if_no_unreleased_section(self, temp_project, changelog_gate):
        """Should fail if [Unreleased] section missing."""
        changelog_path = Path(temp_project) / "docs" / "CHANGELOG.md"
        changelog_path.write_text("# Changelog\n\n## [0.1.0]")
        
        pr_body = "## Description\n- [x] 💥 **Breaking Change**: Breaking API"
        passed, message = changelog_gate.validate(pr_body)
        assert passed is False
        assert "[Unreleased]" in message

    def test_validation_fails_if_no_breaking_entry(self, temp_project, changelog_gate):
        """Should fail if breaking change entry missing from [Unreleased]."""
        changelog_path = Path(temp_project) / "docs" / "CHANGELOG.md"
        changelog_path.write_text(
            "# Changelog\n\n## [Unreleased]\n### Added\n- New feature\n\n## [0.1.0]"
        )
        
        pr_body = "## Description\n- [x] 💥 **Breaking Change**: Breaking API"
        passed, message = changelog_gate.validate(pr_body)
        assert passed is False
        assert "breaking change entry" in message

    def test_validation_passes_for_breaking_change_with_entry(
        self, temp_project, changelog_gate, valid_changelog
    ):
        """Should pass if breaking change properly documented."""
        changelog_path = Path(temp_project) / "docs" / "CHANGELOG.md"
        changelog_path.write_text(valid_changelog)
        
        pr_body = "Fixes #1437\n\n- [x] 💥 **Breaking Change**: Removing old API"
        passed, message = changelog_gate.validate(pr_body)
        assert passed is True
        assert "properly documented" in message


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_changelog_with_multiple_versions(self, changelog_gate):
        """Should find breaking entry in correct [Unreleased] section."""
        changelog = """
## [Unreleased]
### Changed
- Breaking change (#1437)

## [0.2.0] - 2026-02-01
### Added
- Old feature

## [0.1.0] - 2026-01-01
### Added
- Initial release
"""
        assert changelog_gate.has_breaking_entry(changelog, 1437) is True

    def test_breaking_keywords_case_insensitive(self, changelog_gate):
        """Should detect breaking keywords regardless of case."""
        changelog = """
## [Unreleased]
### Changed
- BREAKING CHANGE: API removed
"""
        assert changelog_gate.has_breaking_entry(changelog) is True

    def test_deprecated_keyword_recognized(self, changelog_gate):
        """Should recognize 'deprecated' as breaking change indicator."""
        changelog = """
## [Unreleased]
### Changed
- Deprecated old_function() in favor of new_function()
"""
        assert changelog_gate.has_breaking_entry(changelog) is True
