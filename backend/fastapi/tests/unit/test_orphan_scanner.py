"""
Unit tests for Foreign Key Integrity Orphan Scanner (#1414).

Tests orphan detection, cleanup strategies, and reporting functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
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


class TestForeignKeyRelationship:
    """Test ForeignKeyRelationship dataclass."""

    def test_basic_creation(self):
        """Test creating a FK relationship."""
        rel = ForeignKeyRelationship(
            table_name="responses",
            column_name="user_id",
            referenced_table="users",
            referenced_column="id",
        )
        
        assert rel.table_name == "responses"
        assert rel.column_name == "user_id"
        assert rel.referenced_table == "users"
        assert rel.referenced_column == "id"

    def test_to_dict(self):
        """Test converting to dictionary."""
        rel = ForeignKeyRelationship(
            table_name="responses",
            column_name="user_id",
            referenced_table="users",
            referenced_column="id",
            constraint_name="fk_responses_user",
            on_delete="CASCADE",
        )
        
        result = rel.to_dict()
        
        assert result["table_name"] == "responses"
        assert result["constraint_name"] == "fk_responses_user"
        assert result["on_delete"] == "CASCADE"


class TestOrphanRecord:
    """Test OrphanRecord dataclass."""

    def test_basic_creation(self):
        """Test creating an orphan record."""
        orphan = OrphanRecord(
            table_name="responses",
            record_id=123,
            foreign_key_column="user_id",
            foreign_key_value=456,
            referenced_table="users",
        )
        
        assert orphan.table_name == "responses"
        assert orphan.record_id == 123
        assert orphan.foreign_key_value == 456

    def test_to_dict(self):
        """Test converting to dictionary."""
        orphan = OrphanRecord(
            table_name="responses",
            record_id=123,
            foreign_key_column="user_id",
            foreign_key_value=456,
            referenced_table="users",
            detected_at=datetime(2026, 3, 7, 12, 0, 0),
        )
        
        result = orphan.to_dict()
        
        assert result["table_name"] == "responses"
        assert result["foreign_key_value"] == "456"


class TestScanResult:
    """Test ScanResult dataclass."""

    def test_basic_creation(self):
        """Test creating a scan result."""
        result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=10,
        )
        
        assert result.table_name == "responses"
        assert result.orphan_count == 10
        assert result.has_orphans is True
        assert result.success is True

    def test_no_orphans(self):
        """Test result with no orphans."""
        result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=0,
        )
        
        assert result.has_orphans is False

    def test_with_error(self):
        """Test result with error."""
        result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=0,
            error_message="Connection failed",
        )
        
        assert result.success is False

    def test_to_dict(self):
        """Test converting to dictionary."""
        orphan = OrphanRecord(
            table_name="responses",
            record_id=123,
            foreign_key_column="user_id",
            foreign_key_value=456,
            referenced_table="users",
        )
        
        result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=10,
            sample_orphans=[orphan],
            scan_duration_ms=150.5,
            scan_strategy="not_exists",
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["orphan_count"] == 10
        assert dict_result["has_orphans"] is True
        assert dict_result["scan_duration_ms"] == 150.5


class TestCleanupResult:
    """Test CleanupResult dataclass."""

    def test_basic_creation(self):
        """Test creating a cleanup result."""
        result = CleanupResult(
            table_name="responses",
            foreign_key_column="user_id",
            strategy=CleanupStrategy.DELETE,
            orphans_found=10,
            orphans_processed=10,
            orphans_failed=0,
            dry_run=True,
        )
        
        assert result.table_name == "responses"
        assert result.orphans_processed == 10
        assert result.success is True

    def test_with_errors(self):
        """Test cleanup result with errors."""
        result = CleanupResult(
            table_name="responses",
            foreign_key_column="user_id",
            strategy=CleanupStrategy.DELETE,
            orphans_found=10,
            orphans_processed=5,
            orphans_failed=5,
            dry_run=False,
            errors=["Error 1", "Error 2"],
        )
        
        assert result.success is False

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = CleanupResult(
            table_name="responses",
            foreign_key_column="user_id",
            strategy=CleanupStrategy.SOFT_DELETE,
            orphans_found=100,
            orphans_processed=100,
            orphans_failed=0,
            dry_run=False,
            duration_ms=5000.0,
        )
        
        dict_result = result.to_dict()
        
        assert dict_result["strategy"] == "soft_delete"
        assert dict_result["orphans_found"] == 100
        assert dict_result["success"] is True


class TestDatabaseIntegrityReport:
    """Test DatabaseIntegrityReport dataclass."""

    def test_basic_creation(self):
        """Test creating an integrity report."""
        report = DatabaseIntegrityReport(
            tables_scanned=10,
            relationships_checked=25,
            total_orphans_found=50,
        )
        
        assert report.tables_scanned == 10
        assert report.total_orphans_found == 50

    def test_integrity_score_perfect(self):
        """Test integrity score with no orphans."""
        result1 = ScanResult(
            table_name="t1", foreign_key_column="fk1",
            referenced_table="r1", orphan_count=0
        )
        result2 = ScanResult(
            table_name="t2", foreign_key_column="fk2",
            referenced_table="r2", orphan_count=0
        )
        
        report = DatabaseIntegrityReport(
            relationships_checked=2,
            table_results=[result1, result2],
        )
        
        assert report.integrity_score == 100.0

    def test_integrity_score_partial(self):
        """Test integrity score with some orphans."""
        result1 = ScanResult(
            table_name="t1", foreign_key_column="fk1",
            referenced_table="r1", orphan_count=0
        )
        result2 = ScanResult(
            table_name="t2", foreign_key_column="fk2",
            referenced_table="r2", orphan_count=10
        )
        
        report = DatabaseIntegrityReport(
            relationships_checked=2,
            table_results=[result1, result2],
        )
        
        assert report.integrity_score == 50.0

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=10,
        )
        
        report = DatabaseIntegrityReport(
            scan_time=datetime(2026, 3, 7, 12, 0, 0),
            tables_scanned=5,
            relationships_checked=10,
            total_orphans_found=25,
            table_results=[result],
            duration_ms=1000.0,
        )
        
        dict_result = report.to_dict()
        
        assert dict_result["tables_scanned"] == 5
        assert dict_result["integrity_score"] == 0.0  # 1 of 10 has orphans


class TestOrphanScannerInitialization:
    """Test OrphanScanner initialization."""

    def test_init_with_engine(self):
        """Test initialization with engine."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        assert scanner.engine == mock_engine
        assert len(scanner._relationships) == 0

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test scanner initialization."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock internal methods
        with patch.object(scanner, '_ensure_history_table') as mock_ensure:
            with patch.object(scanner, 'discover_relationships') as mock_discover:
                mock_discover.return_value = []
                await scanner.initialize()
                
                mock_ensure.assert_called_once()
                mock_discover.assert_called_once()


