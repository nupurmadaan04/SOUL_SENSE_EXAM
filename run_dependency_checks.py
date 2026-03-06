"""
Quick Start Script for Dependency Analysis

Provides an easy-to-use interface for running dependency checks.
"""

import sys
import argparse
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from dependency_analyzer import DependencyAnalyzer  # type: ignore
from ci_dependency_lint import CILinter  # type: ignore
from dependency_visualizer import DependencyVisualizer  # type: ignore


def quick_check(path: str = 'backend'):
    """Quick dependency check - reports issues without failing."""
    print("[*] Quick Dependency Check")
    print("=" * 80)
    print(f"Analyzing: {path}")
    print()
    
    analyzer = DependencyAnalyzer(Path(path))
    analyzer.scan_directory()
    analyzer.build_graph()
    
    report = analyzer.generate_report()
    
    # Print summary
    print(f"[i] Summary:")
    print(f"   Modules: {report['summary']['total_modules']}")
    print(f"   Dependencies: {report['summary']['total_dependencies']}")
    print(f"   Average: {report['summary']['average_dependencies']}")
    print()
    
    # Circular dependencies
    if report['circular_dependencies']:
        print(f"[!] Found {len(report['circular_dependencies'])} circular dependencies:")
        for dep in report['circular_dependencies'][:5]:
            cycle = ' -> '.join(dep['cycle'])
            print(f"   - {cycle}")
        if len(report['circular_dependencies']) > 5:
            print(f"   ... and {len(report['circular_dependencies']) - 5} more")
    else:
        print("[+] No circular dependencies")
    
    print()
    
    # Layer violations
    if report['layer_violations']:
        print(f"[!] Found {len(report['layer_violations'])} layer violations")
    else:
        print("[+] No layer violations")
    
    print()
    print("=" * 80)


def full_analysis(path: str = 'backend', output: str = 'dependency_report'):
    """Full analysis with report and visualization."""
    print("[*] Full Dependency Analysis")
    print("=" * 80)
    
    analyzer = DependencyAnalyzer(Path(path))
    analyzer.scan_directory()
    analyzer.build_graph()
    
    # Generate report
    report = analyzer.generate_report()
    circular_deps = analyzer.detect_circular_dependencies()
    
    # Save JSON report
    import json
    report_file = Path(f"{output}_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"[+] Report saved: {report_file}")
    
    # Generate visualizations
    visualizer = DependencyVisualizer(analyzer)
    
    # DOT file
    dot_file = Path(f"{output}.dot")
    visualizer.generate_dot_with_highlights(dot_file, circular_deps)
    print(f"[+] Graph saved: {dot_file}")
    
    # Try to generate SVG
    svg_file = visualizer.dot_to_svg(dot_file)
    if svg_file:
        print(f"[+] SVG saved: {svg_file}")
    
    # HTML report
    html_file = Path(f"{output}.html")
    visualizer.generate_html_visualization(html_file, report)
    print(f"[+] HTML report saved: {html_file}")
    
    print()
    print("=" * 80)
    print("[+] Analysis complete!")
    print(f"\nView HTML report: file://{html_file.absolute()}")


def ci_check(path: str = 'backend', strict: bool = False):
    """CI/CD mode - fails on violations."""
    print("[*] CI/CD Dependency Check")
    print("=" * 80)
    
    linter = CILinter(Path(path), strict=strict)
    report = linter.run_all_checks()
    
    linter.print_summary(report)
    
    # Save report
    output_file = Path('reports/dependencies/ci_report.json')
    linter.save_report(report, output_file)
    
    # Determine exit
    exit_code = linter.determine_exit_code(report)
    
    if exit_code == 0:
        print("\n[+] All checks passed!")
    else:
        print(f"\n[-] Checks failed (exit code: {exit_code})")
        print("\nTo fix circular dependencies:")
        print("  1. Review the cycles listed above")
        print("  2. Use dependency injection")
        print("  3. Create shared models/interfaces")
        print("  4. Refactor to break the cycles")
    
    return exit_code


def interactive_menu():
    """Interactive menu for users."""
    while True:
        print("\n" + "=" * 80)
        print("[*] DEPENDENCY ANALYSIS TOOL")
        print("=" * 80)
        print("\nWhat would you like to do?\n")
        print("  1. Quick Check (backend)")
        print("  2. Quick Check (app)")
        print("  3. Full Analysis with Visualization (backend)")
        print("  4. Full Analysis with Visualization (app)")
        print("  5. CI/CD Check (backend)")
        print("  6. CI/CD Check (app)")
        print("  7. Run Tests")
        print("  8. Exit")
        print()
        
        choice = input("Enter choice (1-8): ").strip()
        
        if choice == '1':
            quick_check('backend')
        elif choice == '2':
            quick_check('app')
        elif choice == '3':
            full_analysis('backend', 'backend_deps')
        elif choice == '4':
            full_analysis('app', 'app_deps')
        elif choice == '5':
            ci_check('backend')
        elif choice == '6':
            ci_check('app')
        elif choice == '7':
            print("\nRunning tests...")
            import subprocess
            subprocess.run(['python', '-m', 'pytest', 'tests/test_dependency_analyzer.py', '-v'])
        elif choice == '8':
            print("\n[*] Goodbye!")
            break
        else:
            print("\n[-] Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Quick Start Script for Dependency Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dependency_checks.py quick backend
  python run_dependency_checks.py full backend --output my_report
  python run_dependency_checks.py ci backend --strict
  python run_dependency_checks.py interactive
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['quick', 'full', 'ci', 'interactive'],
        default='interactive',
        help='Analysis mode'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='backend',
        help='Path to analyze (default: backend)'
    )
    parser.add_argument(
        '--output',
        default='dependency_report',
        help='Output file name (for full mode)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode for CI (warnings also fail)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'quick':
            quick_check(args.path)
        elif args.mode == 'full':
            full_analysis(args.path, args.output)
        elif args.mode == 'ci':
            exit_code = ci_check(args.path, args.strict)
            sys.exit(exit_code)
        elif args.mode == 'interactive':
            interactive_menu()
    except KeyboardInterrupt:
        print("\n\n[*] Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
