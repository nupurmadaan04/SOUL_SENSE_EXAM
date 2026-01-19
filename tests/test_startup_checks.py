"""
Test suite for startup integrity checks.
Tests database schema validation, required files check, and config integrity.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

from app.startup_checks import (
    CheckStatus,
    IntegrityCheckResult,
    check_database_schema,
    check_required_files,
    check_config_integrity,
    run_all_checks,
    get_check_summary,
    REQUIRED_FILES,
    REQUIRED_TABLES,
)
from app.exceptions import IntegrityError


class TestIntegrityCheckResult:
    """Tests for the IntegrityCheckResult dataclass."""
    
    def test_create_passed_result(self):
        result = IntegrityCheckResult(
            name="test_check",
            status=CheckStatus.PASSED,
            message="All good"
        )
        assert result.name == "test_check"
        assert result.status == CheckStatus.PASSED
        assert result.message == "All good"
        assert result.recovery_action is None
        assert result.details == {}
    
    def test_create_failed_result_with_details(self):
        result = IntegrityCheckResult(
            name="db_check",
            status=CheckStatus.FAILED,
            message="Tables missing",
            details={"missing_tables": ["users", "scores"]}
        )
        assert result.status == CheckStatus.FAILED
        assert "users" in result.details["missing_tables"]
    
    def test_create_warning_result_with_recovery(self):
        result = IntegrityCheckResult(
            name="config_check",
            status=CheckStatus.WARNING,
            message="Config was missing",
            recovery_action="Created default config"
        )
        assert result.status == CheckStatus.WARNING
        assert result.recovery_action == "Created default config"


class TestCheckDatabaseSchema:
    """Tests for database schema validation."""
    
    def test_check_database_schema_success(self, temp_db):
        """Test that schema check passes with valid database."""
        result = check_database_schema()
        # With temp_db fixture, tables should exist
        assert result.status in [CheckStatus.PASSED, CheckStatus.WARNING]
    
    def test_check_database_schema_missing_db(self, monkeypatch, tmp_path):
        """Test handling of missing database file."""
        # Point to non-existent DB
        fake_db_path = str(tmp_path / "nonexistent.db")
        monkeypatch.setattr("app.startup_checks.DB_PATH", fake_db_path)
        
        # Mock the check_db_state from app.db where it's actually defined
        with patch("app.db.check_db_state") as mock_check:
            mock_check.return_value = True
            result = check_database_schema()
            # Should attempt recovery
            assert result.status in [CheckStatus.WARNING, CheckStatus.FAILED]
    
    def test_check_database_schema_missing_tables(self, temp_db, monkeypatch):
        """Test detection of missing tables."""
        # Mock inspector to return empty table list
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = []
        
        # Patch inspect at the point of use in startup_checks module
        with patch("app.startup_checks.inspect", return_value=mock_inspector), \
             patch("app.startup_checks.os.path.exists", return_value=True):
            
            result = check_database_schema()
            
            # Should warn about missing tables (after attempting recovery)
            # The function will try to recover, but with mocked inspect still showing no tables
            assert result.status in [CheckStatus.WARNING, CheckStatus.FAILED]


class TestCheckRequiredFiles:
    """Tests for required files validation."""
    
    def test_check_required_files_all_present(self, monkeypatch, tmp_path):
        """Test that check passes when all files exist."""
        # Create all required directories
        monkeypatch.setattr("app.startup_checks.BASE_DIR", str(tmp_path))
        
        for file_info in REQUIRED_FILES:
            path = tmp_path / file_info["path"]
            if file_info["type"] == "directory":
                path.mkdir(exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
        
        result = check_required_files()
        assert result.status == CheckStatus.PASSED
    
    def test_check_required_files_auto_create_directory(self, monkeypatch, tmp_path):
        """Test auto-creation of missing directories."""
        monkeypatch.setattr("app.startup_checks.BASE_DIR", str(tmp_path))
        
        # Don't create directories - let check_required_files create them
        result = check_required_files()
        
        # Should succeed with warnings about created directories
        assert result.status in [CheckStatus.PASSED, CheckStatus.WARNING]
        
        # Verify directories were created
        for file_info in REQUIRED_FILES:
            if file_info.get("auto_create") and file_info["type"] == "directory":
                assert (tmp_path / file_info["path"]).exists()


class TestCheckConfigIntegrity:
    """Tests for configuration file validation."""
    
    def test_check_config_integrity_valid(self, monkeypatch, tmp_path):
        """Test that valid config passes check."""
        config_path = tmp_path / "config.json"
        valid_config = {
            "database": {"filename": "test.db", "path": "db"},
            "ui": {"theme": "dark"},
            "features": {"enable_journal": True}
        }
        
        with open(config_path, 'w') as f:
            json.dump(valid_config, f)
        
        monkeypatch.setattr("app.startup_checks.CONFIG_PATH", str(config_path))
        
        result = check_config_integrity()
        assert result.status == CheckStatus.PASSED
    
    def test_check_config_integrity_missing_creates_default(self, monkeypatch, tmp_path):
        """Test that missing config is created with defaults."""
        config_path = tmp_path / "config.json"
        
        monkeypatch.setattr("app.startup_checks.CONFIG_PATH", str(config_path))
        
        result = check_config_integrity()
        
        # Should create default config and return warning
        assert result.status == CheckStatus.WARNING
        assert config_path.exists()
        
        # Verify default config was written
        with open(config_path) as f:
            config = json.load(f)
        assert "database" in config
    
    def test_check_config_integrity_corrupt_recovers(self, monkeypatch, tmp_path):
        """Test recovery from corrupt config file."""
        config_path = tmp_path / "config.json"
        
        # Write invalid JSON
        with open(config_path, 'w') as f:
            f.write("{ invalid json }")
        
        monkeypatch.setattr("app.startup_checks.CONFIG_PATH", str(config_path))
        
        result = check_config_integrity()
        
        # Should backup corrupt file and create new default
        assert result.status == CheckStatus.WARNING
        assert "corrupt" in result.message.lower() or "restored" in result.message.lower()
        
        # Verify backup was created
        backup_path = tmp_path / "config.json.corrupt.bak"
        assert backup_path.exists()
    
    def test_check_config_integrity_missing_sections(self, monkeypatch, tmp_path):
        """Test detection of missing config sections."""
        config_path = tmp_path / "config.json"
        
        # Config with missing sections
        partial_config = {"database": {"filename": "test.db"}}
        
        with open(config_path, 'w') as f:
            json.dump(partial_config, f)
        
        monkeypatch.setattr("app.startup_checks.CONFIG_PATH", str(config_path))
        
        result = check_config_integrity()
        
        # Should warn about missing sections
        assert result.status == CheckStatus.WARNING
        assert "missing" in result.message.lower()


class TestRunAllChecks:
    """Tests for the main run_all_checks function."""
    
    def test_run_all_checks_all_pass(self, temp_db, monkeypatch, tmp_path):
        """Test that all checks pass with valid setup."""
        # Setup valid environment
        monkeypatch.setattr("app.startup_checks.BASE_DIR", str(tmp_path))
        
        config_path = tmp_path / "config.json"
        valid_config = {
            "database": {"filename": "test.db", "path": "db"},
            "ui": {"theme": "dark"},
            "features": {"enable_journal": True}
        }
        with open(config_path, 'w') as f:
            json.dump(valid_config, f)
        monkeypatch.setattr("app.startup_checks.CONFIG_PATH", str(config_path))
        
        # Create required directories
        for file_info in REQUIRED_FILES:
            if file_info["type"] == "directory":
                (tmp_path / file_info["path"]).mkdir(exist_ok=True)
        
        results = run_all_checks(raise_on_critical=False)
        
        assert len(results) == 3  # config, files, database
        # All should pass or warn (not fail)
        failed = [r for r in results if r.status == CheckStatus.FAILED]
        assert len(failed) == 0
    
    def test_run_all_checks_raises_on_critical_failure(self, monkeypatch):
        """Test that IntegrityError is raised on critical failure."""
        # Mock a failing check
        def mock_failing_check():
            return IntegrityCheckResult(
                name="mock_check",
                status=CheckStatus.FAILED,
                message="Critical failure"
            )
        
        with patch("app.startup_checks.check_config_integrity", mock_failing_check):
            with pytest.raises(IntegrityError):
                run_all_checks(raise_on_critical=True)
    
    def test_run_all_checks_no_raise_when_disabled(self, monkeypatch):
        """Test that no exception is raised when raise_on_critical=False."""
        def mock_failing_check():
            return IntegrityCheckResult(
                name="mock_check",
                status=CheckStatus.FAILED,
                message="Critical failure"
            )
        
        with patch("app.startup_checks.check_config_integrity", mock_failing_check):
            # Should not raise
            results = run_all_checks(raise_on_critical=False)
            assert any(r.status == CheckStatus.FAILED for r in results)


class TestGetCheckSummary:
    """Tests for the summary generation function."""
    
    def test_get_check_summary_format(self):
        """Test that summary is properly formatted."""
        results = [
            IntegrityCheckResult("check1", CheckStatus.PASSED, "OK"),
            IntegrityCheckResult("check2", CheckStatus.WARNING, "Minor issue", 
                               recovery_action="Fixed it"),
            IntegrityCheckResult("check3", CheckStatus.FAILED, "Critical"),
        ]
        
        summary = get_check_summary(results)
        
        assert "check1" in summary
        assert "check2" in summary
        assert "check3" in summary
        assert "Fixed it" in summary  # Recovery action
        assert "✓" in summary  # Passed symbol
        assert "⚠" in summary  # Warning symbol
        assert "✗" in summary  # Failed symbol


class TestIntegrityError:
    """Tests for the IntegrityError exception."""
    
    def test_integrity_error_inheritance(self):
        """Test that IntegrityError inherits from SoulSenseError."""
        from app.exceptions import SoulSenseError
        
        error = IntegrityError("Test error")
        assert isinstance(error, SoulSenseError)
        assert isinstance(error, Exception)
    
    def test_integrity_error_message(self):
        """Test that error message is preserved."""
        error = IntegrityError("Critical failure in startup")
        assert "Critical failure in startup" in str(error)
