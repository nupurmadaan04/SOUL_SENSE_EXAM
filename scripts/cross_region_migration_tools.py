#!/usr/bin/env python
"""
Cross-Region Migration CLI Tools.

Operator commands for managing cross-region migrations:
- plan: Generate execution plan with dependency resolution
- execute: Run migration across regions with safety checks
- status: Monitor real-time progress
- history: View past migrations
- rollback: Reverse failed migrations
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infra.cross_region_migration_sequencer import (
    CrossRegionMigrationSequencer,
    CrossRegionMigrationPlan,
    RegionDefinition,
)
from app.infra.cross_region_migration_registry import (
    get_cross_region_registry,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_regions_config(config_path: str = "config/cross_region_migrations.yaml") -> List[RegionDefinition]:
    """Load regions from config file."""
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        regions = []
        for region_config in config.get("regions", []):
            region = RegionDefinition(
                name=region_config["name"],
                database_url=region_config["database_url"],
                environment=region_config.get("environment", "production"),
                priority=region_config.get("priority", 0),
                replica_of=region_config.get("replica_of"),
                timeout_seconds=region_config.get("timeout_seconds", 120),
            )
            regions.append(region)
        
        return sorted(regions, key=lambda r: r.priority)
    except Exception as e:
        logger.error(f"Failed to load regions config: {e}")
        return []


def cmd_plan(args) -> None:
    """Generate execution plan."""
    version = args.version or "20260307_001"
    regions = load_regions_config()
    
    if not regions:
        logger.error("No regions configured")
        return
    
    sequencer = CrossRegionMigrationSequencer()
    registry = get_cross_region_registry()
    
    # Build dependencies from replica_of relationships
    dependencies = {}
    for region in regions:
        if region.replica_of:
            dependencies[region.name] = [region.replica_of]
        else:
            dependencies[region.name] = []
    
    # Create plan
    plan = CrossRegionMigrationPlan(
        migration_version=version,
        regions=regions,
        dependencies=dependencies,
    )
    
    # Resolve execution order
    order, error = sequencer.resolve_execution_order(plan)
    
    if error:
        logger.error(f"Failed to resolve order: {error}")
        return
    
    plan.execution_order = order
    registry.store_dependency_graph(dependencies)
    
    # Display plan
    print("\n" + "="*60)
    print(f"Cross-Region Migration Plan: {version}")
    print("="*60)
    print(f"\nExecution Order:")
    for idx, region_name in enumerate(order, 1):
        region = next((r for r in regions if r.name == region_name), None)
        if region and region.replica_of:
            print(f"  {idx}. {region_name} (replica of {region.replica_of})")
        else:
            print(f"  {idx}. {region_name} (primary)")
    
    print(f"\nTotal Regions: {len(regions)}")
    print(f"Estimated Duration: ~{len(regions) * 5}s")
    print("\nNext: python scripts/cross_region_migration_tools.py execute --version " + version)
    print("="*60 + "\n")


def cmd_execute(args) -> None:
    """Execute migration across regions."""
    version = args.version or "20260307_001"
    regions = load_regions_config()
    
    if not regions:
        logger.error("No regions configured")
        return
    
    sequencer = CrossRegionMigrationSequencer()
    registry = get_cross_region_registry()
    
    # Build dependencies
    dependencies = {}
    for region in regions:
        if region.replica_of:
            dependencies[region.name] = [region.replica_of]
        else:
            dependencies[region.name] = []
    
    # Create and execute plan
    plan = CrossRegionMigrationPlan(
        migration_version=version,
        regions=regions,
        dependencies=dependencies,
        initiated_by="cli",
    )
    
    # Check if safe to execute
    is_safe, reason = registry.is_migration_safe_to_retry(version)
    if not is_safe:
        logger.error(f"Cannot execute: {reason}")
        return
    
    # Register execution
    registry.register_execution(plan)
    registry.store_dependency_graph(dependencies)
    
    # Execute
    if args.dry_run:
        print(f"\n[DRY-RUN] Would execute migration {version}\n")
        return
    
    result = sequencer.execute_cross_region_migration(plan)
    
    # Log summary
    print("\n" + "="*60)
    print(f"Execution Summary: {version}")
    print("="*60)
    print(f"Status: {result.status.value.upper()}")
    print(f"Started: {result.started_at}")
    print(f"Completed: {result.completed_at}")
    print("="*60 + "\n")


def cmd_status(args) -> None:
    """Check migration status."""
    version = args.version
    registry = get_cross_region_registry()
    
    if not version:
        # Show recent migration
        last = registry.get_last_migration()
        if not last:
            logger.info("No migration history found")
            return
        version = last["migration_version"]
    
    records = registry.get_execution_history(version)
    
    if not records:
        logger.info(f"No execution found for migration {version}")
        return
    
    record = records[-1]
    
    print("\n" + "="*60)
    print(f"Migration Status: {version}")
    print("="*60)
    print(f"Status: {record.get('status', 'unknown').upper()}")
    print(f"Regions: {len(record.get('regions', []))} total")
    print(f"Created: {record.get('created_at')}")
    print(f"Started: {record.get('started_at')}")
    print(f"Completed: {record.get('completed_at')}")
    
    if record.get("steps"):
        print(f"\nRegional Status:")
        for step in record["steps"]:
            status = step.get("status", "unknown")
            symbol = "✓" if status == "completed" else "✗" if status == "failed" else "→"
            print(f"  {symbol} {step['region_name']}: {status}")
    
    print("="*60 + "\n")


def cmd_history(args) -> None:
    """Show migration history."""
    registry = get_cross_region_registry()
    history = registry.get_execution_history()
    
    if not history:
        logger.info("No migration history")
        return
    
    print("\n" + "="*60)
    print("Migration History")
    print("="*60)
    
    for record in history[-10:]:  # Show last 10
        status_symbol = "✓" if record.get("status") == "completed" else "✗"
        print(f"{status_symbol} {record['migration_version']}: {record.get('status')} "
              f"({len(record.get('regions', []))} regions)")
    
    print("="*60 + "\n")


def cmd_rollback(args) -> None:
    """Rollback failed migration."""
    version = args.version
    if not version:
        logger.error("--version required for rollback")
        return
    
    registry = get_cross_region_registry()
    failed_regions = registry.get_failed_regions(version)
    
    if not failed_regions:
        logger.info(f"No failed regions in {version}")
        return
    
    print("\n" + "="*60)
    print(f"Rollback Plan: {version}")
    print("="*60)
    print(f"Failed regions to rollback: {', '.join(failed_regions)}")
    print("Status: Ready for rollback")
    print("="*60 + "\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cross-Region Migration Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/cross_region_migration_tools.py plan --version 20260307_001
  python scripts/cross_region_migration_tools.py execute --version 20260307_001
  python scripts/cross_region_migration_tools.py status --version 20260307_001
  python scripts/cross_region_migration_tools.py history
  python scripts/cross_region_migration_tools.py rollback --version 20260307_001
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Generate execution plan")
    plan_parser.add_argument("--version", help="Migration version", default=None)
    plan_parser.set_defaults(func=cmd_plan)
    
    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Execute migration")
    exec_parser.add_argument("--version", help="Migration version", default=None)
    exec_parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    exec_parser.set_defaults(func=cmd_execute)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check migration status")
    status_parser.add_argument("--version", help="Migration version", default=None)
    status_parser.set_defaults(func=cmd_status)
    
    # History command
    history_parser = subparsers.add_parser("history", help="View migration history")
    history_parser.set_defaults(func=cmd_history)
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback failed migration")
    rollback_parser.add_argument("--version", required=True, help="Migration version to rollback")
    rollback_parser.set_defaults(func=cmd_rollback)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
