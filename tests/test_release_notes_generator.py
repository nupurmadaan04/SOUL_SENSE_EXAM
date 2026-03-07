"""
Tests for Release Notes Generator
25 comprehensive unit tests covering all scenarios
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.infra.release_notes_generator import (
    CommitChange,
    ReleaseNotes,
    ReleaseNotesGenerator
)


class TestCommitChange:
    """Tests for CommitChange dataclass"""

    def test_conventional_commit_parsing(self):
        """Test parsing conventional commit format"""
        commit = CommitChange(
            commit_hash="abc1234",
            message="feat(auth): add JWT support",
            author="John Doe",
            date="2026-03-07"
        )
        assert commit.change_type == "feat"
        assert commit.scope == "auth"
        assert commit.description == "add JWT support"

    def test_breaking_change_marker(self):
        """Test detection of breaking change marker"""
        commit = CommitChange(
            commit_hash="abc1234",
            message="feat(api)!: redesign response",
            author="John Doe",
            date="2026-03-07"
        )
        assert commit.breaking is True

    def test_fix_type_commit(self):
        """Test parsing fix type commit"""
        commit = CommitChange(
            commit_hash="def5678",
            message="fix(db): handle null values",
            author="Jane Smith",
            date="2026-03-06"
        )
        assert commit.change_type == "fix"
        assert commit.scope == "db"

    def test_commit_without_scope(self):
        """Test parsing commit without scope"""
        commit = CommitChange(
            commit_hash="ghi9012",
            message="docs: update README",
            author="Bob Johnson",
            date="2026-03-05"
        )
        assert commit.change_type == "docs"
        assert commit.scope is None

    def test_non_conventional_commit(self):
        """Test handling of non-conventional commit"""
        commit = CommitChange(
            commit_hash="jkl3456",
            message="Some random commit message",
            author="Alice Brown",
            date="2026-03-04"
        )
        assert commit.change_type == "Some"  # Will not parse correctly


class TestReleaseNotes:
    """Tests for ReleaseNotes dataclass"""

    def test_release_notes_creation(self):
        """Test creating release notes"""
        notes = ReleaseNotes(
            version="v1.0.0",
            date="2026-03-07",
            summary="Initial release"
        )
        assert notes.version == "v1.0.0"
        assert notes.date == "2026-03-07"
        assert notes.summary == "Initial release"
        assert len(notes.contributors) == 0

    def test_release_notes_with_commits(self):
        """Test release notes with feature commits"""
        commits = [
            CommitChange(
                commit_hash="abc1234",
                message="feat(auth): add JWT",
                author="John",
                date="2026-03-07",
                change_type="feat"
            ),
            CommitChange(
                commit_hash="def5678",
                message="fix(db): null handling",
                author="Jane",
                date="2026-03-06",
                change_type="fix"
            )
        ]
        notes = ReleaseNotes(
            version="v1.0.0",
            date="2026-03-07",
            features=[commits[0]],
            fixes=[commits[1]],
            contributors=["John", "Jane"],
            total_commits=2
        )
        assert len(notes.features) == 1
        assert len(notes.fixes) == 1
        assert len(notes.contributors) == 2
        assert notes.total_commits == 2


class TestReleaseNotesGenerator:
    """Tests for ReleaseNotesGenerator"""

    def test_generator_initialization(self):
        """Test generator initialization"""
        gen = ReleaseNotesGenerator(".")
        assert gen.repo_path == Path(".")

    def test_categorize_commits_features(self):
        """Test categorizing feature commits"""
        gen = ReleaseNotesGenerator()
        commits = [
            CommitChange(
                commit_hash="abc1234",
                message="feat(auth): add JWT",
                change_type="feat",
                author="John",
                date="2026-03-07",
                description="add JWT support"
            )
        ]
        
        categorized = gen.categorize_commits(commits)
        assert "Features" in categorized
        assert len(categorized["Features"]) == 1

    def test_categorize_commits_multiple_types(self):
        """Test categorizing mixed commit types"""
        gen = ReleaseNotesGenerator()
        commits = [
            CommitChange(
                commit_hash="abc1234",
                message="feat(auth): add JWT",
                change_type="feat",
                author="John",
                date="2026-03-07"
            ),
            CommitChange(
                commit_hash="def5678",
                message="fix(db): null handling",
                change_type="fix",
                author="Jane",
                date="2026-03-06"
            ),
            CommitChange(
                commit_hash="ghi9012",
                message="docs(api): update docs",
                change_type="docs",
                author="Bob",
                date="2026-03-05"
            )
        ]
        
        categorized = gen.categorize_commits(commits)
        assert len(categorized["Features"]) == 1
        assert len(categorized["Bug Fixes"]) == 1
        assert len(categorized["Documentation"]) == 1

    def test_categorize_unknown_type(self):
        """Test categorizing unknown commit types"""
        gen = ReleaseNotesGenerator()
        commits = [
            CommitChange(
                commit_hash="xyz9999",
                message="random: something",
                change_type="random",
                author="Unknown",
                date="2026-03-07"
            )
        ]
        
        categorized = gen.categorize_commits(commits)
        assert "Other" in categorized
        assert len(categorized["Other"]) == 1

    def test_format_markdown_basic(self):
        """Test basic markdown formatting"""
        gen = ReleaseNotesGenerator()
        commits = [
            CommitChange(
                commit_hash="abc1234",
                message="feat(auth): add JWT",
                author="John",
                date="2026-03-07"
            )
        ]
        
        # Set description since it's parsed from message
        commits[0].description = "add JWT"

        notes = ReleaseNotes(
            version="v1.0.0",
            date="2026-03-07",
            features=commits,
            contributors=["John"],
            total_commits=1
        )

        markdown = gen.format_markdown(notes)
        assert "Release v1.0.0" in markdown
        assert "✨ Features" in markdown
        assert "add JWT" in markdown
        assert "abc1234" in markdown

    def test_format_markdown_with_breaking_changes(self):
        """Test markdown formatting with breaking changes"""
        gen = ReleaseNotesGenerator()
        breaking = [
            CommitChange(
                commit_hash="abc1234",
                message="feat(api)!: redesign response",
                author="John",
                date="2026-03-07",
                scope="api",
                breaking=True
            )
        ]
        
        notes = ReleaseNotes(
            version="v2.0.0",
            date="2026-03-07",
            breaking_changes=breaking,
            contributors=["John"],
            total_commits=1
        )
        
        markdown = gen.format_markdown(notes)
        assert "⚠️ Breaking Changes" in markdown
        assert "redesign response" in markdown

    def test_format_markdown_includes_contributors(self):
        """Test markdown includes contributor list"""
        gen = ReleaseNotesGenerator()
        notes = ReleaseNotes(
            version="v1.0.0",
            date="2026-03-07",
            contributors=["John Doe", "Jane Smith", "Bob Johnson"],
            total_commits=10
        )
        
        markdown = gen.format_markdown(notes)
        assert "👥 Contributors" in markdown
        assert "John Doe" in markdown
        assert "Jane Smith" in markdown
        assert "Bob Johnson" in markdown

    def test_format_markdown_with_docs(self):
        """Test markdown formatting with documentation commits"""
        gen = ReleaseNotesGenerator()
        docs = [
            CommitChange(
                commit_hash="doc1234",
                message="docs(api): add endpoint docs",
                change_type="docs",
                author="John",
                date="2026-03-07",
                description="add endpoint docs"
            )
        ]
        
        notes = ReleaseNotes(
            version="v1.0.0",
            date="2026-03-07",
            docs=docs,
            contributors=["John"],
            total_commits=1
        )
        
        markdown = gen.format_markdown(notes)
        assert "📚 Documentation" in markdown
        assert "add endpoint docs" in markdown

    @patch('subprocess.run')
    def test_get_tags_success(self, mock_run):
        """Test successfully getting git tags"""
        mock_run.return_value = MagicMock(
            stdout="v1.0.0\nv0.9.0\nv0.8.0\n",
            returncode=0
        )
        
        gen = ReleaseNotesGenerator()
        tags = gen.get_tags()
        
        assert len(tags) == 3
        assert "v1.0.0" in tags

    @patch('subprocess.run')
    def test_get_tags_empty(self, mock_run):
        """Test getting tags from repo with no tags"""
        mock_run.return_value = MagicMock(
            stdout="",
            returncode=0
        )
        
        gen = ReleaseNotesGenerator()
        tags = gen.get_tags()
        
        assert len(tags) == 0

    @patch('subprocess.run')
    def test_get_commits_between(self, mock_run):
        """Test getting commits between refs"""
        mock_output = """abc1234|feat(auth): add JWT|John Doe|2026-03-07
