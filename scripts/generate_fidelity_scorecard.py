#!/usr/bin/env python3
"""
Test Environment Fidelity Scorecard Generator - Issue #1315

Generates a fidelity scorecard from test metrics.
Usage:
    python scripts/generate_fidelity_scorecard.py
    python scripts/generate_fidelity_scorecard.py --output scorecard.json
    python scripts/generate_fidelity_scorecard.py --html scorecard.html
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.metrics import get_collector


def generate_text_report(report: dict) -> str:
    """Generate text scorecard report."""
    lines = [
        "=" * 70,
        "TEST ENVIRONMENT FIDELITY SCORECARD",
        "=" * 70,
        "",
        f"Generated: {datetime.utcnow().isoformat()}",
        f"Overall Fidelity Score: {report['overall_score']}/100",
        f"Status: {'✓ PASS' if report['passed'] else '✗ FAIL'} (threshold: 75.0)",
        "",
        "SCORE BREAKDOWN:",
        f"  Unit Tests:          {report['score_breakdown']['unit_tests']:.1f}%",
        f"  Integration Tests:   {report['score_breakdown']['integration_tests']:.1f}%",
        f"  Edge Cases:          {report['score_breakdown']['edge_cases']:.1f}%",
        f"  Reproducibility:     {report['score_breakdown']['reproducibility']:.1f}%",
        "",
        "TEST EXECUTION STATS:",
        f"  Total Tests:         {report['stats']['total_tests']}",
        f"  Passed:              {report['stats']['total_passed']}",
        f"  Failed:              {report['stats']['total_failed']}",
        f"  Pass Rate:           {report['stats']['pass_rate']:.2f}%",
        f"  Avg Duration:        {report['stats']['avg_duration_ms']:.2f}ms",
        "",
        "BY CATEGORY:",
    ]
    
    for cat, data in report['stats'].get('by_category', {}).items():
        lines.append(f"  {cat.upper()}:")
        lines.append(f"    Total:    {data['total']}")
        lines.append(f"    Passed:   {data['passed']}")
        lines.append(f"    Failed:   {data['failed']}")
        lines.append(f"    Pass Rate: {data['pass_rate']:.2f}%")
    
    lines.extend([
        "",
        "=" * 70,
        "ACCEPTANCE CRITERIA:",
        "  ✓ All CI checks pass" if not report['stats']['total_failed'] else "  ✗ CI checks failing",
        "  ✓ Behavior documented and reproducible" if report['score_breakdown']['reproducibility'] == 100 else "  ✗ Reproducibility issues",
        "  ✓ Tests cover edge cases" if report['score_breakdown']['edge_cases'] >= 75 else "  ✗ Edge case coverage gaps",
        "  ✓ Deterministic results" if report['score_breakdown']['reproducibility'] == 100 else "  ✗ Non-deterministic results",
        "",
        "=" * 70,
    ])
    
    return "\n".join(lines)


def generate_html_report(report: dict) -> str:
    """Generate HTML scorecard report."""
    status_color = "#27ae60" if report['passed'] else "#e74c3c"
    status_text = "PASS" if report['passed'] else "FAIL"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Environment Fidelity Scorecard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; margin-top: 0; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
        .score {{ font-size: 48px; font-weight: bold; color: {status_color}; text-align: center; margin: 20px 0; }}
        .status {{ text-align: center; font-size: 24px; color: {status_color}; margin: 10px 0; }}
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #ecf0f1; padding: 15px; border-radius: 5px; }}
        .stat-label {{ font-weight: bold; color: #34495e; }}
        .stat-value {{ font-size: 28px; color: #2c3e50; margin-top: 5px; }}
        .category {{ margin: 15px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #3498db; }}
        .category-name {{ font-weight: bold; color: #2980b9; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{ background: #34495e; color: white; }}
        tr:hover {{ background: #f8f9fa; }}
        .pass {{ color: #27ae60; }}
        .fail {{ color: #e74c3c; }}
        .timestamp {{ color: #7f8c8d; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Environment Fidelity Scorecard</h1>
        <p class="timestamp">Generated: {datetime.utcnow().isoformat()}</p>
        
        <div class="score">{report['overall_score']}/100</div>
        <div class="status"><span class="{('pass' if report['passed'] else 'fail')}">{status_text}</span></div>
        
        <h2>Score Breakdown</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-label">Unit Tests</div>
                <div class="stat-value">{report['score_breakdown']['unit_tests']:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Integration Tests</div>
                <div class="stat-value">{report['score_breakdown']['integration_tests']:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Edge Cases</div>
                <div class="stat-value">{report['score_breakdown']['edge_cases']:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Reproducibility</div>
                <div class="stat-value">{report['score_breakdown']['reproducibility']:.1f}%</div>
            </div>
        </div>
        
        <h2>Test Execution Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Tests</td>
                <td>{report['stats']['total_tests']}</td>
            </tr>
            <tr>
                <td>Passed</td>
                <td class="pass">{report['stats']['total_passed']}</td>
            </tr>
            <tr>
                <td>Failed</td>
                <td class="{'fail' if report['stats']['total_failed'] > 0 else 'pass'}">{report['stats']['total_failed']}</td>
            </tr>
            <tr>
                <td>Pass Rate</td>
                <td>{report['stats']['pass_rate']:.2f}%</td>
            </tr>
            <tr>
                <td>Avg Duration</td>
                <td>{report['stats']['avg_duration_ms']:.2f}ms</td>
            </tr>
        </table>
        
        <h2>By Category</h2>
"""
    
    for cat, data in report['stats'].get('by_category', {}).items():
        html += f"""
        <div class="category">
            <div class="category-name">{cat.upper()}</div>
            <table style="font-size: 14px; margin: 10px 0 0 0;">
                <tr>
                    <td>Total: {data['total']}</td>
                    <td>Passed: <span class="pass">{data['passed']}</span></td>
                    <td>Failed: <span class="{'fail' if data['failed'] > 0 else 'pass'}">{data['failed']}</span></td>
                    <td>Pass Rate: {data['pass_rate']:.2f}%</td>
                </tr>
            </table>
        </div>
"""
    
    html += """
        <h2>Acceptance Criteria</h2>
        <table>
            <tr>
                <th>Criterion</th>
                <th>Status</th>
            </tr>
"""
    
    criteria = [
        ("All CI checks pass", "pass" if not report['stats']['total_failed'] else "fail"),
        ("Behavior documented & reproducible", "pass" if report['score_breakdown']['reproducibility'] == 100 else "fail"),
        ("Edge cases covered", "pass" if report['score_breakdown']['edge_cases'] >= 75 else "fail"),
        ("Deterministic results", "pass" if report['score_breakdown']['reproducibility'] == 100 else "fail"),
    ]
    
    for criterion, status in criteria:
        symbol = "✓" if status == "pass" else "✗"
        html += f'<tr><td>{criterion}</td><td class="{status}">{symbol}</td></tr>\n'
    
    html += """
        </table>
    </div>
</body>
</html>
"""
    return html


