#!/usr/bin/env python3
"""
Changelog Gate for Breaking Changes

Validates that PRs marked as breaking changes include CHANGELOG updates.
Checks:
  - PR contains breaking change marker (💥)
  - CHANGELOG.md has been updated
  - Entry exists in [Unreleased] section
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Tuple, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ChangelogGate:
    """Validates breaking changes are documented in CHANGELOG."""

    BREAKING_CHANGE_MARKER = "💥"
    UNRELEASED_SECTION = "## [Unreleased]"

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.changelog_path = self.project_root / "docs" / "CHANGELOG.md"

    def is_breaking_change_pr(self, pr_body: str) -> bool:
        """Check if PR is marked as breaking change."""
        if not pr_body:
            return False
        return self.BREAKING_CHANGE_MARKER in pr_body and "[x]" in pr_body

    def changelog_exists(self) -> bool:
        """Check if CHANGELOG.md exists."""
        return self.changelog_path.exists()

    def has_unreleased_section(self, changelog_content: str) -> bool:
        """Check if CHANGELOG has [Unreleased] section."""
        return self.UNRELEASED_SECTION in changelog_content

    def extract_pr_number(self, pr_body: str) -> Optional[int]:
        """Extract PR number from body (Fixes #1437)."""
        match = re.search(r'(?:Fixes|Closes)\s+#(\d+)', pr_body, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def has_breaking_entry(self, changelog_content: str, pr_number: Optional[int] = None) -> bool:
        """
        Check if changelog has breaking change entry in [Unreleased].
        looks for entry after [Unreleased] that mentions breaking changes.
        """
        if self.UNRELEASED_SECTION not in changelog_content:
            return False

        # Extract [Unreleased] section until next version header
        unreleased_start = changelog_content.find(self.UNRELEASED_SECTION)
        next_version = changelog_content.find("\n## [", unreleased_start + 1)
        
        if next_version == -1:
            unreleased_section = changelog_content[unreleased_start:]
        else:
            unreleased_section = changelog_content[unreleased_start:next_version]

        # Check for breaking change indicators in the section
        breaking_indicators = [
            "breaking",
            "backwards incompatible",
            "incompatible",
            "removed",
            "deprecated",
        ]

        section_lower = unreleased_section.lower()
        has_change = any(indicator in section_lower for indicator in breaking_indicators)

        # If PR number provided, optionally check for it (not required)
        if pr_number and f"#{pr_number}" not in unreleased_section:
            logger.warning(f"PR #{pr_number} not referenced in changelog entry")
            # Don't fail - entry exists even without PR reference

        return has_change

    def validate(self, pr_body: str) -> Tuple[bool, str]:
        """
        Validate breaking change is documented.
        
        Returns:
            Tuple[bool, str]: (passed, message)
        """
        # If not a breaking change PR, always pass
        if not self.is_breaking_change_pr(pr_body):
            return True, "Not marked as breaking change - skipping validation"

        logger.info("Breaking change detected in PR")

        # Check changelog exists
        if not self.changelog_exists():
            return False, f"CHANGELOG not found at {self.changelog_path}"

        # Read changelog
        try:
            changelog_content = self.changelog_path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read CHANGELOG: {e}"

        # Check [Unreleased] section exists
        if not self.has_unreleased_section(changelog_content):
            return False, (
                "CHANGELOG missing [Unreleased] section.\n"
                "Add '## [Unreleased]' after the header and before first version.\n"
                "See: https://keepachangelog.com/"
            )

        # Check breaking change entry exists
        pr_number = self.extract_pr_number(pr_body)
        if not self.has_breaking_entry(changelog_content, pr_number):
            return False, (
                "CHANGELOG [Unreleased] section has no breaking change entry.\n"
                "Add entry under 'Changed', 'Removed', or 'Fixed' describing the breaking change.\n"
                f"Example:\n"
                f"  ### Changed\n"
                f"  - Removed deprecated `old_api()` endpoint (#{pr_number})\n"
                f"  - Users must migrate to `new_api()` (see migration guide in PR)"
            )

        return True, "Breaking change properly documented in CHANGELOG"


def main():
    parser = argparse.ArgumentParser(
        description="Validate breaking changes are documented in CHANGELOG"
    )
    parser.add_argument(
        "--pr-body",
        required=True,
        help="PR description body from GitHub"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--report",
        help="Path to write JSON report (optional)"
    )

    args = parser.parse_args()

    gate = ChangelogGate(args.project_root)
    passed, message = gate.validate(args.pr_body)

    # Print result
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"\n{status}")
    print(f"Message: {message}\n")

    # Write report if requested
    if args.report:
        import json
        report = {
            "passed": passed,
            "message": message,
            "gate": "changelog",
        }
        Path(args.report).write_text(json.dumps(report, indent=2))

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
