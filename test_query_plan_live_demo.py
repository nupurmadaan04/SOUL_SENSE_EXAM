"""
Query Plan Regression Detector - Live Demonstration

This script demonstrates the detector in action with real queries.

Run with: python test_query_plan_live_demo.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.infra.query_plan_regression_detector import QueryPlanRegressionDetector, Severity


def main():
    """Run live demonstration."""
    print("=" * 70)
    print("Query Plan Regression Detector - Live Demonstration")
    print("=" * 70)
    print()

    # Create test database
    test_db = Path(__file__).parent / "test_demo.db"
    conn = sqlite3.connect(str(test_db))
    cursor = conn.cursor()

    # Create test tables
    print("📝 Setting up test database...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            value INTEGER,
            timestamp DATETIME
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_scores_user_id ON scores(user_id)')
    conn.commit()

    print("✅ Database created\n")

    # Initialize detector
    detector = QueryPlanRegressionDetector()

    # Register baselines
    print("📋 Registering query baselines...")
    queries = [
        ("user_by_id", "SELECT * FROM users WHERE id = ?", 2.0),
        ("scores_by_user", "SELECT * FROM scores WHERE user_id = ?", 5.0),
        ("all_scores", "SELECT * FROM scores", 8.0),
    ]

    for query_id, sql, expected_time in queries:
        detector.register_baseline(
            query_id=query_id,
            sql=sql,
            connection=conn,
            expected_time_ms=expected_time
        )
        print(f"  ✅ Registered '{query_id}'")

    print()

    # Simulate query performance measurements and detect regressions
    print("🔍 Detecting regressions...")
    print("-" * 70)

    test_cases = [
        ("user_by_id", 2.5, "No regression (within threshold)"),
        ("scores_by_user", 6.5, "WARNING: Time increased 30%"),
        ("all_scores", 12.0, "CRITICAL: Time increased 50%"),
    ]

    for query_id, current_time, description in test_cases:
        alert = detector.detect_regression(
            query_id=query_id,
            current_time_ms=current_time,
            threshold_percent=10.0
        )

        if alert:
            severity_icon = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(alert.severity.value, '⚪')

            print(f"{severity_icon} {query_id:20s} {current_time:6.1f}ms {alert.variance_percent:+6.1f}%  [{alert.severity.value.upper()}]")
        else:
            print(f"✅ {query_id:20s} {current_time:6.1f}ms {' ':10s}  [OK]")

    print()

    # Generate report
    print("📊 Generating report...")
    print("-" * 70)
    report = detector.generate_report()

    print(f"Total Baselines:        {report['total_baselines']}")
    print(f"Recent Alerts (24h):    {report['recent_alerts_24h']}")
    print(f"  ├─ Critical:          {report['critical_alerts']}")
    print(f"  ├─ Warning:           {report['warning_alerts']}")
    print(f"  └─ Info:              {report['info_alerts']}")
    print()

    if report['most_regressed_queries']:
        print("Top Regressed Queries:")
        for i, query in enumerate(report['most_regressed_queries'], 1):
            severity_icon = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(query['severity'], '⚪')

            print(f"  {i}. {query['query_id']:25s} {query['variance']:>8s}  {severity_icon}")
    else:
        print("✅ No regressions detected!")

    print()

    # Show alert timeline
    print("📈 Alert Timeline:")
    print("-" * 70)
    alerts = detector.get_recent_alerts(hours=24)
    for alert in reversed(alerts[-3:]):  # Show last 3 alerts
        severity_icon = {
            'critical': '🔴',
            'warning': '🟡',
            'info': '🔵'
        }.get(alert.severity.value, '⚪')

        print(f"{severity_icon} [{alert.timestamp}] {alert.query_id}")
        print(f"   {alert.details}")
        print()

    # Cleanup
    conn.close()
    test_db.unlink(missing_ok=True)

    print("=" * 70)
    print("✅ Demonstration complete!")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
