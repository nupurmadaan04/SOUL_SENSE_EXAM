"""
Integration tests for Foreign Key Integrity Orphan Scanner (#1414).

Tests end-to-end orphan scanning with real database operations.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.utils.orphan_scanner import (
    OrphanScanner,
    ForeignKeyRelationship,
    OrphanRecord,
    ScanResult,
    CleanupResult,
    DatabaseIntegrityReport,
    ScanStrategy,
    CleanupStrategy,
    get_orphan_scanner,
)
from api.services.db_service import engine


@pytest.fixture
async def orphan_scanner():
    """Create and initialize orphan scanner for testing."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    return scanner


@pytest.mark.asyncio
async def test_scanner_initialization():
    """Test orphan scanner initialization."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Verify scanner is ready
    assert scanner._metadata is not None


@pytest.mark.asyncio
async def test_relationship_discovery():
    """Test discovering FK relationships from database."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Discover relationships
    relationships = await scanner.discover_relationships()
    
    # Should find some relationships (depending on schema)
    assert isinstance(relationships, list)


@pytest.mark.asyncio
async def test_scan_table_operation():
    """Test scanning a table for orphans."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Scan a known relationship (if exists)
    result = await scanner.scan_table(
        table_name="notification_logs",
        foreign_key_column="user_id",
        referenced_table="users",
        strategy=ScanStrategy.NOT_EXISTS,
    )
    
    # Verify result structure
    assert result.table_name == "notification_logs"
    assert result.foreign_key_column == "user_id"
    assert result.success is True


@pytest.mark.asyncio
async def test_scan_with_different_strategies():
    """Test scanning with different SQL strategies."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    strategies = [ScanStrategy.NOT_EXISTS, ScanStrategy.LEFT_JOIN]
    
    for strategy in strategies:
        result = await scanner.scan_table(
            table_name="notification_logs",
            foreign_key_column="user_id",
            referenced_table="users",
            strategy=strategy,
        )
        
        assert result.scan_strategy == strategy.value
        assert result.success is True


@pytest.mark.asyncio
async def test_full_database_scan():
    """Test full database integrity scan."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Run full scan
    report = await scanner.scan_all()
    
    # Verify report structure
    assert report.tables_scanned >= 0
    assert report.integrity_score >= 0.0
    assert report.integrity_score <= 100.0
    assert isinstance(report.table_results, list)


@pytest.mark.asyncio
async def test_cleanup_dry_run():
    """Test cleanup in dry-run mode."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Run cleanup in dry-run mode
    result = await scanner.cleanup_orphans(
        table_name="notification_logs",
        foreign_key_column="user_id",
        referenced_table="users",
        strategy=CleanupStrategy.REPORT_ONLY,
        dry_run=True,
    )
    
    # Verify result
    assert result.dry_run is True
    assert result.success is True


@pytest.mark.asyncio
async def test_scan_history_tracking():
    """Test that scans are tracked in history."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Perform a scan
    await scanner.scan_table(
        table_name="notification_logs",
        foreign_key_column="user_id",
        referenced_table="users",
    )
    
    # Check history
    history = await scanner.get_scan_history(limit=1)
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_statistics_collection():
    """Test statistics collection."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    stats = await scanner.get_statistics()
    
    # Verify stats structure
    assert "total_scans" in stats
    assert "total_cleanups" in stats
    assert "total_orphans_found" in stats
    assert "relationships_discovered" in stats


