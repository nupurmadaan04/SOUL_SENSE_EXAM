"""
Unit tests for Static Analysis Severity Budget Enforcer (Issue #1435).

Tests severity classification, budget comparison, and report generation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.static_analysis_gate import BudgetEnforcer


class TestMypySeverityClassification:
    """Test mypy error classification."""

    def test_syntax_error_is_critical(self):
        """Syntax errors should be classified as critical."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_mypy_error('syntax error: invalid syntax')
        assert severity == 'critical'

    def test_no_redef_is_high(self):
        """Name redefinition errors should be classified as high."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_mypy_error('error from no-redef check')
        assert severity == 'high'

    def test_name_defined_is_high(self):
        """Name-defined errors should be classified as high."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_mypy_error('name-defined: this is an error')
        assert severity == 'high'

    def test_assignment_is_medium(self):
        """Assignment errors should be classified as medium."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_mypy_error('Incompatible types in assignment')
        assert severity == 'medium'

    def test_other_errors_are_low(self):
        """Unknown errors should be classified as low."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_mypy_error('some random error message')
        assert severity == 'low'


class TestFlake8SeverityClassification:
    """Test flake8 error classification."""

    def test_e9xx_is_critical(self):
        """E9xx errors (syntax) should be critical."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_flake8_error('E901')
        assert severity == 'critical'

    def test_c9xx_is_high(self):
        """C9xx errors (complexity) should be high."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_flake8_error('C901')
        assert severity == 'high'

    def test_e1xx_is_medium(self):
        """E1xx errors (indentation) should be medium."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_flake8_error('E101')
        assert severity == 'medium'

    def test_e2xx_is_medium(self):
        """E2xx errors (whitespace) should be medium."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_flake8_error('E201')
        assert severity == 'medium'

    def test_e7xx_is_medium(self):
        """E7xx errors should be medium."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_flake8_error('E701')
        assert severity == 'medium'

    def test_other_codes_are_low(self):
        """Other error codes should be low."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        severity = enforcer._classify_flake8_error('W292')
        assert severity == 'low'