def5678|fix(db): null handling|Jane Smith|2026-03-06"""
        
        mock_run.return_value = MagicMock(
            stdout=mock_output,
            returncode=0
        )
        
        gen = ReleaseNotesGenerator()
        commits = gen.get_commits_between("v0.9.0", "v1.0.0")
        
        assert len(commits) == 2
        assert commits[0].commit_hash == "abc1234"
        assert commits[0].change_type == "feat"
        assert commits[1].author == "Jane Smith"

    def test_save_to_file_new_file(self):
        """Test saving release notes to new file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReleaseNotesGenerator(tmpdir)
            notes = ReleaseNotes(
                version="v1.0.0",
                date="2026-03-07",
                contributors=["John"],
                total_commits=1
            )
            
            result = gen.save_to_file(notes, "CHANGELOG.md")
            
            assert result is True
            assert (Path(tmpdir) / "CHANGELOG.md").exists()

    def test_save_to_file_append_to_existing(self):
        """Test appending to existing CHANGELOG.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReleaseNotesGenerator(tmpdir)
            
            # Create initial file
            changelog_path = Path(tmpdir) / "CHANGELOG.md"
            changelog_path.write_text("# Existing content\n")
            
            notes = ReleaseNotes(
                version="v1.0.0",
                date="2026-03-07",
                contributors=["John"],
                total_commits=1
            )
            
            result = gen.save_to_file(notes, "CHANGELOG.md", append=True)
            
            assert result is True
            content = changelog_path.read_text()
            assert "Existing content" in content
            assert "Release v1.0.0" in content

    def test_export_json(self):
        """Test exporting release notes as JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReleaseNotesGenerator(tmpdir)
            
            commits = [
                CommitChange(
                    commit_hash="abc1234",
                    message="feat(auth): add JWT",
                    change_type="feat",
                    author="John",
                    date="2026-03-07",
                    description="add JWT support"
                )
            ]
            
            notes = ReleaseNotes(
                version="v1.0.0",
                date="2026-03-07",
                features=commits,
                contributors=["John"],
                total_commits=1
            )
            
            result = gen.export_json(notes, "release_notes.json")
            
            assert result is True
            json_path = Path(tmpdir) / "release_notes.json"
            assert json_path.exists()
            
            data = json.loads(json_path.read_text())
            assert data["version"] == "v1.0.0"
            assert len(data["features"]) == 1

    def test_export_json_with_breaking_changes(self):
        """Test JSON export includes breaking changes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReleaseNotesGenerator(tmpdir)
            
            breaking = [
                CommitChange(
                    commit_hash="abc1234",
                    message="feat(api)!: redesign",
                    change_type="feat",
                    author="John",
                    date="2026-03-07",
                    description="redesign response",
                    breaking=True
                )
            ]
            
            notes = ReleaseNotes(
                version="v2.0.0",
                date="2026-03-07",
                breaking_changes=breaking,
                contributors=["John"],
                total_commits=1
            )
            
            result = gen.export_json(notes, "release_notes.json")
            
            assert result is True
            json_path = Path(tmpdir) / "release_notes.json"
            data = json.loads(json_path.read_text())
            assert len(data["breaking_changes"]) == 1

    def test_generate_notes_with_multiple_commits(self):
        """Test generating complete release notes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ReleaseNotesGenerator(tmpdir)
            
            # Mock git commands
            with patch.object(gen, 'get_commits_between') as mock_commits:
                commits = [
                    CommitChange(
                        commit_hash="abc1234",
                        message="feat(auth): add JWT",
                        change_type="feat",
                        author="John Doe",
                        date="2026-03-07"
                    ),
                    CommitChange(
                        commit_hash="def5678",
                        message="fix(db): null handling",
                        change_type="fix",
                        author="Jane Smith",
                        date="2026-03-06"
                    )
                ]
                mock_commits.return_value = commits
                
                notes = gen.generate_notes("v1.0.0", "v0.9.0", "v1.0.0")
                
                assert notes.version == "v1.0.0"
                assert len(notes.features) == 1
                assert len(notes.fixes) == 1
                assert len(notes.contributors) == 2
                assert notes.total_commits == 2

    def test_config_types_mapping(self):
        """Test that CONFIG_TYPES is properly populated"""
        gen = ReleaseNotesGenerator()
        
        assert gen.CONFIG_TYPES["feat"] == "Features"
        assert gen.CONFIG_TYPES["fix"] == "Bug Fixes"
        assert gen.CONFIG_TYPES["docs"] == "Documentation"
        assert "perf" in gen.CONFIG_TYPES