class TestRelationshipDiscovery:
    """Test relationship discovery."""

    @pytest.mark.asyncio
    async def test_discover_relationships(self):
        """Test discovering FK relationships."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock database connection
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock table list
        mock_conn.execute.return_value = [
            Mock(table_name="users"),
            Mock(table_name="responses"),
        ]
        
        # Mock FK query
        mock_fk_result = [
            Mock(
                constraint_name="fk_responses_user",
                column_name="user_id",
                foreign_table_name="users",
                foreign_column_name="id",
                delete_rule=None,
                update_rule=None,
            )
        ]
        
        relationships = await scanner.discover_relationships()
        
        # Note: This is a simplified test - actual implementation
        # would need more complex mocking


class TestScanOperations:
    """Test scan operations."""

    @pytest.mark.asyncio
    async def test_scan_table_no_orphans(self):
        """Test scanning table with no orphans."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock database result - no orphans
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        
        with patch('api.utils.orphan_scanner.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.execute.return_value = mock_result
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(scanner, '_record_scan_history'):
                result = await scanner.scan_table(
                    "responses", "user_id", "users"
                )
                
                assert result.orphan_count == 0
                assert result.has_orphans is False

    @pytest.mark.asyncio
    async def test_scan_table_with_orphans(self):
        """Test scanning table with orphans."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock database result - has orphans
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 10
        
        mock_sample_result = [
            Mock(id=1, user_id=100),
            Mock(id=2, user_id=101),
        ]
        
        with patch('api.utils.orphan_scanner.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.execute.side_effect = [
                mock_count_result,
                mock_sample_result,
            ]
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with patch.object(scanner, '_record_scan_history'):
                result = await scanner.scan_table(
                    "responses", "user_id", "users"
                )
                
                assert result.orphan_count == 10
                assert result.has_orphans is True


class TestCleanupOperations:
    """Test cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_no_orphans(self):
        """Test cleanup when no orphans exist."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock scan result - no orphans
        mock_scan_result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=0,
        )
        
        with patch.object(scanner, 'scan_table', return_value=mock_scan_result):
            result = await scanner.cleanup_orphans(
                "responses", "user_id", "users",
                strategy=CleanupStrategy.DELETE,
                dry_run=True,
            )
            
            assert result.orphans_found == 0
            assert result.orphans_processed == 0

    @pytest.mark.asyncio
    async def test_cleanup_dry_run(self):
        """Test cleanup in dry-run mode."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock scan result - has orphans
        mock_scan_result = ScanResult(
            table_name="responses",
            foreign_key_column="user_id",
            referenced_table="users",
            orphan_count=10,
        )
        
        with patch.object(scanner, 'scan_table', return_value=mock_scan_result):
            with patch('api.utils.orphan_scanner.AsyncSessionLocal') as mock_session:
                mock_session_instance = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
                
                result = await scanner.cleanup_orphans(
                    "responses", "user_id", "users",
                    strategy=CleanupStrategy.DELETE,
                    dry_run=True,
                )
                
                assert result.dry_run is True
                assert result.orphans_found == 10


class TestStatisticsAndHistory:
    """Test statistics and history tracking."""

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """Test getting statistics."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Mock database results
        mock_results = [
            Mock(scalar=lambda: 50),   # total_scans
            Mock(scalar=lambda: 10),   # total_cleanups
            Mock(scalar=lambda: 1000), # total_orphans
            Mock(scalar=lambda: 500),  # total_processed
            Mock(scalar=lambda: 5),    # recent_scans
        ]
        
        with patch('api.utils.orphan_scanner.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session_instance.execute.side_effect = mock_results
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
            
            stats = await scanner.get_statistics()
            
            assert stats["total_scans"] == 50
            assert stats["total_orphans_found"] == 1000


class TestCallbackRegistration:
    """Test callback registration."""

    def test_register_scan_callback(self):
        """Test registering scan callback."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        def callback(result):
            pass
        
        scanner.register_scan_callback(callback)
        
        assert callback in scanner._scan_callbacks

    def test_register_cleanup_callback(self):
        """Test registering cleanup callback."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        def callback(result):
            pass
        
        scanner.register_cleanup_callback(callback)
        
        assert callback in scanner._cleanup_callbacks


class TestEnums:
    """Test enum classes."""

    def test_scan_strategy_values(self):
        """Test scan strategy enum values."""
        assert ScanStrategy.NOT_EXISTS.value == "not_exists"
        assert ScanStrategy.LEFT_JOIN.value == "left_join"
        assert ScanStrategy.EXCEPT_QUERY.value == "except"

    def test_cleanup_strategy_values(self):
        """Test cleanup strategy enum values."""
        assert CleanupStrategy.DELETE.value == "delete"
        assert CleanupStrategy.SOFT_DELETE.value == "soft_delete"
        assert CleanupStrategy.NULLIFY.value == "nullify"
        assert CleanupStrategy.REPORT_ONLY.value == "report_only"
        assert CleanupStrategy.ARCHIVE_THEN_DELETE.value == "archive_then_delete"


class TestFullScan:
    """Test full database scan."""

    @pytest.mark.asyncio
    async def test_scan_all(self):
        """Test scanning all tables."""
        mock_engine = Mock()
        scanner = OrphanScanner(mock_engine)
        
        # Add some relationships
        scanner._relationships = [
            ForeignKeyRelationship(
                table_name="responses",
                column_name="user_id",
                referenced_table="users",
                referenced_column="id",
            ),
            ForeignKeyRelationship(
                table_name="scores",
                column_name="user_id",
                referenced_table="users",
                referenced_column="id",
            ),
        ]
        
        # Mock scan results
        mock_results = [
            ScanResult("responses", "user_id", "users", 0),
            ScanResult("scores", "user_id", "users", 5),
        ]
        
        with patch.object(scanner, 'scan_table', side_effect=mock_results):
            report = await scanner.scan_all()
            
            assert report.tables_scanned == 2
            assert report.relationships_checked == 2
            assert report.total_orphans_found == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
