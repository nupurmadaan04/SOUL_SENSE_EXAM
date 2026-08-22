"""
CLI tool for filesystem case-sensitivity conflict detection.

Usage:
    python -m app.tools.case_detector_cli --help
    python -m app.tools.case_detector_cli                    # Scan current directory
    python -m app.tools.case_detector_cli --report json       # JSON output
    python -m app.tools.case_detector_cli --git-staged        # Check staged files only
    python -m app.tools.case_detector_cli --output report.json
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from app.tools.case_sensitivity_detector import (
    scan_directory,
    check_git_staged_files,
    generate_report,
    format_report_text
)


def main(argv: Optional[list] = None) -> int:
    """
    Main CLI entry point.
    
    Args:
        argv: Command-line arguments (for testing)
    
    Returns:
        Exit code (0 = success, 1 = conflicts found)
    """
    parser = argparse.ArgumentParser(
        description='Detect case-sensitivity filename conflicts'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory to scan (default: current directory)'
    )
    parser.add_argument(
        '--git-staged',
        action='store_true',
        help='Check only staged Git files (faster for pre-commit)'
    )
    parser.add_argument(
        '--report',
        choices=['text', 'json'],
        default='text',
        help='Report format (default: text)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save report to file (optional)'
    )
    
    args = parser.parse_args(argv)
    
    # Scan for conflicts
    if args.git_staged:
        conflicts = check_git_staged_files(args.path)
    else:
        conflicts = scan_directory(args.path)
    
    # Generate report
    report = generate_report(conflicts)
    
    # Format and output
    if args.report == 'json':
        output = json.dumps(report, indent=2)
    else:
        output = format_report_text(report)
    
    print(output)
    
    # Save to file if requested
    if args.output:
        Path(args.output).write_text(output)
        print(f"\nReport saved to: {args.output}")
    
    # Return appropriate exit code
    return 1 if report['status'] == 'FAILED' else 0


if __name__ == '__main__':
    sys.exit(main())