def main():
    parser = argparse.ArgumentParser(description="Generate test environment fidelity scorecard")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: stdout)")
    parser.add_argument("--html", help="Output HTML file path")
    parser.add_argument("--text", "-t", action="store_true", help="Output as text (default: JSON)")
    parser.add_argument("--demo", action="store_true", help="Generate demo scorecard with sample data")
    
    args = parser.parse_args()
    
    # Get metrics from collector
    collector = get_collector()
    
    # If no metrics and not demo mode, try to get from tests
    if not collector.metrics and not args.demo:
        print("No metrics collected. Run 'pytest tests/test_environment_fidelity.py' first, or use --demo flag.")
        return 1
    
    # If demo mode, create sample metrics
    if args.demo and not collector.metrics:
        collector.record("test_unit_1", "unit", True, 2.5)
        collector.record("test_unit_2", "unit", True, 1.8)
        collector.record("test_integration_1", "integration", True, 5.2)
        collector.record("test_edge_1", "edge_case", True, 3.1)
        collector.record("test_edge_2", "edge_case", True, 2.9)
        collector.record("test_race_1", "edge_case", True, 4.5)
    
    report = collector.export_report()
    
    # Default to JSON output if no format specified
    if args.text:
        output = generate_text_report(report)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"[OK] Text scorecard written to {args.output}")
        else:
            print(output)
    
    if args.html:
        html_output = generate_html_report(report)
        with open(args.html, "w") as f:
            f.write(html_output)
        print(f"[OK] HTML scorecard written to {args.html}")
    
    if not args.text and not args.html:
        # Default JSON output
        json_output = json.dumps(report, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(json_output)
            print(f"[OK] Scorecard written to {args.output}")
        else:
            print(json_output)
    
    # Print summary to stdout
    status = "PASS" if report['passed'] else "FAIL"
    print(f"\nSummary: Overall Score {report['overall_score']}/100 - {status}")
    return 0 if report['passed'] else 1


if __name__ == "__main__":
    sys.exit(main())