@pytest.mark.asyncio
async def test_callback_registration():
    """Test callback registration."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    scan_callbacks = []
    cleanup_callbacks = []
    
    def scan_callback(result):
        scan_callbacks.append(result.table_name)
    
    def cleanup_callback(result):
        cleanup_callbacks.append(result.table_name)
    
    scanner.register_scan_callback(scan_callback)
    scanner.register_cleanup_callback(cleanup_callback)
    
    # Verify callbacks registered
    assert scan_callback in scanner._scan_callbacks
    assert cleanup_callback in scanner._cleanup_callbacks


@pytest.mark.asyncio
async def test_database_integrity_report():
    """Test database integrity report generation."""
    scanner = OrphanScanner(engine)
    await scanner.initialize()
    
    # Generate report
    report = await scanner.scan_all()
    
    # Convert to dict
    report_dict = report.to_dict()
    
    assert "scan_time" in report_dict
    assert "tables_scanned" in report_dict
    assert "integrity_score" in report_dict
    assert "table_results" in report_dict


@pytest.mark.asyncio
async def test_scan_result_properties():
    """Test ScanResult helper properties."""
    # No orphans
    result_clean = ScanResult(
        table_name="test",
        foreign_key_column="fk",
        referenced_table="ref",
        orphan_count=0,
    )
    assert result_clean.has_orphans is False
    assert result_clean.success is True
    
    # With orphans
    result_orphans = ScanResult(
        table_name="test",
        foreign_key_column="fk",
        referenced_table="ref",
        orphan_count=10,
    )
    assert result_orphans.has_orphans is True
    
    # With error
    result_error = ScanResult(
        table_name="test",
        foreign_key_column="fk",
        referenced_table="ref",
        orphan_count=0,
        error_message="Connection failed",
    )
    assert result_error.success is False


@pytest.mark.asyncio
async def test_cleanup_result_properties():
    """Test CleanupResult helper properties."""
    # Successful cleanup
    result_success = CleanupResult(
        table_name="test",
        foreign_key_column="fk",
        strategy=CleanupStrategy.DELETE,
        orphans_found=10,
        orphans_processed=10,
        orphans_failed=0,
        dry_run=False,
    )
    assert result_success.success is True
    
    # Failed cleanup
    result_failed = CleanupResult(
        table_name="test",
        foreign_key_column="fk",
        strategy=CleanupStrategy.DELETE,
        orphans_found=10,
        orphans_processed=5,
        orphans_failed=5,
        dry_run=False,
        errors=["Error 1"],
    )
    assert result_failed.success is False


@pytest.mark.asyncio
async def test_integrity_score_calculation():
    """Test integrity score calculations."""
    # Perfect score
    results_clean = [
        ScanResult("t1", "fk1", "r1", 0),
        ScanResult("t2", "fk2", "r2", 0),
    ]
    report_clean = DatabaseIntegrityReport(
        relationships_checked=2,
        table_results=results_clean,
    )
    assert report_clean.integrity_score == 100.0
    
    # 50% score
    results_mixed = [
        ScanResult("t1", "fk1", "r1", 0),
        ScanResult("t2", "fk2", "r2", 10),
    ]
    report_mixed = DatabaseIntegrityReport(
        relationships_checked=2,
        table_results=results_mixed,
    )
    assert report_mixed.integrity_score == 50.0
    
    # 0% score
    results_dirty = [
        ScanResult("t1", "fk1", "r1", 5),
        ScanResult("t2", "fk2", "r2", 10),
    ]
    report_dirty = DatabaseIntegrityReport(
        relationships_checked=2,
        table_results=results_dirty,
    )
    assert report_dirty.integrity_score == 0.0


@pytest.mark.asyncio
async def test_global_scanner_instance():
    """Test global scanner instance."""
    scanner1 = await get_orphan_scanner(engine)
    scanner2 = await get_orphan_scanner(engine)
    
    # Should return same instance
    assert scanner1 is scanner2


@pytest.mark.asyncio
async def test_orphan_record_creation():
    """Test orphan record creation."""
    orphan = OrphanRecord(
        table_name="responses",
        record_id=123,
        foreign_key_column="user_id",
        foreign_key_value=456,
        referenced_table="users",
        detected_at=datetime(2026, 3, 7, 12, 0, 0),
    )
    
    orphan_dict = orphan.to_dict()
    
    assert orphan_dict["table_name"] == "responses"
    assert orphan_dict["record_id"] == 123
    assert orphan_dict["foreign_key_value"] == "456"


@pytest.mark.asyncio
async def test_foreign_key_relationship_creation():
    """Test FK relationship creation."""
    rel = ForeignKeyRelationship(
        table_name="responses",
        column_name="user_id",
        referenced_table="users",
        referenced_column="id",
        constraint_name="fk_test",
        on_delete="CASCADE",
        on_update="NO ACTION",
    )
    
    rel_dict = rel.to_dict()
    
    assert rel_dict["table_name"] == "responses"
    assert rel_dict["constraint_name"] == "fk_test"
    assert rel_dict["on_delete"] == "CASCADE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
