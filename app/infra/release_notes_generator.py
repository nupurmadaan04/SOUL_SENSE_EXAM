"""
Centralized Release Notes Auto-Generator
Parses git commits and generates structured release notes
"""

import json
import subprocess
import re
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class CommitChange:
    """Represents a parsed git commit"""
    commit_hash: str
    message: str
    scope: Optional[str] = None
    change_type: str = ""
    description: str = ""
    author: str = ""
    date: str = ""
    breaking: bool = False

    def __post_init__(self):
        """Parse conventional commit format"""
        pattern = r'^(\w+)(?:\(([^)]*)\))?!?:\s*(.+)$'
        match = re.match(pattern, self.message)
        if match:
            self.change_type = match.group(1)
            self.scope = match.group(2)
            self.description = match.group(3)
            self.breaking = "!" in self.message
        else:
            # If not conventional format, extract first word as type
            parts = self.message.split(":")
            if parts:
                self.change_type = parts[0].split()[0] if parts[0] else "other"
                self.description = self.message


@dataclass
class ReleaseNotes:
    """Represents complete release notes"""
    version: str
    date: str
    summary: str = ""
    features: List[CommitChange] = field(default_factory=list)
    fixes: List[CommitChange] = field(default_factory=list)
    docs: List[CommitChange] = field(default_factory=list)
    breaking_changes: List[CommitChange] = field(default_factory=list)
    contributors: List[str] = field(default_factory=list)
    total_commits: int = 0


class ReleaseNotesGenerator:
    """Generate release notes from git commits"""

    CONFIG_TYPES = {
        "feat": "Features",
        "fix": "Bug Fixes",
        "docs": "Documentation",
        "refactor": "Refactoring",
        "perf": "Performance",
        "test": "Testing"
    }

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.commits: List[CommitChange] = []

    def get_tags(self) -> List[str]:
        """Get all git tags sorted by version"""
        try:
            result = subprocess.run(
                ["git", "tag", "-l"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            tags = sorted(result.stdout.strip().split('\n'), reverse=True)
            return [t for t in tags if t]
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []

    def get_commits_between(self, from_ref: str, to_ref: str = "HEAD") -> List[CommitChange]:
        """Get commits between two refs"""
        try:
            cmd = [
                "git",
                "log",
                f"{from_ref}..{to_ref}",
                "--pretty=format:%H|%s|%an|%ai"
            ]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 4:
                    commit = CommitChange(
                        commit_hash=parts[0][:7],
                        message=parts[1],
                        author=parts[2],
                        date=parts[3][:10]
                    )
                    commits.append(commit)
            
            return commits
        except Exception as e:
            print(f"Error getting commits: {e}")
            return []

    def categorize_commits(self, commits: List[CommitChange]) -> Dict[str, List[CommitChange]]:
        """Categorize commits by type"""
        categorized = {
            "Features": [],
            "Bug Fixes": [],
            "Documentation": [],
            "Refactoring": [],
            "Performance": [],
            "Testing": [],
            "Other": []
        }

        for commit in commits:
            commit_type = commit.change_type.lower()
            category = self.CONFIG_TYPES.get(commit_type, "Other")
            categorized[category].append(commit)

        return {k: v for k, v in categorized.items() if v}

    def generate_notes(self, version: str, from_tag: str, to_tag: str = "HEAD") -> ReleaseNotes:
        """Generate release notes between two versions"""
        commits = self.get_commits_between(from_tag, to_tag)
        categorized = self.categorize_commits(commits)

        breaking_changes = [c for c in commits if c.breaking]
        contributors = sorted(set(c.author for c in commits if c.author))

        notes = ReleaseNotes(
            version=version,
            date=datetime.now().strftime("%Y-%m-%d"),
            features=categorized.get("Features", []),
            fixes=categorized.get("Bug Fixes", []),
            docs=categorized.get("Documentation", []),
            breaking_changes=breaking_changes,
            contributors=contributors,
            total_commits=len(commits)
        )

        return notes

    def format_markdown(self, notes: ReleaseNotes) -> str:
        """Format release notes as markdown"""
        md = f"# Release {notes.version}\n\n"
        md += f"**Release Date:** {notes.date}\n\n"
        md += f"**Total Commits:** {notes.total_commits} | **Contributors:** {len(notes.contributors)}\n\n"

        if notes.breaking_changes:
            md += "## ⚠️ Breaking Changes\n\n"
            for commit in notes.breaking_changes:
                md += f"- **{commit.scope or 'core'}:** {commit.description}\n"
            md += "\n"

        if notes.features:
            md += "## ✨ Features\n\n"
            for commit in notes.features:
                md += f"- {commit.description} ({commit.commit_hash})\n"
            md += "\n"

        if notes.fixes:
            md += "## 🐛 Bug Fixes\n\n"
            for commit in notes.fixes:
                md += f"- {commit.description} ({commit.commit_hash})\n"
            md += "\n"

        if notes.docs:
            md += "## 📚 Documentation\n\n"
            for commit in notes.docs:
                md += f"- {commit.description}\n"
            md += "\n"

        if notes.contributors:
            md += "## 👥 Contributors\n\n"
            md += ", ".join(notes.contributors) + "\n"

        return md

    def save_to_file(self, notes: ReleaseNotes, filepath: str = "CHANGELOG.md", append: bool = True) -> bool:
        """Save release notes to file"""
        try:
            filepath = self.repo_path / filepath
            markdown = self.format_markdown(notes)

            if append and filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing = f.read()
                markdown = markdown + "\n---\n\n" + existing
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            return False

    def export_json(self, notes: ReleaseNotes, filepath: str = "release_notes.json") -> bool:
        """Export release notes as JSON"""
        try:
            filepath = self.repo_path / filepath
            data = {
                "version": notes.version,
                "date": notes.date,
                "total_commits": notes.total_commits,
                "contributors": notes.contributors,
                "features": [asdict(c) for c in notes.features],
                "fixes": [asdict(c) for c in notes.fixes],
                "documentation": [asdict(c) for c in notes.docs],
                "breaking_changes": [asdict(c) for c in notes.breaking_changes]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
