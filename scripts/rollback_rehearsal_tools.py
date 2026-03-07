#!/usr/bin/env python
"""
Schema Rollback Rehearsal CLI Tools

Commands for testing and monitoring migration rollback safety.

Usage:
    python scripts/rollback_rehearsal_tools.py rehearse-pending
    python scripts/rollback_rehearsal_tools.py check-safety <migration-version>
    python scripts/rollback_rehearsal_tools.py metrics
    python scripts/rollback_rehearsal_tools.py history <migration-version>
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.infra.schema_rollback_rehearsal import RollbackRehearsalPipeline
    from app.infra.rollback_rehearsal_registry import get_rollback_rehearsal_registry
except ImportError as e:
    print(f"Error: Cannot import rehearsal modules. {e}")
    sys.exit(1)


def format_result(result):
    """Format a single result line for display."""
    status_emoji = {
        "passed": "✓",
        "warning": "⚠",
        "failed": "❌"
    }
    
    emoji = status_emoji.get(result.status, "?")
    return f"{emoji} {result.migration_version:30} | {result.status:8} | {result.reversibility_score:3}% | {result.duration_up_ms + result.duration_down_ms:6.1f}ms"


def print_table_header():
    """Print table header."""
    print("\n" + "=" * 110)
    print(f"{'Status':<3} {'Migration':<30} | {'Status':<8} | {'Score':<3} | {'Duration':<6}")
    print("-" * 110)


def cmd_rehearse_pending(args):
    """Rehearse all pending migrations."""
    pipeline = RollbackRehearsalPipeline()
    registry = get_rollback_rehearsal_registry()
    
    print("\n🔄 Rehearsing pending migrations...\n")
    
    migrations = pipeline.discover_pending_migrations()
    if not migrations:
        print("✓ No pending migrations to rehearse.\n")
        return 0
    
    print(f"Found {len(migrations)} migrations with downgrade paths.\n")
    
    results, summary = pipeline.rehearse_all_pending()
    
    # Display results table
    print_table_header()
    for r in results:
        print(format_result(r))
    print("=" * 110)
    
    # Display warnings
    has_warnings = False
    for result in results:
        if result.warnings:
            has_warnings = True
            print(f"\n⚠️  {result.migration_version}:")
            for warning in result.warnings:
                print(f"   - {warning}")
    
    # Display summary
    print(f"\n📊 Summary:")
    print(f"   Total: {summary['total']} | Passed: {summary['passed']} | "
          f"Warnings: {summary['warnings']} | Failed: {summary['failed']}")
    print(f"   Average Reversibility: {summary['avg_reversibility']}%")
    
    # Record results
    registry.record_batch(results)
    print(f"\n✓ Rehearsal results recorded to registry\n")
    
    return 0 if summary['failed'] == 0 else 1


def cmd_check_safety(args):
    """Check rollback safety for a specific migration."""
    migration_version = args.migration
    
    pipeline = RollbackRehearsalPipeline()
    
    print(f"\n🔍 Checking rollback safety for {migration_version}...\n")
    
    result = pipeline.rehearse_migration(migration_version)
    
    # Display result
    status_symbol = "✓" if result.status == "passed" else "⚠" if result.status == "warning" else "❌"
    print(f"{status_symbol} Status: {result.status.upper()}")
    print(f"📈 Reversibility Score: {result.reversibility_score}%")
    print(f"⏱️  Duration: {result.duration_up_ms:.1f}ms (up) + {result.duration_down_ms:.1f}ms (down)")
    
    if result.warnings:
        print(f"\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"   - {warning}")
    
    if result.non_reversible_ops:
        print(f"\n❌ Non-Reversible Operations:")
        for op in result.non_reversible_ops:
            print(f"   - {op}")
    
    if result.error_message:
        print(f"\n💥 Error: {result.error_message}")
    
    # Recommendations
    if result.reversibility_score < 75:
        print(f"\n💡 Recommendations:")
        if "DROP" in str(result.non_reversible_ops):
            print("   - Use soft deletes or shadow tables instead of DROP")
        if "DELETE" in str(result.non_reversible_ops):
            print("   - Archive deleted data before executing")
    
    print()
    return 0 if result.status == "passed" else 1


def cmd_metrics(args):
    """Show aggregate rehearsal metrics."""
    registry = get_rollback_rehearsal_registry()
    metrics = registry.get_aggregate_metrics()
    
    print("\n📊 Rollback Rehearsal Metrics\n")
    
    if metrics["total_rehearsals"] == 0:
        print("No rehearsals recorded yet.\n")
        return 0
    
    print(f"Total Rehearsals: {metrics['total_rehearsals']}")
    print(f"Passed: {metrics['passed']} ({metrics['pass_rate']}%)")
    print(f"Warnings: {metrics['warnings']} ({metrics['warning_rate']}%)")
    print(f"Failed: {metrics['failed']} ({metrics['failure_rate']}%)")
    print(f"Average Reversibility: {metrics['avg_reversibility']}%")
    
    if metrics["non_reversible_migrations"]:
        print(f"\n⚠️  Non-Reversible Migrations ({len(metrics['non_reversible_migrations'])}):")
        for migration in sorted(set(metrics['non_reversible_migrations']))[:10]:
            print(f"   - {migration}")
    
    print()
    return 0


def cmd_history(args):
    """Show rehearsal history for a migration."""
    migration_version = args.migration
    registry = get_rollback_rehearsal_registry()
    
    print(f"\n📜 Rehearsal History: {migration_version}\n")
    
    history = registry.get_rehearsal_history(migration_version)
    
    if not history:
        print("No rehearsal history found.\n")
        return 0
    
    # Display history
    print("=" * 100)
    print(f"{'Timestamp':<20} | {'Status':<8} | {'Score':<5} | {'Duration':<10}")
    print("-" * 100)
    
    for record in history:
        timestamp = record.get("timestamp", "?")[:19]
        status = record.get("status", "?")
        score = f"{record.get('reversibility_score', 0)}%"
        duration = f"{record.get('duration_up_ms', 0) + record.get('duration_down_ms', 0):.1f}ms"
        print(f"{timestamp:<20} | {status:<8} | {score:<5} | {duration:<10}")
    
    print("=" * 100)
    print()
    return 0


def cmd_help(args):
    """Show help information."""
    print("""
