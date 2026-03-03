"""
Tests for Supply Chain Security Hardening #1070

Comprehensive test suite covering:
- Dependency pinning verification
- Hash verification validation
- Supply chain security gate functionality
- Requirements file parsing
- Security report generation
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.supply_chain_security import (
    DependencyCheck,
    SupplyChainSecurityChecker,
    main
)


class TestDependencyCheck:
    """Test DependencyCheck dataclass functionality."""

    def test_dependency_check_creation(self):
        """Test creating a DependencyCheck instance."""
        dep = DependencyCheck(
            name="requests",
            version="2.31.0",
            is_pinned=True,
            has_hash=True,
            hashes=["abc123"]
        )
        assert dep.name == "requests"
        assert dep.version == "2.31.0"
        assert dep.is_pinned is True
        assert dep.has_hash is True
        assert dep.hashes == ["abc123"]

    def test_dependency_check_defaults(self):
        """Test DependencyCheck with default values."""
        dep = DependencyCheck(name="fastapi", version="0.100.0")
        assert dep.has_hash is False
        assert dep.is_pinned is False
        assert dep.hashes == []
        assert dep.error_messages == []


class TestSupplyChainSecurityChecker:
    """Test SupplyChainSecurityChecker functionality."""

    @pytest.fixture
    def checker(self, tmp_path):
        """Create a checker instance with temporary project root."""
        return SupplyChainSecurityChecker(project_root=tmp_path)

    @pytest.fixture
    def sample_requirements(self, tmp_path):
        """Create a sample requirements file."""
        req_file = tmp_path / "requirements-pinned.txt"
        content = """
# Test requirements file
bandit==1.7.8 \\
    --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
safety==3.2.0 \\
    --hash=sha256:6f9e0d8f5b6c4c8d7e9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2

# Package without hash
unpinned-package>=1.0.0
"""
        req_file.write_text(content)
        return req_file

    def test_parse_requirements_file_with_hashes(self, checker, sample_requirements):
        """Test parsing requirements file with hashed dependencies."""
        deps = checker.parse_requirements_file(sample_requirements)
        
        assert len(deps) == 2
        
        # Check first dependency
        bandit = next(d for d in deps if d.name == "bandit")
        assert bandit.version == "1.7.8"
        assert bandit.is_pinned is True
        assert bandit.has_hash is True
        assert len(bandit.hashes) == 1

    def test_parse_requirements_file_not_found(self, checker, tmp_path):
        """Test parsing non-existent requirements file."""
        non_existent = tmp_path / "non_existent.txt"
        deps = checker.parse_requirements_file(non_existent)
        assert deps == []

    def test_check_pinned_requirements_all_pinned(self, checker, tmp_path):
        """Test check with all dependencies pinned and hashed."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("""
