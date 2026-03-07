"""
CLI Tools for Shadow Table Swap Validation

Provides command-line interface for operators to validate shadow table swaps.

Usage:
    python shadow_table_tools.py pre-swap --original users --shadow users_new
    python shadow_table_tools.py post-swap --backup users_old --active users
    python shadow_table_tools.py compare-schema --table1 users --table2 users_new
    python shadow_table_tools.py rollback-plan --original users --shadow users_old
"""

import sys
import argparse
import json
from dataclasses import asdict
from sqlalchemy import create_engine

from app.infra.shadow_table_swap_validator import ShadowTableSwapValidator


def format_result(title: str, passed: bool, details: str = "") -> None:
    """Format and print result with emoji indicator."""
    status = "✓ PASS" if passed else "✗ FAIL"
    emoji = "🟢" if passed else "🔴"

    print(f"\n{emoji} {title}: {status}")
    if details:
        print(f"   {details}")


def cmd_pre_swap(args) -> int:
    """Validate tables before swap."""
    engine = create_engine(args.database_url)
    validator = ShadowTableSwapValidator(engine)

    print(f"\nValidating swap: {args.original} → {args.shadow}")
    print("-" * 60)

    result = validator.validate_pre_swap(args.original, args.shadow)

    # Schema validation
    format_result(
        "Schema Validation",
        result.schema_valid,
        f"{len(result.schema_comparison.original_columns)} columns"
        if result.schema_comparison
        else ""
    )

    # Data validation
    if result.data_metrics:
        format_result(
            "Data Integrity",
            result.data_valid,
            f"{result.data_metrics.original_row_count} rows"
        )

    # FK validation
    format_result(
        "Foreign Key Safety",
        result.fk_safe,
        f"{len(result.fk_errors)} FK errors" if result.fk_errors else "All FKs valid"
    )

    # Overall result
    print("\n" + "=" * 60)
    if result.passed:
        print("✅ All validations passed - SAFE TO SWAP")
    else:
        print("❌ Validation failed - DO NOT SWAP")
        if result.recommendations:
            print("\nRecommendations:")
            for rec in result.recommendations:
                print(f"  • {rec}")

    print("=" * 60)

    return 0 if result.passed else 1


def cmd_post_swap(args) -> int:
    """Validate tables after swap."""
    engine = create_engine(args.database_url)
    validator = ShadowTableSwapValidator(engine)

    print(f"\nValidating swap completed: {args.backup} → {args.active}")
    print("-" * 60)

    result = validator.validate_post_swap(args.backup, args.active)

    format_result("Post-Swap Validation", result.passed)

    print("\n" + "=" * 60)
    if result.passed:
        print(f"✅ Swap successful - '{args.active}' is now active")
        print(f"   Backup: '{args.backup}'")
    else:
        print("❌ Post-swap validation failed")
        if result.error_message:
            print(f"   Error: {result.error_message}")

    print("=" * 60)

    return 0 if result.passed else 1


def cmd_compare_schema(args) -> int:
    """Compare schemas of two tables."""
    engine = create_engine(args.database_url)
    validator = ShadowTableSwapValidator(engine)

    print(f"\nComparing schemas: {args.table1} vs {args.table2}")
    print("-" * 60)

    result = validator.compare_schemas(args.table1, args.table2)

    format_result("Schema Comparison", result.passed)

    if not result.passed:
        if result.missing_columns:
            print(f"\n  Missing in {args.table2}: {result.missing_columns}")
        if result.extra_columns:
            print(f"  Extra in {args.table2}: {result.extra_columns}")
        if result.type_mismatches:
            print(f"\n  Type mismatches:")
            for col, (t1, t2) in result.type_mismatches.items():
                print(f"    {col}: {t1} vs {t2}")

    return 0 if result.passed else 1


def cmd_rollback_plan(args) -> int:
    """Generate rollback instructions."""
    print(f"\nGenerating rollback plan: {args.shadow} → {args.original}")
    print("-" * 60)

    print("\n📋 Rollback Instructions:")
    print(f"\n  1. Verify backup table exists: {args.shadow}")
    print(f"  2. Rename active table to temporary: {args.original} → {args.original}_current")
    print(f"  3. Restore from backup: {args.shadow} → {args.original}")
    print(f"  4. Validate data checksums match before/after")
    print(f"  5. Archive current table: {args.original}_current → {args.original}_archive")

    print("\n📝 SQL Commands:")
    print(f"\n  -- Step 1: Rename current table to backup")
    print(f"  ALTER TABLE \"{args.original}\" RENAME TO \"{args.original}_current\";")
    print(f"\n  -- Step 2: Rename shadow table to original")
    print(f"  ALTER TABLE \"{args.shadow}\" RENAME TO \"{args.original}\";")
    print(f"\n  -- Step 3: Keep current for audit (optional cleanup later)")
    print(f"  -- Archive {args.original}_current after verification")

    print("\n" + "-" * 60)
    print("⚠️  Always verify data integrity before finalizing rollback!")
    print("-" * 60)

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Shadow Table Swap Validation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pre-swap validation
  python shadow_table_tools.py pre-swap \\
      --original users \\
      --shadow users_new \\
      --database-url sqlite:///data/soulsense.db

  # Post-swap validation
  python shadow_table_tools.py post-swap \\
      --backup users_old \\
      --active users \\
      --database-url sqlite:///data/soulsense.db

  # Compare schemas
  python shadow_table_tools.py compare-schema \\
      --table1 users \\
      --table2 users_new \\
      --database-url sqlite:///data/soulsense.db
        """,
    )

    parser.add_argument(
        "--database-url",
        default="sqlite:///data/soulsense.db",
        help="Database URL (default: sqlite:///data/soulsense.db)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Pre-swap command
    pre_swap = subparsers.add_parser(
        "pre-swap",
        help="Validate tables before swap"
    )
    pre_swap.add_argument("--original", required=True, help="Original table name")
    pre_swap.add_argument("--shadow", required=True, help="Shadow table name")
    pre_swap.set_defaults(func=cmd_pre_swap)

    # Post-swap command
    post_swap = subparsers.add_parser(
        "post-swap",
        help="Validate tables after swap"
    )
    post_swap.add_argument("--backup", required=True, help="Backup table name (original renamed)")
    post_swap.add_argument("--active", required=True, help="Active table name (shadow renamed)")
    post_swap.set_defaults(func=cmd_post_swap)

    # Compare schema command
    compare = subparsers.add_parser(
        "compare-schema",
        help="Compare schemas of two tables"
    )
    compare.add_argument("--table1", required=True, help="First table name")
    compare.add_argument("--table2", required=True, help="Second table name")
    compare.set_defaults(func=cmd_compare_schema)

    # Rollback plan command
    rollback = subparsers.add_parser(
        "rollback-plan",
        help="Generate rollback instructions"
    )
    rollback.add_argument(
        "--original",
        required=True,
        help="Original table name (now active)"
    )
    rollback.add_argument(
        "--shadow",
        required=True,
        help="Shadow/backup table name"
    )
    rollback.set_defaults(func=cmd_rollback_plan)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