Schema Rollback Rehearsal Pipeline - CLI Tools

COMMANDS:
    rehearse-pending    Rehearse all pending migrations
                       Example: python scripts/rollback_rehearsal_tools.py rehearse-pending
    
    check-safety        Check rollback safety for specific migration
                       Example: python scripts/rollback_rehearsal_tools.py check-safety 001_create_users
    
    metrics            Show aggregate rehearsal statistics
                       Example: python scripts/rollback_rehearsal_tools.py metrics
    
    history            Show rehearsal history for a migration
                       Example: python scripts/rollback_rehearsal_tools.py history 001_create_users
    
    help               Show this help message

EXAMPLES:
    # Rehearse all pending migrations
    python scripts/rollback_rehearsal_tools.py rehearse-pending
    
    # Check safety of a specific migration before deploying
    python scripts/rollback_rehearsal_tools.py check-safety 003_add_email
    
    # View metrics dashboard
    python scripts/rollback_rehearsal_tools.py metrics
    
    # See history of rehearsals for a migration
    python scripts/rollback_rehearsal_tools.py history 003_add_email

UNDERSTANDING THE OUTPUT:
    ✓ = PASSED       - Migration is reversible
    ⚠ = WARNING      - Migration has reversibility issues
    ❌ = FAILED      - Migration cannot be safely rolled back
    
    Reversibility Score (0-100%):
    - 100%:  Fully reversible, safe to deploy
    - 75-99%: Minor concerns, review before deployment
    - <75%:  Major issues, reconsider migration design

ABOUT THIS TOOL:
    The rollback rehearsal pipeline validates that all migrations can
    be safely reversed before production deployment. This prevents
    catastrophic failures when rollbacks become necessary.
""")
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Schema Rollback Rehearsal Pipeline - Test migration reversibility",
        add_help=False
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # rehearse-pending
    subparsers.add_parser("rehearse-pending", help="Rehearse all pending migrations")
    
    # check-safety
    check_parser = subparsers.add_parser("check-safety", help="Check migration reversibility")
    check_parser.add_argument("migration", help="Migration version to check")
    
    # metrics
    subparsers.add_parser("metrics", help="Show rehearsal metrics")
    
    # history
    history_parser = subparsers.add_parser("history", help="Show rehearsal history")
    history_parser.add_argument("migration", help="Migration version to show history for")
    
    # help
    subparsers.add_parser("help", help="Show help information")
    
    args = parser.parse_args()
    
    # Command mapping
    commands = {
        "rehearse-pending": cmd_rehearse_pending,
        "check-safety": cmd_check_safety,
        "metrics": cmd_metrics,
        "history": cmd_history,
        "help": cmd_help,
    }
    
    if not args.command or args.command not in commands:
        cmd_help(args)
        return 0
    
    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