package1==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
package2==2.0.0 --hash=sha256:b8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
""")
        
        passed, errors = checker.check_pinned_requirements(req_file)
        assert passed is True
        assert errors == []

    def test_check_pinned_requirements_missing_hash(self, checker, tmp_path):
        """Test check with dependency missing hash."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("package1==1.0.0")
        
        passed, errors = checker.check_pinned_requirements(req_file)
        assert passed is False
        assert len(errors) == 1
        assert "missing SHA256 hash" in errors[0]

    def test_check_pinned_requirements_unpinned(self, checker, tmp_path):
        """Test check with unpinned dependency."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("package1>=1.0.0")
        
        passed, errors = checker.check_pinned_requirements(req_file)
        # Unpinned packages don't get added to the list
        assert passed is True  # No pinned packages to check

    def test_verify_hash_integrity_valid(self, checker):
        """Test hash integrity verification with valid hash."""
        valid_hash = "a" * 64  # 64 hex characters
        result = checker.verify_hash_integrity("package", "1.0.0", valid_hash)
        assert result is True

    def test_verify_hash_integrity_invalid(self, checker):
        """Test hash integrity verification with invalid hash."""
        invalid_hash = "short"
        result = checker.verify_hash_integrity("package", "1.0.0", invalid_hash)
        assert result is False

    def test_check_requirements_txt_exists_no_pinned(self, checker, tmp_path):
        """Test check when requirements-pinned.txt doesn't exist."""
        (tmp_path / "requirements.txt").write_text("package==1.0.0")
        
        passed, errors = checker.check_requirements_txt_exists()
        assert passed is True  # Still passes, just warns
        assert errors == []

    def test_check_requirements_txt_exists_missing_requirements(self, checker, tmp_path):
        """Test check when requirements.txt doesn't exist."""
        passed, errors = checker.check_requirements_txt_exists()
        assert passed is False
        assert "requirements.txt not found" in errors

    def test_check_transitive_dependencies(self, checker, tmp_path):
        """Test transitive dependency check."""
        # Create pinned requirements
        pinned = tmp_path / "requirements-pinned.txt"
        pinned.write_text("package1==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([
                    {"name": "package1", "version": "1.0.0"},
                    {"name": "unpinned-package", "version": "2.0.0"}
                ])
            )
            
            passed, warnings = checker.check_transitive_dependencies()
            # Should warn about unpinned installed packages
            assert len(warnings) > 0

    def test_generate_security_report(self, checker, tmp_path):
        """Test security report generation."""
        # Create requirements files
        (tmp_path / "requirements.txt").write_text("package==1.0.0")
        
        report = checker.generate_security_report()
        
        assert 'timestamp' in report
        assert 'project_root' in report
        assert 'checks' in report
        assert 'overall_passed' in report

    def test_generate_security_report_with_output(self, checker, tmp_path):
        """Test security report generation with output file."""
        (tmp_path / "requirements.txt").write_text("package==1.0.0")
        output_path = tmp_path / "report.json"
        
        report = checker.generate_security_report(output_path)
        
        assert output_path.exists()
        saved_report = json.loads(output_path.read_text())
        assert saved_report['overall_passed'] == report['overall_passed']

    def test_run_security_gate_pass(self, checker, tmp_path):
        """Test security gate that passes."""
        # Create a valid requirements-pinned.txt
        pinned = tmp_path / "requirements-pinned.txt"
        pinned.write_text(
            "package1==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f"
        )
        (tmp_path / "requirements.txt").write_text("package1==1.0.0")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{"name": "package1", "version": "1.0.0"}])
            )
            result = checker.run_security_gate(fail_on_issues=True)
            assert result is True

    def test_run_security_gate_fail(self, checker, tmp_path):
        """Test security gate that fails."""
        # Don't create requirements.txt to trigger failure
        result = checker.run_security_gate(fail_on_issues=True)
        assert result is False

    def test_parse_multiline_requirement(self, checker, tmp_path):
        """Test parsing multi-line requirements entry."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("""
package1==1.0.0 \\
    --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f \\
    --hash=sha256:b8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
""")
        
        deps = checker.parse_requirements_file(req_file)
        assert len(deps) == 1
        assert deps[0].hashes == [
            "a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f",
            "b8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f"
        ]

    def test_parse_inline_hash(self, checker, tmp_path):
        """Test parsing inline hash in requirements."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            'package1==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f'
        )
        
        deps = checker.parse_requirements_file(req_file)
        assert len(deps) == 1
        assert deps[0].has_hash is True


class TestSupplyChainSecurityIntegration:
    """Integration tests for supply chain security."""

    def test_full_workflow_valid_project(self, tmp_path):
        """Test complete workflow with valid project structure."""
        # Create project structure
        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\nuvicorn==0.23.0")
        (tmp_path / "requirements-pinned.txt").write_text("""
fastapi==0.100.0 \\
    --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
uvicorn==0.23.0 \\
    --hash=sha256:b8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
""")
        
        checker = SupplyChainSecurityChecker(project_root=tmp_path)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([
                    {"name": "fastapi", "version": "0.100.0"},
                    {"name": "uvicorn", "version": "0.23.0"}
                ])
            )
            
            report = checker.generate_security_report()
            assert report['overall_passed'] is True

    def test_full_workflow_invalid_project(self, tmp_path):
        """Test complete workflow with missing requirements."""
        checker = SupplyChainSecurityChecker(project_root=tmp_path)
        
        report = checker.generate_security_report()
        assert report['overall_passed'] is False
        assert 'requirements_validation' in report['checks']
        assert report['checks']['requirements_validation']['passed'] is False


class TestMainFunction:
    """Test main function CLI behavior."""

    def test_main_check_specific_requirements(self, tmp_path, monkeypatch):
        """Test main with --requirements flag."""
        req_file = tmp_path / "test.txt"
        req_file.write_text(
            "package==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f"
        )
        
        monkeypatch.setattr(sys, 'argv', [
            'script', '--requirements', str(req_file)
        ])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0

    def test_main_gate_mode(self, tmp_path, monkeypatch):
        """Test main with --gate flag."""
        # Create valid requirements
        (tmp_path / "requirements.txt").write_text("package==1.0.0")
        (tmp_path / "requirements-pinned.txt").write_text(
            "package==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f"
        )
        
        monkeypatch.setattr(sys, 'argv', [
            'script', '--gate', '--project-root', str(tmp_path)
        ])
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{"name": "package", "version": "1.0.0"}])
            )
            
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 0

    def test_main_report_mode(self, tmp_path, monkeypatch):
        """Test main with --report flag."""
        (tmp_path / "requirements.txt").write_text("package==1.0.0")
        report_path = tmp_path / "report.json"
        
        monkeypatch.setattr(sys, 'argv', [
            'script', '--report', str(report_path), '--project-root', str(tmp_path)
        ])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        assert report_path.exists()

    def test_main_no_args(self, monkeypatch):
        """Test main with no arguments shows help."""
        monkeypatch.setattr(sys, 'argv', ['script'])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0


class TestSecurityEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_requirements_file(self, checker, tmp_path):
        """Test parsing empty requirements file."""
        req_file = tmp_path / "empty.txt"
        req_file.write_text("")
        
        deps = checker.parse_requirements_file(req_file)
        assert deps == []

    def test_requirements_with_only_comments(self, checker, tmp_path):
        """Test parsing requirements file with only comments."""
        req_file = tmp_path / "comments.txt"
        req_file.write_text("# Comment 1\n# Comment 2")
        
        deps = checker.parse_requirements_file(req_file)
        assert deps == []

    def test_malformed_version_specifier(self, checker, tmp_path, caplog):
        """Test handling of malformed version specifiers."""
        req_file = tmp_path / "malformed.txt"
        req_file.write_text("package>=1.0.0<2.0.0")
        
        deps = checker.parse_requirements_file(req_file)
        # Should not crash, just not parse this entry
        assert len(deps) == 0

    def test_very_long_hash(self, checker):
        """Test hash verification with invalid long hash."""
        long_hash = "a" * 100
        result = checker.verify_hash_integrity("package", "1.0.0", long_hash)
        assert result is False

    def test_non_hex_hash(self, checker):
        """Test hash verification with non-hex characters."""
        non_hex_hash = "xyz" + "a" * 61
        result = checker.verify_hash_integrity("package", "1.0.0", non_hex_hash)
        assert result is False

    def test_subprocess_failure_transitive_check(self, checker, tmp_path):
        """Test handling of subprocess failure in transitive check."""
        (tmp_path / "requirements-pinned.txt").write_text(
            "package==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f"
        )
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command failed")
            
            passed, warnings = checker.check_transitive_dependencies()
            # Should handle gracefully
            assert isinstance(warnings, list)


class TestHashCoverageReport:
    """Test hash coverage reporting."""

    def test_full_hash_coverage(self, checker, tmp_path):
        """Test report with 100% hash coverage."""
        (tmp_path / "requirements-pinned.txt").write_text("""
package1==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
package2==2.0.0 --hash=sha256:b8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
""")
        
        report = checker.generate_security_report()
        
        assert 'hash_coverage' in report['checks']
        coverage = report['checks']['hash_coverage']
        assert coverage['total_dependencies'] == 2
        assert coverage['hashed_dependencies'] == 2
        assert coverage['coverage_percentage'] == 100.0
        assert coverage['passed'] is True

    def test_partial_hash_coverage(self, checker, tmp_path):
        """Test report with partial hash coverage."""
        (tmp_path / "requirements-pinned.txt").write_text("""
package1==1.0.0 --hash=sha256:a8bf9e42d6f5f727dbf7d5cec38c02ae4e690fde9ad31c8dc2aabb0d5d7b3a3f
package2==2.0.0
""")
        
        report = checker.generate_security_report()
        
        coverage = report['checks']['hash_coverage']
        assert coverage['total_dependencies'] == 2
        assert coverage['hashed_dependencies'] == 1
        assert coverage['coverage_percentage'] == 50.0
        assert coverage['passed'] is False


class TestSeverityThresholds:
    """Test different severity threshold configurations."""

    def test_critical_threshold(self, tmp_path):
        """Test checker with critical threshold."""
        checker = SupplyChainSecurityChecker(
            project_root=tmp_path,
            severity_threshold='critical'
        )
        assert checker.threshold_value == 4

    def test_high_threshold(self, tmp_path):
        """Test checker with high threshold."""
        checker = SupplyChainSecurityChecker(
            project_root=tmp_path,
            severity_threshold='high'
        )
        assert checker.threshold_value == 3

    def test_invalid_threshold_defaults_to_high(self, tmp_path):
        """Test checker with invalid threshold defaults to high."""
        checker = SupplyChainSecurityChecker(
            project_root=tmp_path,
            severity_threshold='invalid'
        )
        assert checker.threshold_value == 3  # defaults to high


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
