"""
Foreign Key Integrity Orphan Scanner (#1414)

Provides comprehensive detection, reporting, and cleanup of orphaned records
- records with foreign keys referencing non-existent parent records.

This tool helps maintain database referential integrity by:
- Scanning tables for orphaned foreign key references
- Reporting orphan statistics and details
- Providing safe cleanup mechanisms
- Supporting dry-run mode for safe testing
- Offering multiple cleanup strategies

Features:
- Automatic foreign key relationship discovery
- Configurable scan scope (specific tables or all)
- Multiple detection strategies (JOIN, NOT EXISTS, LEFT JOIN)
- Safe cleanup with backup/restore capability
- Comprehensive observability and metrics
- Scheduled scanning via Celery tasks

Example:
    from api.utils.orphan_scanner import OrphanScanner, CleanupStrategy
    
    scanner = OrphanScanner(engine)
    
    # Scan for orphans
    report = await scanner.scan_table("responses", "user_id", "users")
    
    # Clean up with dry-run first
    result = await scanner.cleanup_orphans(
        "responses", "user_id", "users",
        strategy=CleanupStrategy.DELETE,
        dry_run=True
    )
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import json

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text, inspect, MetaData, Table, Column, ForeignKey, select, func
from sqlalchemy.engine import reflection

from ..services.db_service import AsyncSessionLocal


logger = logging.getLogger("api.orphan_scanner")


class CleanupStrategy(str, Enum):
    """Strategy for handling orphaned records."""
    DELETE = "delete"  # Permanently delete orphans
    SOFT_DELETE = "soft_delete"  # Mark as deleted
    NULLIFY = "nullify"  # Set FK to NULL (nullable only)
    REPORT_ONLY = "report_only"  # Only report, no action
    ARCHIVE_THEN_DELETE = "archive_then_delete"  # Archive before delete


class ScanStrategy(str, Enum):
    """SQL strategy for detecting orphans."""
    NOT_EXISTS = "not_exists"  # WHERE NOT EXISTS
    LEFT_JOIN = "left_join"  # LEFT JOIN + IS NULL
    EXCEPT_QUERY = "except"  # EXCEPT query (PostgreSQL)


@dataclass
class ForeignKeyRelationship:
    """Represents a foreign key relationship."""
    table_name: str
    column_name: str
    referenced_table: str
    referenced_column: str
    constraint_name: Optional[str] = None
    on_delete: Optional[str] = None
    on_update: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "column_name": self.column_name,
            "referenced_table": self.referenced_table,
            "referenced_column": self.referenced_column,
            "constraint_name": self.constraint_name,
            "on_delete": self.on_delete,
            "on_update": self.on_update,
        }


@dataclass
class OrphanRecord:
    """Represents a single orphaned record."""
    table_name: str
    record_id: Any
    foreign_key_column: str
    foreign_key_value: Any
    referenced_table: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "record_id": self.record_id,
            "foreign_key_column": self.foreign_key_column,
            "foreign_key_value": str(self.foreign_key_value),
            "referenced_table": self.referenced_table,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class ScanResult:
    """Result of an orphan scan operation."""
    table_name: str
    foreign_key_column: str
    referenced_table: str
    orphan_count: int
    sample_orphans: List[OrphanRecord] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    scan_strategy: str = "not_exists"
    error_message: Optional[str] = None
    
    @property
    def has_orphans(self) -> bool:
        return self.orphan_count > 0
    
    @property
    def success(self) -> bool:
        return self.error_message is None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "foreign_key_column": self.foreign_key_column,
            "referenced_table": self.referenced_table,
            "orphan_count": self.orphan_count,
            "sample_orphans": [o.to_dict() for o in self.sample_orphans[:10]],
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "scan_strategy": self.scan_strategy,
            "has_orphans": self.has_orphans,
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    table_name: str
    foreign_key_column: str
    strategy: CleanupStrategy
    orphans_found: int
    orphans_processed: int
    orphans_failed: int
    dry_run: bool
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    backup_table: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and self.orphans_failed == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "foreign_key_column": self.foreign_key_column,
            "strategy": self.strategy.value,
            "orphans_found": self.orphans_found,
            "orphans_processed": self.orphans_processed,
            "orphans_failed": self.orphans_failed,
            "dry_run": self.dry_run,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            "errors": self.errors,
            "backup_table": self.backup_table,
        }


@dataclass
class DatabaseIntegrityReport:
    """Comprehensive database integrity report."""
    scan_time: datetime = field(default_factory=datetime.utcnow)
    tables_scanned: int = 0
    relationships_checked: int = 0
    total_orphans_found: int = 0
    table_results: List[ScanResult] = field(default_factory=list)
    duration_ms: float = 0.0
    
    @property
    def integrity_score(self) -> float:
        """Calculate integrity score (0-100)."""
        if self.relationships_checked == 0:
            return 100.0
        clean_relationships = sum(1 for r in self.table_results if not r.has_orphans)
        return (clean_relationships / self.relationships_checked) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_time": self.scan_time.isoformat(),
            "tables_scanned": self.tables_scanned,
            "relationships_checked": self.relationships_checked,
            "total_orphans_found": self.total_orphans_found,
            "integrity_score": round(self.integrity_score, 2),
            "duration_ms": round(self.duration_ms, 2),
            "table_results": [r.to_dict() for r in self.table_results],
        }


class OrphanScanner:
    """
    Foreign key integrity orphan scanner and cleanup tool.
    
    Provides comprehensive detection and remediation of orphaned
    database records that violate foreign key constraints.
    
    Example:
        scanner = OrphanScanner(engine)
        await scanner.initialize()
        
        # Scan specific relationship
        result = await scanner.scan_table(
            "responses", "user_id", "users"
        )
        
        if result.has_orphans:
            # Clean up orphans
            cleanup = await scanner.cleanup_orphans(
                "responses", "user_id", "users",
                strategy=CleanupStrategy.DELETE,
                dry_run=True  # Test first
            )
    """
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._relationships: List[ForeignKeyRelationship] = []
        self._scan_callbacks: List[Callable[[ScanResult], None]] = []
        self._cleanup_callbacks: List[Callable[[CleanupResult], None]] = []
    
    async def initialize(self) -> None:
        """Initialize scanner and discover relationships."""
        await self._ensure_history_table()
        await self.discover_relationships()
        logger.info(f"OrphanScanner initialized with {len(self._relationships)} relationships")
    
    async def _ensure_history_table(self) -> None:
        """Ensure scan/cleanup history tables exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(self._create_history_tables)
    
    def _create_history_tables(self, conn) -> None:
        """Create history tables (synchronous helper)."""
        metadata = MetaData()
        
        if not inspect(conn).has_table("orphan_scan_history"):
            Table(
                "orphan_scan_history",
                metadata,
                Column("id", Column(Integer, primary_key=True, autoincrement=True)),
                Column("table_name", Column(String, nullable=False, index=True)),
                Column("foreign_key_column", Column(String, nullable=False)),
                Column("referenced_table", Column(String, nullable=False)),
                Column("orphan_count", Column(Integer, default=0)),
                Column("scan_strategy", Column(String)),
                Column("scan_duration_ms", Column(Integer)),
                Column("created_at", Column(datetime, default=datetime.utcnow)),
                Column("details", Column(Text)),
            ).create(conn)
            logger.info("Created orphan_scan_history table")
        
        if not inspect(conn).has_table("orphan_cleanup_history"):
            Table(
                "orphan_cleanup_history",
                metadata,
                Column("id", Column(Integer, primary_key=True, autoincrement=True)),
                Column("table_name", Column(String, nullable=False, index=True)),
                Column("foreign_key_column", Column(String, nullable=False)),
                Column("strategy", Column(String)),
                Column("orphans_found", Column(Integer)),
                Column("orphans_processed", Column(Integer)),
                Column("dry_run", Column(Boolean)),
                Column("success", Column(Boolean)),
                Column("errors", Column(Text)),
                Column("created_at", Column(datetime, default=datetime.utcnow)),
                Column("details", Column(Text)),
            ).create(conn)
            logger.info("Created orphan_cleanup_history table")
    
    async def discover_relationships(self) -> List[ForeignKeyRelationship]:
        """
        Automatically discover foreign key relationships from database schema.
        
        Returns:
            List of discovered ForeignKeyRelationship objects
        """
        self._relationships = []
        
        async with self.engine.connect() as conn:
            # Get all tables
            result = await conn.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
            )
            tables = [row.table_name for row in result]
            
            for table_name in tables:
                # Get foreign keys for each table
                fk_result = await conn.execute(
                    text("""
                        SELECT
                            tc.constraint_name,
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name,
                            rc.update_rule,
                            rc.delete_rule
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                            AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                            AND ccu.table_schema = tc.table_schema
                        LEFT JOIN information_schema.referential_constraints AS rc
                            ON rc.constraint_name = tc.constraint_name
                            AND rc.constraint_schema = tc.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = :table_name
                    """),
                    {"table_name": table_name}
                )
                
                for row in fk_result:
                    relationship = ForeignKeyRelationship(
                        table_name=table_name,
                        column_name=row.column_name,
                        referenced_table=row.foreign_table_name,
                        referenced_column=row.foreign_column_name,
                        constraint_name=row.constraint_name,
                        on_delete=row.delete_rule,
                        on_update=row.update_rule,
                    )
                    self._relationships.append(relationship)
        
        return self._relationships
    
    async def scan_table(
        self,
        table_name: str,
        foreign_key_column: str,
        referenced_table: str,
        referenced_column: str = "id",
        strategy: ScanStrategy = ScanStrategy.NOT_EXISTS,
        sample_size: int = 100
    ) -> ScanResult:
        """
        Scan a specific table for orphaned records.
        
        Args:
            table_name: Table to scan
            foreign_key_column: FK column to check
            referenced_table: Parent table name
            referenced_column: Parent column name (default: id)
            strategy: SQL detection strategy
            sample_size: Number of sample orphans to return
            
        Returns:
            ScanResult with orphan details
        """
        start_time = datetime.utcnow()
        
        result = ScanResult(
            table_name=table_name,
            foreign_key_column=foreign_key_column,
            referenced_table=referenced_table,
            orphan_count=0,
            scan_strategy=strategy.value,
        )
        
        try:
            async with AsyncSessionLocal() as session:
                # Build query based on strategy
                if strategy == ScanStrategy.NOT_EXISTS:
                    count_query = text(f"""
                        SELECT COUNT(*) as count
                        FROM {table_name} t
                        WHERE t.{foreign_key_column} IS NOT NULL
                        AND NOT EXISTS (
                            SELECT 1 FROM {referenced_table} r
                            WHERE r.{referenced_column} = t.{foreign_key_column}
                        )
                    """)
                elif strategy == ScanStrategy.LEFT_JOIN:
                    count_query = text(f"""
                        SELECT COUNT(*) as count
                        FROM {table_name} t
                        LEFT JOIN {referenced_table} r
                            ON r.{referenced_column} = t.{foreign_key_column}
                        WHERE t.{foreign_key_column} IS NOT NULL
                        AND r.{referenced_column} IS NULL
                    """)
                else:
                    count_query = text(f"""
                        SELECT COUNT(*) as count
                        FROM {table_name} t
                        WHERE t.{foreign_key_column} IS NOT NULL
                        AND t.{foreign_key_column} NOT IN (
                            SELECT {referenced_column} FROM {referenced_table}
                        )
                    """)
                
                # Get count
                count_result = await session.execute(count_query)
                result.orphan_count = count_result.scalar()
                
                # Get sample orphans
                if result.orphan_count > 0 and sample_size > 0:
                    sample_query = text(f"""
                        SELECT t.id, t.{foreign_key_column}
                        FROM {table_name} t
                        WHERE t.{foreign_key_column} IS NOT NULL
                        AND NOT EXISTS (
                            SELECT 1 FROM {referenced_table} r
                            WHERE r.{referenced_column} = t.{foreign_key_column}
                        )
                        LIMIT :limit
                    """)
                    
                    sample_result = await session.execute(
                        sample_query, {"limit": sample_size}
                    )
                    
                    for row in sample_result:
                        orphan = OrphanRecord(
                            table_name=table_name,
                            record_id=row.id,
                            foreign_key_column=foreign_key_column,
                            foreign_key_value=getattr(row, foreign_key_column),
                            referenced_table=referenced_table,
                        )
                        result.sample_orphans.append(orphan)
                
                end_time = datetime.utcnow()
                result.scan_duration_ms = (end_time - start_time).total_seconds() * 1000
                
                # Record in history
                await self._record_scan_history(result)
                
                # Trigger callbacks
                for callback in self._scan_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(result)
                        else:
                            callback(result)
                    except Exception as e:
                        logger.error(f"Scan callback failed: {e}")
                
                if result.has_orphans:
                    logger.warning(
                        f"Found {result.orphan_count} orphans in {table_name}.{foreign_key_column} "
                        f"referencing {referenced_table}"
                    )
                else:
                    logger.info(
                        f"No orphans found in {table_name}.{foreign_key_column}"
                    )
                
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Scan failed for {table_name}: {e}")
        
        return result
    
    async def scan_all(
        self,
        tables: Optional[List[str]] = None,
        strategy: ScanStrategy = ScanStrategy.NOT_EXISTS
    ) -> DatabaseIntegrityReport:
        """
        Scan all tables or specified tables for orphans.
        
        Args:
            tables: Specific tables to scan (None = all discovered)
            strategy: SQL detection strategy
            
        Returns:
            DatabaseIntegrityReport with comprehensive results
        """
        start_time = datetime.utcnow()
        report = DatabaseIntegrityReport()
        
        relationships_to_scan = self._relationships
        if tables:
            relationships_to_scan = [
                r for r in self._relationships if r.table_name in tables
            ]
        
        report.relationships_checked = len(relationships_to_scan)
        report.tables_scanned = len(set(r.table_name for r in relationships_to_scan))
        
        logger.info(f"Starting full database scan: {report.relationships_checked} relationships")
        
        for relationship in relationships_to_scan:
            result = await self.scan_table(
                table_name=relationship.table_name,
                foreign_key_column=relationship.column_name,
                referenced_table=relationship.referenced_table,
                referenced_column=relationship.referenced_column,
                strategy=strategy,
            )
            report.table_results.append(result)
            report.total_orphans_found += result.orphan_count
        
        end_time = datetime.utcnow()
        report.duration_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.info(
            f"Full scan complete: {report.total_orphans_found} orphans found, "
            f"integrity score: {report.integrity_score:.1f}%"
        )
        
        return report
    
    async def cleanup_orphans(
        self,
        table_name: str,
        foreign_key_column: str,
        referenced_table: str,
        strategy: CleanupStrategy = CleanupStrategy.REPORT_ONLY,
        dry_run: bool = True,
        batch_size: int = 1000,
        create_backup: bool = True
    ) -> CleanupResult:
        """
        Clean up orphaned records.
        
        Args:
            table_name: Table to clean
            foreign_key_column: FK column
            referenced_table: Parent table
            strategy: Cleanup strategy
            dry_run: If True, only simulate
            batch_size: Rows per batch
            create_backup: Create backup table before delete
            
        Returns:
            CleanupResult with operation details
        """
        start_time = datetime.utcnow()
        
        result = CleanupResult(
            table_name=table_name,
            foreign_key_column=foreign_key_column,
            strategy=strategy,
            orphans_found=0,
            orphans_processed=0,
            orphans_failed=0,
            dry_run=dry_run,
        )
        
        try:
            # First scan to count orphans
            scan_result = await self.scan_table(
                table_name, foreign_key_column, referenced_table
            )
            result.orphans_found = scan_result.orphan_count
            
            if result.orphans_found == 0:
                result.end_time = datetime.utcnow()
                result.duration_ms = (result.end_time - start_time).total_seconds() * 1000
                return result
            
            async with AsyncSessionLocal() as session:
                # Create backup if needed
                if create_backup and strategy in (CleanupStrategy.DELETE, CleanupStrategy.ARCHIVE_THEN_DELETE):
                    backup_table = f"{table_name}_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    if not dry_run:
                        await session.execute(
                            text(f"CREATE TABLE {backup_table} AS SELECT * FROM {table_name}")
                        )
                        result.backup_table = backup_table
                        logger.info(f"Created backup table: {backup_table}")
                
                # Execute cleanup based on strategy
                if strategy == CleanupStrategy.REPORT_ONLY:
                    # No action needed
                    pass
                    
                elif strategy == CleanupStrategy.DELETE:
                    result = await self._delete_orphans(
                        session, table_name, foreign_key_column,
                        referenced_table, result, dry_run, batch_size
                    )
                    
                elif strategy == CleanupStrategy.SOFT_DELETE:
                    result = await self._soft_delete_orphans(
                        session, table_name, foreign_key_column,
                        referenced_table, result, dry_run
                    )
                    
                elif strategy == CleanupStrategy.NULLIFY:
                    result = await self._nullify_orphans(
                        session, table_name, foreign_key_column,
                        referenced_table, result, dry_run
                    )
                    
                elif strategy == CleanupStrategy.ARCHIVE_THEN_DELETE:
                    result = await self._archive_then_delete_orphans(
                        session, table_name, foreign_key_column,
                        referenced_table, result, dry_run, batch_size
                    )
                
                if dry_run:
                    await session.rollback()
                    logger.info(f"Dry-run cleanup completed for {table_name}")
                else:
                    await session.commit()
                    logger.info(
                        f"Cleanup completed: {result.orphans_processed} orphans processed"
                    )
            
            result.end_time = datetime.utcnow()
            result.duration_ms = (result.end_time - start_time).total_seconds() * 1000
            
            # Record history
            await self._record_cleanup_history(result)
            
            # Trigger callbacks
            for callback in self._cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(result)
                    else:
                        callback(result)
                except Exception as e:
                    logger.error(f"Cleanup callback failed: {e}")
            
        except Exception as e:
            result.end_time = datetime.utcnow()
            result.duration_ms = (result.end_time - start_time).total_seconds() * 1000
            result.errors.append(str(e))
            logger.error(f"Cleanup failed for {table_name}: {e}")
            raise
        
        return result
    
    async def _delete_orphans(
        self,
        session: AsyncSession,
        table_name: str,
        foreign_key_column: str,
        referenced_table: str,
        result: CleanupResult,
        dry_run: bool,
        batch_size: int
    ) -> CleanupResult:
        """Delete orphaned records."""
        processed = 0
        
        while True:
            if dry_run:
                # Just count remaining
                count_result = await session.execute(
                    text(f"""
                        SELECT COUNT(*) FROM {table_name}
                        WHERE {foreign_key_column} IS NOT NULL
                        AND NOT EXISTS (
                            SELECT 1 FROM {referenced_table}
                            WHERE id = {table_name}.{foreign_key_column}
                        )
                    """)
                )
                remaining = count_result.scalar()
                if remaining == 0:
                    break
                processed += min(remaining, batch_size)
                if processed >= result.orphans_found:
                    break
            else:
                # Delete batch
                delete_result = await session.execute(
                    text(f"""
                        DELETE FROM {table_name}
                        WHERE id IN (
                            SELECT id FROM {table_name}
                            WHERE {foreign_key_column} IS NOT NULL
                            AND NOT EXISTS (
                                SELECT 1 FROM {referenced_table}
                                WHERE id = {table_name}.{foreign_key_column}
                            )
                            LIMIT :batch_size
                        )
                    """),
                    {"batch_size": batch_size}
                )
                
                batch_deleted = delete_result.rowcount
                processed += batch_deleted
                
                if batch_deleted == 0:
                    break
                
                # Commit batch
                await session.commit()
        
        result.orphans_processed = processed
        return result
    
    async def _soft_delete_orphans(
        self,
        session: AsyncSession,
        table_name: str,
        foreign_key_column: str,
        referenced_table: str,
        result: CleanupResult,
        dry_run: bool
    ) -> CleanupResult:
        """Mark orphans as deleted."""
        if not dry_run:
            update_result = await session.execute(
                text(f"""
                    UPDATE {table_name}
                    SET is_deleted = TRUE, deleted_at = NOW()
                    WHERE {foreign_key_column} IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM {referenced_table}
                        WHERE id = {table_name}.{foreign_key_column}
                    )
                    AND (is_deleted = FALSE OR is_deleted IS NULL)
                """)
            )
            result.orphans_processed = update_result.rowcount
        else:
            result.orphans_processed = result.orphans_found
        
        return result
    
    async def _nullify_orphans(
        self,
        session: AsyncSession,
        table_name: str,
        foreign_key_column: str,
        referenced_table: str,
        result: CleanupResult,
        dry_run: bool
    ) -> CleanupResult:
        """Set FK to NULL for orphans."""
        if not dry_run:
            update_result = await session.execute(
                text(f"""
                    UPDATE {table_name}
                    SET {foreign_key_column} = NULL
                    WHERE {foreign_key_column} IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM {referenced_table}
                        WHERE id = {table_name}.{foreign_key_column}
                    )
                """)
            )
            result.orphans_processed = update_result.rowcount
        else:
            result.orphans_processed = result.orphans_found
        
        return result
    
    async def _archive_then_delete_orphans(
        self,
        session: AsyncSession,
        table_name: str,
        foreign_key_column: str,
        referenced_table: str,
        result: CleanupResult,
        dry_run: bool,
        batch_size: int
    ) -> CleanupResult:
        """Archive orphans before deletion."""
        archive_table = f"{table_name}_orphans"
        
        if not dry_run:
            # Ensure archive table exists
            await session.execute(
                text(f"""
                    CREATE TABLE IF NOT EXISTS {archive_table} (
                        LIKE {table_name} INCLUDING ALL
                    )
                """)
            )
            
            # Add archival timestamp
            await session.execute(
                text(f"""
                    ALTER TABLE {archive_table}
                    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP DEFAULT NOW()
                """)
            )
            
            # Archive and delete in batches
            processed = 0
            while True:
                # Archive batch
                await session.execute(
                    text(f"""
                        INSERT INTO {archive_table}
                        SELECT *, NOW() FROM {table_name}
                        WHERE id IN (
                            SELECT id FROM {table_name}
                            WHERE {foreign_key_column} IS NOT NULL
                            AND NOT EXISTS (
                                SELECT 1 FROM {referenced_table}
                                WHERE id = {table_name}.{foreign_key_column}
                            )
                            LIMIT :batch_size
                        )
                    """),
                    {"batch_size": batch_size}
                )
                
                # Delete batch
                delete_result = await session.execute(
                    text(f"""
                        DELETE FROM {table_name}
                        WHERE id IN (
                            SELECT id FROM {archive_table}
                            WHERE archived_at > NOW() - INTERVAL '1 minute'
                        )
                    """)
                )
                
                batch_deleted = delete_result.rowcount
                processed += batch_deleted
                
                if batch_deleted == 0:
                    break
                
                await session.commit()
            
            result.orphans_processed = processed
        else:
            result.orphans_processed = result.orphans_found
        
        return result
    
    async def _record_scan_history(self, result: ScanResult) -> None:
        """Record scan in history table."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        INSERT INTO orphan_scan_history (
                            table_name, foreign_key_column, referenced_table,
                            orphan_count, scan_strategy, scan_duration_ms, details
                        ) VALUES (
                            :table_name, :fk_column, :ref_table,
                            :orphan_count, :strategy, :duration_ms, :details
                        )
                    """),
                    {
                        "table_name": result.table_name,
                        "fk_column": result.foreign_key_column,
                        "ref_table": result.referenced_table,
                        "orphan_count": result.orphan_count,
                        "strategy": result.scan_strategy,
                        "duration_ms": int(result.scan_duration_ms),
                        "details": json.dumps(result.to_dict()),
                    }
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record scan history: {e}")
    
    async def _record_cleanup_history(self, result: CleanupResult) -> None:
        """Record cleanup in history table."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text("""
                        INSERT INTO orphan_cleanup_history (
                            table_name, foreign_key_column, strategy,
                            orphans_found, orphans_processed, dry_run,
                            success, errors, details
                        ) VALUES (
                            :table_name, :fk_column, :strategy,
                            :orphans_found, :orphans_processed, :dry_run,
                            :success, :errors, :details
                        )
                    """),
                    {
                        "table_name": result.table_name,
                        "fk_column": result.foreign_key_column,
                        "strategy": result.strategy.value,
                        "orphans_found": result.orphans_found,
                        "orphans_processed": result.orphans_processed,
                        "dry_run": result.dry_run,
                        "success": result.success,
                        "errors": json.dumps(result.errors) if result.errors else None,
                        "details": json.dumps(result.to_dict()),
                    }
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record cleanup history: {e}")
    
    async def get_scan_history(
        self,
        table_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get scan history."""
        async with AsyncSessionLocal() as session:
            if table_name:
                result = await session.execute(
                    text("""
                        SELECT * FROM orphan_scan_history
                        WHERE table_name = :table_name
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"table_name": table_name, "limit": limit}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM orphan_scan_history
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            
            history = []
            for row in result:
                history.append({
                    "id": row.id,
                    "table_name": row.table_name,
                    "foreign_key_column": row.foreign_key_column,
                    "referenced_table": row.referenced_table,
                    "orphan_count": row.orphan_count,
                    "scan_strategy": row.scan_strategy,
                    "scan_duration_ms": row.scan_duration_ms,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
            
            return history
    
    async def get_cleanup_history(
        self,
        table_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get cleanup history."""
        async with AsyncSessionLocal() as session:
            if table_name:
                result = await session.execute(
                    text("""
                        SELECT * FROM orphan_cleanup_history
                        WHERE table_name = :table_name
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"table_name": table_name, "limit": limit}
                )
            else:
                result = await session.execute(
                    text("""
                        SELECT * FROM orphan_cleanup_history
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
            
            history = []
            for row in result:
                history.append({
                    "id": row.id,
                    "table_name": row.table_name,
                    "foreign_key_column": row.foreign_key_column,
                    "strategy": row.strategy,
                    "orphans_found": row.orphans_found,
                    "orphans_processed": row.orphans_processed,
                    "dry_run": row.dry_run,
                    "success": row.success,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
            
            return history
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall scanner statistics."""
        async with AsyncSessionLocal() as session:
            # Total scans
            result = await session.execute(
                text("SELECT COUNT(*) FROM orphan_scan_history")
            )
            total_scans = result.scalar()
            
            # Total cleanups
            result = await session.execute(
                text("SELECT COUNT(*) FROM orphan_cleanup_history")
            )
            total_cleanups = result.scalar()
            
            # Total orphans found
            result = await session.execute(
                text("SELECT COALESCE(SUM(orphan_count), 0) FROM orphan_scan_history")
            )
            total_orphans = result.scalar()
            
            # Total orphans processed
            result = await session.execute(
                text("SELECT COALESCE(SUM(orphans_processed), 0) FROM orphan_cleanup_history")
            )
            total_processed = result.scalar()
            
            # Recent scans (last 24h)
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM orphan_scan_history
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
            )
            recent_scans = result.scalar()
            
            return {
                "total_scans": total_scans,
                "total_cleanups": total_cleanups,
                "total_orphans_found": total_orphans,
                "total_orphans_processed": total_processed,
                "scans_last_24h": recent_scans,
                "relationships_discovered": len(self._relationships),
            }
    
    def register_scan_callback(self, callback: Callable[[ScanResult], None]) -> None:
        """Register a callback for scan completion."""
        self._scan_callbacks.append(callback)
    
    def register_cleanup_callback(self, callback: Callable[[CleanupResult], None]) -> None:
        """Register a callback for cleanup completion."""
        self._cleanup_callbacks.append(callback)


# Global instance
_orphan_scanner: Optional[OrphanScanner] = None


async def get_orphan_scanner(engine: Optional[AsyncEngine] = None) -> OrphanScanner:
    """Get or create the global orphan scanner."""
    global _orphan_scanner
    
    if _orphan_scanner is None:
        if engine is None:
            from ..services.db_service import engine
        _orphan_scanner = OrphanScanner(engine)
        await _orphan_scanner.initialize()
    
    return _orphan_scanner
