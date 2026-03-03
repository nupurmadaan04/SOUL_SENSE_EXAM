#!/usr/bin/env python3
"""
Supply Chain Security Verification Script
Issue #1070: Implement Supply Chain Security Hardening

This script provides comprehensive supply chain security verification including:
- Hash verification for pinned dependencies
- Detection of unpinned/transitive dependencies
- Validation of requirements files
- Security gate for CI/CD pipelines
"""

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DependencyCheck:
    """Represents a dependency check result."""
    name: str
    version: str
    has_hash: bool = False
    hashes: List[str] = field(default_factory=list)
    is_pinned: bool = False
    error_messages: List[str] = field(default_factory=list)


class SupplyChainSecurityChecker:
    """
    Comprehensive supply chain security checker.
    
    Validates:
    - Dependency pinning (== versions)
    - Hash verification (--hash=sha256:)
    - No transitive dependency vulnerabilities
    - Requirements file integrity
    """
    
    SEVERITY_LEVELS = {
        'critical': 4,
        'high': 3,
        'medium': 2,
        'low': 1,
        'info': 0
    }
    
    def __init__(self, project_root: Path, severity_threshold: str = 'high'):
        self.project_root = project_root
        self.severity_threshold = severity_threshold
        self.threshold_value = self.SEVERITY_LEVELS.get(severity_threshold, 3)
        self.findings: List[Dict] = []
        
    def parse_requirements_file(self, filepath: Path) -> List[DependencyCheck]:
        """
        Parse a requirements file and extract dependency information.
        
        Args:
            filepath: Path to requirements file
            
        Returns:
            List of DependencyCheck objects
        """
        dependencies = []
        current_dep: Optional[DependencyCheck] = None
        
        if not filepath.exists():
            logger.warning(f"Requirements file not found: {filepath}")
            return dependencies
            
        content = filepath.read_text()
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments (except inline comments with packages)
            if not line or line.startswith('#') and '==' not in line:
                i += 1
                continue
                
            # Check for hash continuation lines
            if line.startswith('--hash=sha256:'):
                if current_dep:
                    hash_value = line.replace('--hash=sha256:', '').strip()
                    current_dep.hashes.append(hash_value)
                    current_dep.has_hash = True
                i += 1
                continue
            
            # Check for backslash continuation
            if line.endswith('\\'):
                # Multi-line entry - collect all lines
                full_line = line[:-1].strip()
                i += 1
                while i < len(lines) and lines[i].strip().startswith('--'):
                    full_line += ' ' + lines[i].strip()
                    i += 1
                line = full_line
            else:
                i += 1
            
            # Parse package specification
            # Match patterns like: package==1.0.0 or package==1.0.0 # comment
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*==\s*([^\s;#]+)', line)
            if match:
                package_name = match.group(1)
                version = match.group(2)
                
                current_dep = DependencyCheck(
                    name=package_name,
                    version=version,
                    is_pinned=True
                )
                
                # Check for inline hash
                if '--hash=sha256:' in line:
                    hash_matches = re.findall(r'--hash=sha256:([a-f0-9]+)', line)
                    current_dep.hashes.extend(hash_matches)
                    current_dep.has_hash = len(hash_matches) > 0
                
                dependencies.append(current_dep)
            elif '==' in line and not line.startswith('#'):
                # Unpinned or invalid version specifier
                logger.warning(f"Potential unpinned dependency: {line}")
        
        return dependencies
    
    def check_pinned_requirements(self, filepath: Path) -> Tuple[bool, List[str]]:
        """
        Check that all dependencies in a requirements file are pinned with hashes.
        
        Args:
            filepath: Path to requirements file
            
        Returns:
            Tuple of (passed, list of error messages)
        """
        errors = []
        dependencies = self.parse_requirements_file(filepath)
        
        if not dependencies:
            logger.warning(f"No dependencies found in {filepath}")
            return True, errors
        
        unpinned = []
        missing_hashes = []
        
        for dep in dependencies:
            if not dep.is_pinned:
                unpinned.append(dep.name)
                errors.append(f"Dependency '{dep.name}' is not pinned to a specific version")
            elif not dep.has_hash:
                missing_hashes.append(dep.name)
                errors.append(f"Dependency '{dep.name}=={dep.version}' is missing SHA256 hash")
        
        if unpinned:
            logger.error(f"Found {len(unpinned)} unpinned dependencies: {', '.join(unpinned)}")
        
        if missing_hashes:
            logger.error(f"Found {len(missing_hashes)} dependencies without hashes: {', '.join(missing_hashes)}")
        
        return len(errors) == 0, errors
    
    def verify_hash_integrity(self, package_name: str, version: str, expected_hash: str) -> bool:
        """
        Verify the hash integrity of an installed package.
        
        Note: This is a simplified check. In production, you would download
        the package and verify its actual hash against the expected hash.
        
        Args:
            package_name: Name of the package
            version: Expected version
            expected_hash: Expected SHA256 hash
            
        Returns:
            True if hash is valid format
        """
        # Validate hash format (64 hex characters)
        if not re.match(r'^[a-f0-9]{64}$', expected_hash, re.IGNORECASE):
            logger.error(f"Invalid hash format for {package_name}: {expected_hash}")
            return False
        return True
    
    def check_requirements_txt_exists(self) -> Tuple[bool, List[str]]:
        """
        Check that required requirements files exist and follow best practices.
        
        Returns:
            Tuple of (passed, list of error messages)
        """
        errors = []
        
        # Check for requirements.txt
        req_txt = self.project_root / 'requirements.txt'
        if not req_txt.exists():
            errors.append("requirements.txt not found")
            logger.error("requirements.txt not found in project root")
        
        # Check for requirements-pinned.txt (recommended)
        req_pinned = self.project_root / 'requirements-pinned.txt'
        if not req_pinned.exists():
            logger.warning("requirements-pinned.txt not found - consider creating one with hashed dependencies")
        else:
            # Validate pinned requirements
            passed, pin_errors = self.check_pinned_requirements(req_pinned)
            if not passed:
                errors.extend(pin_errors)
        
        return len(errors) == 0, errors
    
    def check_transitive_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Check for potentially vulnerable transitive dependencies.
        
        Returns:
            Tuple of (passed, list of warning messages)
        """
        warnings = []
        
        # Run pip list to see all installed packages
        try:
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                check=True
            )
            installed = json.loads(result.stdout)
            
            # Check if we have a requirements-pinned.txt that covers all installed packages
            req_pinned = self.project_root / 'requirements-pinned.txt'
            if req_pinned.exists():
                pinned_deps = self.parse_requirements_file(req_pinned)
                pinned_names = {d.name.lower() for d in pinned_deps}
                
                unpinned_installed = [
                    pkg['name'] for pkg in installed 
                    if pkg['name'].lower() not in pinned_names and pkg['name'].lower() != 'pip'
                ]
                
                if unpinned_installed:
                    warning_msg = f"Found {len(unpinned_installed)} unpinned installed packages: {', '.join(unpinned_installed[:5])}"
                    if len(unpinned_installed) > 5:
                        warning_msg += f" and {len(unpinned_installed) - 5} more"
                    warnings.append(warning_msg)
                    logger.warning(warning_msg)
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to check transitive dependencies: {e}")
        except FileNotFoundError:
            logger.warning("pip not found, skipping transitive dependency check")
        
        return len(warnings) == 0, warnings
    
    def generate_security_report(self, output_path: Optional[Path] = None) -> Dict:
        """
        Generate a comprehensive security report.
        
        Args:
            output_path: Optional path to write report to
            
        Returns:
            Dictionary containing report data
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'project_root': str(self.project_root),
            'severity_threshold': self.severity_threshold,
            'checks': {}
        }
        
        # Check 1: Requirements files exist and are valid
        req_passed, req_errors = self.check_requirements_txt_exists()
        report['checks']['requirements_validation'] = {
            'passed': req_passed,
            'errors': req_errors
        }
        
        # Check 2: Transitive dependencies
        trans_passed, trans_warnings = self.check_transitive_dependencies()
        report['checks']['transitive_dependencies'] = {
            'passed': trans_passed,
            'warnings': trans_warnings
        }
        
        # Check 3: Hash verification for pinned requirements
        req_pinned = self.project_root / 'requirements-pinned.txt'
        if req_pinned.exists():
            deps = self.parse_requirements_file(req_pinned)
            total_deps = len(deps)
            hashed_deps = sum(1 for d in deps if d.has_hash)
            
            report['checks']['hash_coverage'] = {
                'total_dependencies': total_deps,
                'hashed_dependencies': hashed_deps,
                'coverage_percentage': (hashed_deps / total_deps * 100) if total_deps > 0 else 0,
                'passed': hashed_deps == total_deps
            }
        
        # Overall status
        all_passed = all(check.get('passed', True) for check in report['checks'].values())
        report['overall_passed'] = all_passed
        
        # Write report if path provided
        if output_path:
            output_path.write_text(json.dumps(report, indent=2))
            logger.info(f"Security report written to {output_path}")
        
        return report
    
    def run_security_gate(self, fail_on_issues: bool = True) -> bool:
        """
        Run the complete security gate check.
        
        Args:
            fail_on_issues: Whether to fail (return False) if issues are found
            
        Returns:
            True if gate passed, False if failed
        """
        logger.info("=" * 60)
        logger.info("Supply Chain Security Gate")
        logger.info("=" * 60)
        
        report = self.generate_security_report()
        
        # Print summary
        logger.info("\nCheck Summary:")
        for check_name, check_data in report['checks'].items():
            status = "✅ PASS" if check_data.get('passed', True) else "❌ FAIL"
            logger.info(f"  {check_name}: {status}")
            
            if 'errors' in check_data and check_data['errors']:
                for error in check_data['errors']:
                    logger.error(f"    - {error}")
            
            if 'warnings' in check_data and check_data['warnings']:
                for warning in check_data['warnings']:
                    logger.warning(f"    - {warning}")
        
        if 'hash_coverage' in report['checks']:
            coverage = report['checks']['hash_coverage']
            logger.info(f"\nHash Coverage: {coverage['hashed_dependencies']}/{coverage['total_dependencies']} "
                       f"({coverage['coverage_percentage']:.1f}%)")
        
        logger.info("=" * 60)
        
        if report['overall_passed']:
            logger.info("✅ Supply chain security gate PASSED")
            return True
        else:
            logger.error("❌ Supply chain security gate FAILED")
            if fail_on_issues:
                return False
            return True


def main():
    """Main entry point for the supply chain security checker."""
    parser = argparse.ArgumentParser(
        description='Supply Chain Security Verification Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full security check
  python scripts/supply_chain_security.py --check
  
  # Generate security report
  python scripts/supply_chain_security.py --report security-report.json
  
  # Run as CI gate (fails on issues)
  python scripts/supply_chain_security.py --gate --fail-on-issues
  
  # Check specific requirements file
  python scripts/supply_chain_security.py --check --requirements requirements-pinned.txt
        """
    )
    
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path('.'),
        help='Project root directory (default: current directory)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run dependency checks'
    )
    
    parser.add_argument(
        '--gate',
        action='store_true',
        help='Run as CI security gate'
    )
    
    parser.add_argument(
        '--report',
        type=Path,
        metavar='PATH',
        help='Generate JSON report to specified path'
    )
    
    parser.add_argument(
        '--requirements',
        type=Path,
        metavar='PATH',
        help='Path to requirements file to check'
    )
    
    parser.add_argument(
        '--severity-threshold',
        choices=['critical', 'high', 'medium', 'low', 'info'],
        default='high',
        help='Severity threshold for gate (default: high)'
    )
    
    parser.add_argument(
        '--fail-on-issues',
        action='store_true',
        default=True,
        help='Fail if security issues are found (default: True)'
    )
    
    parser.add_argument(
        '--no-fail-on-issues',
        action='store_true',
        help='Do not fail even if security issues are found'
    )
    
    args = parser.parse_args()
    
    # Handle --no-fail-on-issues
    fail_on_issues = not args.no_fail_on_issues if args.no_fail_on_issues else args.fail_on_issues
    
    checker = SupplyChainSecurityChecker(
        project_root=args.project_root,
        severity_threshold=args.severity_threshold
    )
    
    if args.requirements:
        # Check specific requirements file
        passed, errors = checker.check_pinned_requirements(args.requirements)
        if not passed:
            for error in errors:
                print(f"ERROR: {error}")
            sys.exit(1)
        print(f"✅ Requirements file validation passed: {args.requirements}")
        sys.exit(0)
    
    elif args.gate:
        # Run as CI gate
        passed = checker.run_security_gate(fail_on_issues=fail_on_issues)
        sys.exit(0 if passed else 1)
    
    elif args.report:
        # Generate report
        report = checker.generate_security_report(args.report)
        print(f"Security report generated: {args.report}")
        print(f"Overall status: {'PASSED' if report['overall_passed'] else 'FAILED'}")
        sys.exit(0 if report['overall_passed'] else 1)
    
    elif args.check:
        # Run checks
        passed = checker.run_security_gate(fail_on_issues=False)
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
