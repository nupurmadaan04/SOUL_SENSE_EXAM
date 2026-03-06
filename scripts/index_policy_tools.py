#!/usr/bin/env python3
"""
Online Index Policy CLI Tools

Commands:
  validate-index    - Validate a specific index against policies
  audit-database    - Scan all indexes in database for policy compliance
  check-compatibility - Check if database supports online index creation
"""

import sys
import os
import json
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infra.online_index_policy import (
    validate_index_in_migration,
    DatabaseType,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_index_command(
    db_type: str,
    index_name: str,
    table_name: str,
    columns: str,
    duration: int = 30,
    unique: bool = False
) -> int:
    """
    Validate a specific index.
    
    Example:
        python scripts/index_policy_tools.py validate-index \\
            --db-type postgresql \\
            --index-name ix_users_email \\
            --table-name users \\
            --columns email
    """
    try:
        column_list = [c.strip() for c in columns.split(',')]
        result = validate_index_in_migration(
            db_type=db_type,
            index_name=index_name,
            table_name=table_name,
            columns=column_list,
            estimated_duration_seconds=duration,
            is_unique=unique
        )
        
        # Print result
        print(f"\n{'='*70}")
        print(f"Index Policy Validation Report")
        print(f"{'='*70}")
        print(f"Index:       {result.index_name}")
        print(f"Database:    {result.database_type}")
        print(f"Status:      {'✓ PASS' if result.passed else '✗ FAIL'}")
        print(f"Timestamp:   {result.timestamp}")
        
        if result.checks:
            print(f"\nPolicy Checks ({len(result.checks)}):")
            for check in result.checks:
                status = "✓" if check.passed else "✗"
                print(f"  {status} {check.policy.value}")
                if check.reason:
                    print(f"     {check.reason}")
                if check.recommendation:
                    print(f"     → {check.recommendation}")
        
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  ✗ {error}")
        
        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
        
        if result.recommendations:
            print(f"\nRecommendations ({len(result.recommendations)}):")
            for rec in result.recommendations:
                print(f"  → {rec}")
        
        print(f"\nMetrics:")
        for key, value in result.metrics.items():
            print(f"  {key}: {value}")
        
        print(f"{'='*70}\n")
        
        return 0 if result.passed else 1
    
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"\n✗ Error: {e}\n")
        return 1


def check_compatibility_command(db_type: str) -> int:
    """
    Check database compatibility for online index creation.
    
    Example:
        python scripts/index_policy_tools.py check-compatibility postgresql
    """
    try:
        db_enum = DatabaseType(db_type)
    except ValueError:
        print(f"\n✗ Unknown database type: {db_type}")
        print(f"  Supported: postgresql, mysql, sqlite\n")
        return 1
    
    print(f"\n{'='*70}")
    print(f"Online Index Creation Compatibility Check")
    print(f"{'='*70}\n")
    
    if db_type == "postgresql":
        print("✓ PostgreSQL - Online index creation supported")
        print("  Method:   CREATE INDEX CONCURRENTLY")
        print("  Feature:  No table locks, concurrent writes allowed")
        print("  Syntax:   CREATE INDEX CONCURRENTLY ix_name ON table (columns)")
        print("  Downgrade: DROP INDEX CONCURRENTLY ix_name")
    
    elif db_type == "mysql":
        print("✓ MySQL - Online index creation supported")
        print("  Method:   ALGORITHM=INPLACE with LOCK=NONE")
        print("  Feature:  No locks (MySQL 5.6+), all reads and writes allowed")
        print("  Syntax:   ALTER TABLE table ADD INDEX ix_name (columns),")
        print("            ALGORITHM=INPLACE, LOCK=NONE")
        print("  Downgrade: DROP INDEX ix_name ON table")
    
    elif db_type == "sqlite":
        print("⚠ SQLite - Online index creation NOT supported")
        print("  Limitation: Full table lock during CREATE INDEX")
        print("  Impact:     All reads and writes blocked during index creation")
        print("  Solution:   Schedule index creation during maintenance window")
        print("  Syntax:     CREATE INDEX ix_name ON table (columns)")
        print("  Downgrade:  DROP INDEX ix_name")
    
    print(f"\n{'='*70}\n")
    return 0


def help_command() -> int:
    """Show help message."""
    print(f"""
Online Index Policy CLI Tools

COMMANDS:
  validate-index      Validate a specific index against policies
  check-compatibility Check if database supports online index creation
  help               Show this help message

USAGE EXAMPLES:

  # Validate a PostgreSQL index
  python scripts/index_policy_tools.py validate-index \\
      --db-type postgresql \\
      --index-name ix_users_email \\
      --table-name users \\
      --columns email \\
      --duration 45

  # Validate a unique index
  python scripts/index_policy_tools.py validate-index \\
      --db-type mysql \\
      --index-name ix_orders_code \\
      --table-name orders \\
      --columns order_code \\
      --unique \\
      --duration 120

  # Check compatibility
  python scripts/index_policy_tools.py check-compatibility postgresql
  python scripts/index_policy_tools.py check-compatibility mysql
  python scripts/index_policy_tools.py check-compatibility sqlite

OPTIONS:
  --db-type TYPE      Database type: postgresql, mysql, sqlite (required)
  --index-name NAME   Name of the index (required for validate-index)
  --table-name TABLE  Name of the table (required for validate-index)
  --columns COLS      Comma-separated columns (required for validate-index)
  --duration SECONDS  Estimated index creation duration in seconds (default: 30)
  --unique            Mark index as unique constraint (optional)
  --help              Show this help message
""")
    return 0


def main() -> int:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        return help_command()
    
    command = sys.argv[1]
    
    if command == "help" or command in ["-h", "--help"]:
        return help_command()
    
    elif command == "validate-index":
        # Parse arguments
        kwargs = {}
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--db-type" and i + 1 < len(sys.argv):
                kwargs["db_type"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--index-name" and i + 1 < len(sys.argv):
                kwargs["index_name"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--table-name" and i + 1 < len(sys.argv):
                kwargs["table_name"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--columns" and i + 1 < len(sys.argv):
                kwargs["columns"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--duration" and i + 1 < len(sys.argv):
                kwargs["duration"] = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--unique":
                kwargs["unique"] = True
                i += 1
            else:
                i += 1
        
        # Validate required arguments
        required = ["db_type", "index_name", "table_name", "columns"]
        missing = [k for k in required if k not in kwargs]
        if missing:
            print(f"\n✗ Missing required arguments: {', '.join(missing)}\n")
            return help_command()
        
        return validate_index_command(**kwargs)
    
    elif command == "check-compatibility":
        if len(sys.argv) < 3:
            print("\n✗ Missing database type argument\n")
            return help_command()
        return check_compatibility_command(sys.argv[2])
    
    else:
        print(f"\n✗ Unknown command: {command}\n")
        return help_command()


if __name__ == "__main__":
    sys.exit(main())
