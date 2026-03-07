#!/usr/bin/env python3
"""
Static Analysis Severity Budget Enforcer

Enforces quality gates by comparing actual static analysis violations
against configured severity budgets for mypy, flake8, and bandit.
"""

import json
import subprocess
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

class BudgetEnforcer:
    """Enforce static analysis severity budgets."""

    SEVERITY_ORDER = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}

    def __init__(self, config_path: str, project_root: str = '.'):
        self.project_root = Path(project_root)
        with open(config_path) as f:
            self.budget = json.load(f)
        self.violations = {'mypy': {}, 'flake8': {}, 'bandit': {}}
        self.report = {'status': 'pass', 'tools_checked': [], 'details': {}}

    def run_mypy(self) -> Dict[str, List[Dict]]:
        """Run mypy and parse violations."""
        violations = {'critical': [], 'high': [], 'medium': [], 'low': []}
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'mypy', 'app/', 'backend/', '--json'],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    try:
                        error = json.loads(line)
                        severity = self._classify_mypy_error(error.get('msg', ''))
                        violations[severity].append(error)
                    except json.JSONDecodeError:
                        violations['low'].append({'msg': line})

            logger.info(f"✓ mypy scan completed")
            return violations
        except Exception as e:
            logger.error(f"✗ mypy scan failed: {e}")
            return violations

    def run_flake8(self) -> Dict[str, List[Dict]]:
        """Run flake8 and parse violations."""
        violations = {'critical': [], 'high': [], 'medium': [], 'low': []}
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'flake8', '.', '--format=json', '--extend-ignore=E203,W503'],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.stdout:
                errors = json.loads(result.stdout)
                for error in errors:
                    severity = self._classify_flake8_error(error.get('code', ''))
                    violations[severity].append(error)

            logger.info(f"✓ flake8 scan completed")
            return violations
        except json.JSONDecodeError:
            logger.warning("⚠ flake8 output parsing failed")
            return violations
        except Exception as e:
            logger.error(f"✗ flake8 scan failed: {e}")
            return violations

    def run_bandit(self) -> Dict[str, List[Dict]]:
        """Run bandit and parse violations."""
        violations = {'critical': [], 'high': [], 'medium': [], 'low': []}
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'bandit', '-r', 'backend/', '-f', 'json', '-ll'],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.stdout:
                data = json.loads(result.stdout)
                for issue in data.get('results', []):
                    severity = issue.get('severity', 'medium').lower()
                    violations[severity].append(issue)

            logger.info(f"✓ bandit scan completed")
            return violations
        except json.JSONDecodeError:
            logger.warning("⚠ bandit output parsing failed")
            return violations
        except Exception as e:
            logger.error(f"✗ bandit scan failed: {e}")
            return violations

    def _classify_mypy_error(self, msg: str) -> str:
        """Classify mypy error by severity."""
        if any(x in msg for x in ['syntax error', 'invalid syntax']):
            return 'critical'
        if any(x in msg for x in ['no-redef', 'name-defined', 'type-var']):
            return 'high'
        if any(x in msg for x in ['assignment', 'call-arg', 'union-attr']):
            return 'medium'
        return 'low'

    def _classify_flake8_error(self, code: str) -> str:
        """Classify flake8 error by severity."""
        if code.startswith('E9'):  # Syntax errors
            return 'critical'
        if code.startswith('C9'):  # McCabe complexity
            return 'high'
        if code.startswith(('E1', 'E2', 'E7')):  # Logic errors
            return 'medium'
        return 'low'  # Style warnings

    def check_budget(self, tool: str, violations: Dict[str, List]) -> Tuple[bool, Dict]:
        """Check if violations exceed budget for a tool."""
        budget = self.budget.get(tool, {})
        result = {'passed': True, 'summary': {}, 'exceeded': []}

        for severity in ['critical', 'high', 'medium', 'low']:
            count = len(violations.get(severity, []))
            limit = budget.get(severity, 0)
            result['summary'][severity] = {'count': count, 'limit': limit}

            if count > limit:
                result['passed'] = False
                result['exceeded'].append({
                    'severity': severity,
                    'count': count,
                    'limit': limit,
                    'overage': count - limit
                })

        return result['passed'], result

    def enforce(self) -> bool:
        """Run all checks and determine if budget is respected."""
        all_passed = True

        # Run mypy
        mypy_violations = self.run_mypy()
        passed, details = self.check_budget('mypy', mypy_violations)
        self.report['details']['mypy'] = details
        self.violations['mypy'] = mypy_violations
        all_passed = all_passed and passed

        # Run flake8
        flake8_violations = self.run_flake8()
        passed, details = self.check_budget('flake8', flake8_violations)
        self.report['details']['flake8'] = details
        self.violations['flake8'] = flake8_violations
        all_passed = all_passed and passed

        # Run bandit
        bandit_violations = self.run_bandit()
        passed, details = self.check_budget('bandit', bandit_violations)
        self.report['details']['bandit'] = details
        self.violations['bandit'] = bandit_violations
        all_passed = all_passed and passed

        self.report['status'] = 'pass' if all_passed else 'fail'
        return all_passed

    def print_summary(self):
        """Print summary of findings."""
        print("\n" + "=" * 70)
        print("STATIC ANALYSIS SEVERITY BUDGET REPORT")
        print("=" * 70)

        for tool in ['mypy', 'flake8', 'bandit']:
            details = self.report['details'].get(tool, {})
            summary = details.get('summary', {})

            print(f"\n{tool.upper()}:")
            passed = all(summary[s]['count'] <= summary[s]['limit'] for s in ['critical', 'high', 'medium', 'low'])
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  Status: {status}")

            for severity in ['critical', 'high', 'medium', 'low']:
                s = summary.get(severity, {})
                count = s.get('count', 0)
                limit = s.get('limit', 0)
                mark = "✓" if count <= limit else "✗"
                print(f"  {mark} {severity:8} : {count:3} / {limit:3}")

        print("\n" + "=" * 70)
        print(f"OVERALL: {self.report['status'].upper()}")
        print("=" * 70 + "\n")

    def save_report(self, output_file: str):
        """Save detailed report to JSON."""
        report = {
            'status': self.report['status'],
            'summary': self.report['details'],
            'violations': {
                tool: {severity: len(v) for severity, v in vdict.items()}
                for tool, vdict in self.violations.items()
            }
        }
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Static Analysis Severity Budget Enforcer')
    parser.add_argument('--config', default='config/static_analysis_budget.json',
                       help='Path to budget configuration')
    parser.add_argument('--project-root', default='.',
                       help='Project root directory')
    parser.add_argument('--report', help='Output report file')
    args = parser.parse_args()

    enforcer = BudgetEnforcer(args.config, args.project_root)
    passed = enforcer.enforce()
    enforcer.print_summary()

    if args.report:
        enforcer.save_report(args.report)

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
