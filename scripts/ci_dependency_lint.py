"""
CI/CD Integration for Dependency Linting

This script is designed to be run in CI/CD pipelines to enforce
architectural boundaries and prevent circular dependencies.

Exit codes:
    0: All checks passed
    1: Circular dependencies found
    2: Layer violations found
    3: Excessive dependencies found
    4: Multiple violations found
"""

import sys
import json
from pathlib import Path
from typing import Dict, List
import argparse

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from dependency_analyzer import DependencyAnalyzer, CircularDependency
from dependency_rules import (
    LAYER_HIERARCHY,
    MODULE_RULES,
    CI_CONFIG,
    EXCLUDE_PATTERNS
)


class CILinter:
    """CI/CD linter for dependency checks."""
    
    def __init__(self, root_path: Path, strict: bool = False):
        self.root_path = root_path
        self.strict = strict
        self.analyzer = DependencyAnalyzer(root_path, EXCLUDE_PATTERNS)
        self.violations = {
            'circular': [],
            'layer': [],
            'excessive': [],
            'critical': []
        }
        
    def run_all_checks(self) -> Dict:
        """Run all dependency checks."""
        print("🔍 Running dependency checks...")
        print(f"   Root path: {self.root_path}")
        print(f"   Strict mode: {self.strict}")
        print()
        
        # Scan and build graph
        self.analyzer.scan_directory()
        self.analyzer.build_graph()
        
        # Run checks
        self.check_circular_dependencies()
        self.check_layer_violations()
        self.check_excessive_dependencies()
        self.check_critical_modules()
        
        return self.generate_ci_report()
    
    def check_circular_dependencies(self) -> None:
        """Check for circular dependencies."""
        print("📊 Checking for circular dependencies...")
        
        circular_deps = self.analyzer.detect_circular_dependencies()
        
        if circular_deps:
            print(f"   ❌ Found {len(circular_deps)} circular dependencies")
            self.violations['circular'] = [
                {
                    'cycle': dep.cycle,
                    'severity': 'error' if CI_CONFIG['fail_on_circular'] else 'warning'
                }
                for dep in circular_deps
            ]
        else:
            print("   ✅ No circular dependencies found")
    
    def check_layer_violations(self) -> None:
        """Check for architectural layer violations."""
        print("📊 Checking for layer violations...")
        
        violations = self.analyzer.check_layer_violations()
        
        if violations:
            print(f"   ❌ Found {len(violations)} layer violations")
            self.violations['layer'] = [
                {
                    'from': m1,
                    'to': m2,
                    'reason': reason,
                    'severity': 'error' if CI_CONFIG['fail_on_layer_violations'] else 'warning'
                }
                for m1, m2, reason in violations
            ]
        else:
            print("   ✅ No layer violations found")
    
    def check_excessive_dependencies(self) -> None:
        """Check for modules with excessive dependencies."""
        print("📊 Checking for excessive dependencies...")
        
        max_deps = MODULE_RULES['max_dependencies']
        excessive = []
        
        for module_name, module in self.analyzer.modules.items():
            layer = module.layer
            max_allowed = max_deps.get(layer, max_deps['default'])
            dep_count = len(self.analyzer.dependency_graph.get(module_name, set()))
            
            if dep_count > max_allowed:
                excessive.append({
                    'module': module_name,
                    'layer': layer,
                    'count': dep_count,
                    'max_allowed': max_allowed,
                    'severity': 'error' if CI_CONFIG['fail_on_excessive_deps'] else 'warning'
                })
        
        if excessive:
            print(f"   ⚠️  Found {len(excessive)} modules with excessive dependencies")
            self.violations['excessive'] = excessive
        else:
            print("   ✅ No excessive dependencies found")
    
    def check_critical_modules(self) -> None:
        """Check critical modules for any issues."""
        print("📊 Checking critical modules...")
        
        critical_modules = MODULE_RULES['critical_modules']
        issues = []
        
        for module_name in self.analyzer.modules.keys():
            # Check if module name contains any critical module identifier
            for critical in critical_modules:
                if critical in module_name:
                    # Check if this module is in any circular dependency
                    for circ in self.violations['circular']:
                        if module_name in circ['cycle']:
                            issues.append({
                                'module': module_name,
                                'issue': 'Circular dependency in critical module',
                                'severity': 'critical'
                            })
                    
                    # Check dependency count
                    dep_count = len(self.analyzer.dependency_graph.get(module_name, set()))
                    if dep_count > 8:  # Critical modules should have fewer deps
                        issues.append({
                            'module': module_name,
                            'issue': f'Too many dependencies for critical module: {dep_count}',
                            'severity': 'warning'
                        })
        
        if issues:
            print(f"   ⚠️  Found {len(issues)} issues in critical modules")
            self.violations['critical'] = issues
        else:
            print("   ✅ No issues in critical modules")
    
    def generate_ci_report(self) -> Dict:
        """Generate CI report."""
        total_errors = sum(
            len(v) for k, v in self.violations.items() 
            if any(item.get('severity') == 'error' for item in v)
        )
        total_warnings = sum(
            len(v) for k, v in self.violations.items() 
            if any(item.get('severity') == 'warning' for item in v)
        )
        total_critical = len(self.violations['critical'])
        
        report = {
            'status': 'passed' if total_errors == 0 else 'failed',
            'summary': {
                'total_modules': len(self.analyzer.modules),
                'total_dependencies': sum(
                    len(deps) for deps in self.analyzer.dependency_graph.values()
                ),
                'errors': total_errors,
                'warnings': total_warnings,
                'critical_issues': total_critical
            },
            'violations': self.violations,
            'metadata': {
                'root_path': str(self.root_path),
                'strict_mode': self.strict,
                'timestamp': self.get_timestamp()
            }
        }
        
        return report
    
    def get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def print_summary(self, report: Dict) -> None:
        """Print summary of checks."""
        print("\n" + "="*80)
        print("DEPENDENCY LINT SUMMARY")
        print("="*80)
        print(f"\nStatus: {report['status'].upper()}")
        print(f"Total Modules: {report['summary']['total_modules']}")
        print(f"Total Dependencies: {report['summary']['total_dependencies']}")
        print(f"Errors: {report['summary']['errors']}")
        print(f"Warnings: {report['summary']['warnings']}")
        print(f"Critical Issues: {report['summary']['critical_issues']}")
        
        # Print violations
        if report['violations']['circular']:
            print("\n" + "-"*80)
            print("CIRCULAR DEPENDENCIES:")
            print("-"*80)
            for v in report['violations']['circular']:
                cycle_str = " -> ".join(v['cycle'])
                print(f"  [{v['severity'].upper()}] {cycle_str}")
        
        if report['violations']['layer']:
            print("\n" + "-"*80)
            print("LAYER VIOLATIONS:")
            print("-"*80)
            for v in report['violations']['layer'][:10]:  # Limit output
                print(f"  [{v['severity'].upper()}] {v['from']} -> {v['to']}")
                print(f"    {v['reason']}")
        
        if report['violations']['excessive']:
            print("\n" + "-"*80)
            print("EXCESSIVE DEPENDENCIES:")
            print("-"*80)
            for v in report['violations']['excessive'][:10]:
                print(f"  [{v['severity'].upper()}] {v['module']}")
                print(f"    Has {v['count']} deps, max allowed: {v['max_allowed']}")
        
        if report['violations']['critical']:
            print("\n" + "-"*80)
            print("CRITICAL MODULE ISSUES:")
            print("-"*80)
            for v in report['violations']['critical']:
                print(f"  [{v['severity'].upper()}] {v['module']}")
                print(f"    {v['issue']}")
        
        print("\n" + "="*80)
    
    def save_report(self, report: Dict, output_path: Path) -> None:
        """Save report to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {output_path}")
    
    def determine_exit_code(self, report: Dict) -> int:
        """Determine appropriate exit code based on violations."""
        if report['summary']['critical_issues'] > 0:
            return 4
        
        has_circular = len(report['violations']['circular']) > 0
        has_layer = len(report['violations']['layer']) > 0
        has_excessive = len(report['violations']['excessive']) > 0
        
        # Check if we should fail on these
        fail_circular = has_circular and CI_CONFIG['fail_on_circular']
        fail_layer = has_layer and CI_CONFIG['fail_on_layer_violations']
        fail_excessive = has_excessive and CI_CONFIG['fail_on_excessive_deps']
        
        if fail_circular and fail_layer:
            return 4
        elif fail_circular:
            return 1
        elif fail_layer:
            return 2
        elif fail_excessive:
            return 3
        
        # Check warnings limit
        if report['summary']['warnings'] > CI_CONFIG.get('max_warnings', 10):
            if self.strict:
                return 4
        
        return 0


def main():
    """Main entry point for CI linting."""
    parser = argparse.ArgumentParser(
        description='CI/CD Dependency Linter'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='backend',
        help='Path to analyze (default: backend)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode (warnings also fail the build)'
    )
    parser.add_argument(
        '--output',
        default='reports/dependencies/ci_report.json',
        help='Output report path'
    )
    parser.add_argument(
        '--no-fail',
        action='store_true',
        help='Always exit with 0 (report only mode)'
    )
    
    args = parser.parse_args()
    
    # Run linter
    linter = CILinter(Path(args.path), strict=args.strict)
    report = linter.run_all_checks()
    
    # Print summary
    linter.print_summary(report)
    
    # Save report
    linter.save_report(report, Path(args.output))
    
    # Determine exit code
    if args.no_fail:
        exit_code = 0
    else:
        exit_code = linter.determine_exit_code(report)
    
    if exit_code == 0:
        print("\n✅ All dependency checks passed!")
    else:
        print(f"\n❌ Dependency checks failed with exit code: {exit_code}")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
