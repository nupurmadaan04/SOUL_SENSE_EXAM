"""
Query Plan Regression Detector - CLI Tools

Provides command-line interface for monitoring and managing query plan regressions.

Usage:
    python -m scripts.query_plan_tools register-baseline --query-id user_scores --sql "SELECT * FROM scores WHERE user_id = ?" --expected-time-ms 10
    python -m scripts.query_plan_tools check-regressions --threshold 15
    python -m scripts.query_plan_tools generate-report
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infra.query_plan_regression_detector import QueryPlanRegressionDetector, Severity


def format_report(report: dict) -> str:
    """Format report for console display."""
    lines = [
        "=" * 70,
        "Query Plan Regression Detector - Report",
        "=" * 70,
        "",
        f"Monitored Queries:        {report['total_queries_monitored']}",
        f"Recent Alerts (24h):      {report['recent_alerts_24h']}",
        f"  ├─ Critical:            {report['critical_alerts']}",
        f"  ├─ Warning:             {report['warning_alerts']}",
        f"  └─ Info:                {report['info_alerts']}",
        "",
    ]

    if report['most_regressed_queries']:
        lines.extend([
            "Top Regressed Queries:",
            "-" * 70,
        ])
        for i, query in enumerate(report['most_regressed_queries'], 1):
            severity_icon = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(query['severity'], '⚪')
            
            lines.append(
                f"{i}. {query['query_id']:30s} {query['variance']:>8s}  "
                f"{severity_icon} [{query['type']}]"
            )
        lines.extend(["", "=" * 70])
    else:
        lines.append("✅ No regressions detected!")
        lines.append("=" * 70)

    return "\n".join(lines)


def cmd_register_baseline(args) -> int:
    """Register a baseline for a query."""
    detector = QueryPlanRegressionDetector()

    try:
        # Try to get actual database connection if db path provided
        if args.db:
            conn = sqlite3.connect(args.db)
        else:
            # Fallback to memory for testing
            conn = sqlite3.connect(':memory:')

        success = detector.register_baseline(
            query_id=args.query_id,
            sql=args.sql,
            connection=conn,
            expected_time_ms=args.expected_time_ms,
            row_count=args.row_count or 0
        )

        if not args.db:
            conn.close()

        if success:
            print(f"✅ Baseline registered for query '{args.query_id}'")
            print(f"   Expected Time: {args.expected_time_ms}ms")
            return 0
        else:
            print(f"❌ Failed to register baseline")
            return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_check_regressions(args) -> int:
    """Check all baselines for regressions (requires executing queries)."""
    detector = QueryPlanRegressionDetector()

    baselines = detector.list_baselines()
    if not baselines:
        print("ℹ️  No baselines registered yet")
        return 0

    print(f"Checking {len(baselines)} baselines for regressions...")
    print("-" * 70)

    try:
        if args.db:
            conn = sqlite3.connect(args.db)
        else:
            conn = sqlite3.connect(':memory:')

        regression_count = 0
        for baseline in baselines:
            try:
                # Get current plan
                cursor = conn.cursor()
                cursor.execute(f"EXPLAIN QUERY PLAN {baseline.sql_text}")
                current_plan = str(cursor.fetchall())

                # Detect regression
                alert = detector.detect_regression(
                    query_id=baseline.query_id,
                    current_time_ms=baseline.baseline_time_ms,  # Would be measured in real scenario
                    current_plan=current_plan,
                    threshold_percent=args.threshold
                )

                if alert:
                    regression_count += 1
                    severity_icon = {
                        'critical': '🔴',
                        'warning': '🟡',
                        'info': '🔵'
                    }.get(alert.severity.value, '⚪')
                    
                    print(
                        f"{severity_icon} {baseline.query_id:30s} "
                        f"{alert.variance_percent:+6.1f}% "
                        f"[{alert.regression_type}]"
                    )

            except Exception as e:
                print(f"⚠️  {baseline.query_id:30s} Error: {str(e)[:40]}")

        if not args.db:
            conn.close()

        print("-" * 70)
        print(f"✅ Check complete: {regression_count} regressions detected")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_generate_report(args) -> int:
    """Generate and display regression report."""
    detector = QueryPlanRegressionDetector()

    try:
        report = detector.generate_report()

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(format_report(report))

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_list_baselines(args) -> int:
    """List all registered baselines."""
    detector = QueryPlanRegressionDetector()

    baselines = detector.list_baselines()

    if not baselines:
        print("ℹ️  No baselines registered")
        return 0

    print(f"\n{'Query ID':<30s} {'Table(s)':<20s} {'Baseline (ms)':<15s} {'Uses Index':<12s}")
    print("-" * 80)

    for baseline in baselines:
        tables = ", ".join(baseline.table_names) if baseline.table_names else "unknown"
        index_status = "✅" if baseline.uses_index else "❌"

        print(
            f"{baseline.query_id:<30s} {tables:<20s} "
            f"{baseline.baseline_time_ms:<15.2f} {index_status:<12s}"
        )

    print()
    return 0


def cmd_timeline(args) -> int:
    """Show regression timeline for a query."""
    detector = QueryPlanRegressionDetector()

    alerts = detector.get_alerts_for_query(args.query_id)

    if not alerts:
        print(f"ℹ️  No alerts for query '{args.query_id}'")
        return 0

    print(f"Regression Timeline for '{args.query_id}':\n")

    for alert in sorted(alerts, key=lambda a: a.timestamp):
        severity_icon = {
            'critical': '🔴',
            'warning': '🟡',
            'info': '🔵'
        }.get(alert.severity.value, '⚪')

        print(
            f"{severity_icon} [{alert.timestamp}] {alert.regression_type}\n"
            f"   {alert.details}\n"
            f"   Variance: {alert.variance_percent:+.1f}%\n"
        )

    return 0


def cmd_reset_baseline(args) -> int:
    """Reset a baseline."""
    detector = QueryPlanRegressionDetector()

    if detector.reset_baseline(args.query_id):
        print(f"✅ Baseline reset for query '{args.query_id}'")
        return 0
    else:
        print(f"❌ Query '{args.query_id}' not found")
        return 1


def cmd_clear_alerts(args) -> int:
    """Clear old alerts."""
    detector = QueryPlanRegressionDetector()

    removed = detector.clear_old_alerts(days=args.days)
    print(f"✅ Removed {removed} alerts older than {args.days} days")
    return 0


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query Plan Regression Detector - CLI Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Register baseline
    p_register = subparsers.add_parser('register-baseline', help='Register a query baseline')
    p_register.add_argument('--query-id', required=True, help='Unique query identifier')
    p_register.add_argument('--sql', required=True, help='SQL query text')
    p_register.add_argument('--expected-time-ms', type=float, required=True, help='Expected execution time (ms)')
    p_register.add_argument('--row-count', type=int, default=0, help='Expected row count')
    p_register.add_argument('--db', help='Database file path (optional)')
    p_register.set_defaults(func=cmd_register_baseline)

    # Check regressions
    p_check = subparsers.add_parser('check-regressions', help='Check baselines for regressions')
    p_check.add_argument('--threshold', type=float, default=10, help='Regression threshold percentage (default: 10)')
    p_check.add_argument('--db', help='Database file path (optional)')
    p_check.set_defaults(func=cmd_check_regressions)

    # Generate report
    p_report = subparsers.add_parser('generate-report', help='Generate regression report')
    p_report.add_argument('--json', action='store_true', help='Output as JSON')
    p_report.set_defaults(func=cmd_generate_report)

    # List baselines
    p_list = subparsers.add_parser('list-baselines', help='List all registered baselines')
    p_list.set_defaults(func=cmd_list_baselines)

    # Timeline
    p_timeline = subparsers.add_parser('timeline', help='Show regression timeline for a query')
    p_timeline.add_argument('--query-id', required=True, help='Query identifier')
    p_timeline.set_defaults(func=cmd_timeline)

    # Reset baseline
    p_reset = subparsers.add_parser('reset-baseline', help='Reset a baseline')
    p_reset.add_argument('--query-id', required=True, help='Query identifier to reset')
    p_reset.set_defaults(func=cmd_reset_baseline)

    # Clear alerts
    p_clear = subparsers.add_parser('clear-alerts', help='Clear old alerts')
    p_clear.add_argument('--days', type=int, default=30, help='Clear alerts older than N days')
    p_clear.set_defaults(func=cmd_clear_alerts)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