class TestBudgetComparison:
    """Test budget comparison logic."""

    def test_violations_under_budget_pass(self):
        """Violations under limit should pass."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        violations = {
            'critical': [],
            'high': [{'msg': 'error1'}, {'msg': 'error2'}],
            'medium': [{'msg': 'error3'}],
            'low': []
        }
        passed, result = enforcer.check_budget('flake8', violations)
        assert passed is True
        assert result['passed'] is True

    def test_violations_equal_budget_pass(self):
        """Violations equal to limit should pass."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        violations = {
            'critical': [],
            'high': [{'msg': f'error{i}'} for i in range(5)],  # Limit is 5
            'medium': [],
            'low': []
        }
        passed, result = enforcer.check_budget('flake8', violations)
        assert passed is True

    def test_violations_over_budget_fail(self):
        """Violations exceeding limit should fail."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        violations = {
            'critical': [],
            'high': [{'msg': f'error{i}'} for i in range(6)],  # Limit is 5
            'medium': [],
            'low': []
        }
        passed, result = enforcer.check_budget('flake8', violations)
        assert passed is False
        assert result['passed'] is False
        assert len(result['exceeded']) == 1
        assert result['exceeded'][0]['severity'] == 'high'
        assert result['exceeded'][0]['overage'] == 1

    def test_critical_violations_fail_immediately(self):
        """Any critical violations should fail."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        violations = {
            'critical': [{'msg': 'syntax error'}],
            'high': [],
            'medium': [],
            'low': []
        }
        passed, result = enforcer.check_budget('mypy', violations)
        assert passed is False

    def test_multiple_severity_levels_exceed(self):
        """Multiple severity levels exceeding should all be reported."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        violations = {
            'critical': [{'msg': 'critical1'}],  # Limit is 0
            'high': [{'msg': f'high{i}'} for i in range(15)],  # Limit is 10
            'medium': [],
            'low': []
        }
        passed, result = enforcer.check_budget('mypy', violations)
        assert passed is False
        assert len(result['exceeded']) == 2


class TestReportGeneration:
    """Test report generation."""

    def test_report_structure(self):
        """Generated report should have correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'budget.json'
            with open(config_file, 'w') as f:
                json.dump({
                    'mypy': {'critical': 0, 'high': 5, 'medium': 10, 'low': 20},
                    'flake8': {'critical': 0, 'high': 5, 'medium': 10, 'low': 20},
                    'bandit': {'critical': 0, 'high': 0, 'medium': 3, 'low': 10}
                }, f)

            enforcer = BudgetEnforcer(str(config_file), tmpdir)
            report_file = Path(tmpdir) / 'report.json'

            # Mock the scan methods
            enforcer.violations = {
                'mypy': {'critical': [], 'high': [], 'medium': [], 'low': []},
                'flake8': {'critical': [], 'high': [], 'medium': [], 'low': []},
                'bandit': {'critical': [], 'high': [], 'medium': [], 'low': []}
            }
            enforcer.report['status'] = 'pass'
            enforcer.report['details'] = {
                'mypy': {'passed': True, 'summary': {}, 'exceeded': []},
                'flake8': {'passed': True, 'summary': {}, 'exceeded': []},
                'bandit': {'passed': True, 'summary': {}, 'exceeded': []}
            }

            enforcer.save_report(str(report_file))

            assert report_file.exists()
            with open(report_file) as f:
                report = json.load(f)

            assert 'status' in report
            assert 'summary' in report
            assert 'violations' in report
            assert 'mypy' in report['summary']
            assert 'flake8' in report['summary']
            assert 'bandit' in report['summary']

    def test_report_includes_violation_counts(self):
        """Report should include violation counts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'budget.json'
            with open(config_file, 'w') as f:
                json.dump({
                    'mypy': {'critical': 0, 'high': 5, 'medium': 10, 'low': 20},
                    'flake8': {'critical': 0, 'high': 5, 'medium': 10, 'low': 20},
                    'bandit': {'critical': 0, 'high': 0, 'medium': 3, 'low': 10}
                }, f)

            enforcer = BudgetEnforcer(str(config_file), tmpdir)
            report_file = Path(tmpdir) / 'report.json'

            enforcer.violations = {
                'mypy': {'critical': [], 'high': [1, 2], 'medium': [1, 2, 3], 'low': []},
                'flake8': {'critical': [], 'high': [], 'medium': [], 'low': [1]},
                'bandit': {'critical': [], 'high': [], 'medium': [], 'low': []}
            }
            enforcer.report['status'] = 'pass'
            enforcer.report['details'] = {
                'mypy': {'passed': True, 'summary': {}, 'exceeded': []},
                'flake8': {'passed': True, 'summary': {}, 'exceeded': []},
                'bandit': {'passed': True, 'summary': {}, 'exceeded': []}
            }

            enforcer.save_report(str(report_file))

            with open(report_file) as f:
                report = json.load(f)

            assert report['violations']['mypy']['high'] == 2
            assert report['violations']['mypy']['medium'] == 3
            assert report['violations']['flake8']['low'] == 1


class TestConfigLoading:
    """Test configuration loading."""

    def test_load_budget_config(self):
        """Should load budget configuration successfully."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        assert 'mypy' in enforcer.budget
        assert 'flake8' in enforcer.budget
        assert 'bandit' in enforcer.budget

    def test_budget_has_severity_levels(self):
        """Budget config should have all severity levels for each tool."""
        enforcer = BudgetEnforcer('config/static_analysis_budget.json')
        for tool in ['mypy', 'flake8', 'bandit']:
            for severity in ['critical', 'high', 'medium', 'low']:
                assert severity in enforcer.budget[tool]
                assert isinstance(enforcer.budget[tool][severity], int)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
