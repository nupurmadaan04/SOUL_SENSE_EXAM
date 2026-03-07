"""
Orphan Scanner API Endpoints (#1414)

Provides REST API endpoints for foreign key integrity scanning,
orphan detection, and cleanup operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..utils.orphan_scanner import (
    get_orphan_scanner,
    OrphanScanner,
    ScanStrategy,
    CleanupStrategy,
    ForeignKeyRelationship,
)
from .auth import require_admin


router = APIRouter(tags=["Orphan Scanner"], prefix="/admin/orphan-scanner")


# --- Pydantic Schemas ---

class ScanRequest(BaseModel):
    """Schema for orphan scan request."""
    table_name: str = Field(..., description="Table to scan")
    foreign_key_column: str = Field(..., description="FK column to check")
    referenced_table: str = Field(..., description="Parent table name")
    referenced_column: str = Field(default="id", description="Parent column name")
    strategy: ScanStrategy = Field(default=ScanStrategy.NOT_EXISTS)
    sample_size: int = Field(default=100, ge=0, le=1000)


class CleanupRequest(BaseModel):
    """Schema for cleanup request."""
    table_name: str = Field(..., description="Table to clean")
    foreign_key_column: str = Field(..., description="FK column")
    referenced_table: str = Field(..., description="Parent table")
    strategy: CleanupStrategy = Field(default=CleanupStrategy.REPORT_ONLY)
    dry_run: bool = Field(default=True, description="Simulate only")
    batch_size: int = Field(default=1000, ge=100, le=10000)
    create_backup: bool = Field(default=True)


class ScanResultResponse(BaseModel):
    """Schema for scan result."""
    table_name: str
    foreign_key_column: str
    referenced_table: str
    orphan_count: int
    sample_orphans: List[Dict[str, Any]]
    scan_duration_ms: float
    scan_strategy: str
    has_orphans: bool
    success: bool
    error_message: Optional[str]


class CleanupResultResponse(BaseModel):
    """Schema for cleanup result."""
    table_name: str
    foreign_key_column: str
    strategy: str
    orphans_found: int
    orphans_processed: int
    orphans_failed: int
    dry_run: bool
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: float
    success: bool
    errors: List[str]
    backup_table: Optional[str]


class ForeignKeyRelationshipResponse(BaseModel):
    """Schema for FK relationship."""
    table_name: str
    column_name: str
    referenced_table: str
    referenced_column: str
    constraint_name: Optional[str]
    on_delete: Optional[str]
    on_update: Optional[str]


class DatabaseIntegrityReportResponse(BaseModel):
    """Schema for integrity report."""
    scan_time: datetime
    tables_scanned: int
    relationships_checked: int
    total_orphans_found: int
    integrity_score: float
    duration_ms: float
    table_results: List[ScanResultResponse]


class OrphanScannerStatsResponse(BaseModel):
    """Schema for scanner statistics."""
    total_scans: int
    total_cleanups: int
    total_orphans_found: int
    total_orphans_processed: int
    scans_last_24h: int
    relationships_discovered: int


class OrphanScannerStatusResponse(BaseModel):
    """Schema for scanner status."""
    status: str
    relationships: List[ForeignKeyRelationshipResponse]
    statistics: OrphanScannerStatsResponse


# --- API Endpoints ---

@router.get(
    "/status",
    response_model=OrphanScannerStatusResponse,
    summary="Get orphan scanner status",
    description="Returns scanner status, discovered relationships, and statistics."
)
async def get_scanner_status(
    current_user: Any = Depends(require_admin)
) -> OrphanScannerStatusResponse:
    """Get orphan scanner status."""
    scanner = await get_orphan_scanner()
    
    # Get statistics
    stats = await scanner.get_statistics()
    
    # Build relationships list
    relationships = [
        ForeignKeyRelationshipResponse(**rel.to_dict())
        for rel in scanner._relationships
    ]
    
    return OrphanScannerStatusResponse(
        status="healthy" if len(scanner._relationships) > 0 else "inactive",
        relationships=relationships,
        statistics=OrphanScannerStatsResponse(**stats),
    )


@router.post(
    "/discover",
    response_model=List[ForeignKeyRelationshipResponse],
    summary="Discover foreign key relationships",
    description="Scans database schema to discover all FK relationships."
)
async def discover_relationships(
    current_user: Any = Depends(require_admin)
) -> List[ForeignKeyRelationshipResponse]:
    """Discover foreign key relationships."""
    scanner = await get_orphan_scanner()
    relationships = await scanner.discover_relationships()
    
    return [ForeignKeyRelationshipResponse(**rel.to_dict()) for rel in relationships]


@router.post(
    "/scan",
    response_model=ScanResultResponse,
    summary="Scan table for orphans",
    description="Scans a specific table for orphaned foreign key references."
)
async def scan_table(
    request: ScanRequest,
    current_user: Any = Depends(require_admin)
) -> ScanResultResponse:
    """Scan a table for orphans."""
    scanner = await get_orphan_scanner()
    
    result = await scanner.scan_table(
        table_name=request.table_name,
        foreign_key_column=request.foreign_key_column,
        referenced_table=request.referenced_table,
        referenced_column=request.referenced_column,
        strategy=request.strategy,
        sample_size=request.sample_size,
    )
    
    return ScanResultResponse(**result.to_dict())


@router.post(
    "/scan-all",
    response_model=DatabaseIntegrityReportResponse,
    summary="Scan all tables",
    description="Performs full database scan for all orphaned records."
)
async def scan_all(
    tables: Optional[List[str]] = Query(None, description="Specific tables to scan"),
    strategy: ScanStrategy = Query(default=ScanStrategy.NOT_EXISTS),
    current_user: Any = Depends(require_admin)
) -> DatabaseIntegrityReportResponse:
    """Scan all tables for orphans."""
    scanner = await get_orphan_scanner()
    
    report = await scanner.scan_all(tables=tables, strategy=strategy)
    
    return DatabaseIntegrityReportResponse(
        scan_time=report.scan_time,
        tables_scanned=report.tables_scanned,
        relationships_checked=report.relationships_checked,
        total_orphans_found=report.total_orphans_found,
        integrity_score=report.integrity_score,
        duration_ms=report.duration_ms,
        table_results=[ScanResultResponse(**r.to_dict()) for r in report.table_results],
    )


@router.post(
    "/cleanup",
    response_model=CleanupResultResponse,
    summary="Clean up orphans",
    description="Cleans up orphaned records using specified strategy."
)
async def cleanup_orphans(
    request: CleanupRequest,
    current_user: Any = Depends(require_admin)
) -> CleanupResultResponse:
    """Clean up orphaned records."""
    scanner = await get_orphan_scanner()
    
    result = await scanner.cleanup_orphans(
        table_name=request.table_name,
        foreign_key_column=request.foreign_key_column,
        referenced_table=request.referenced_table,
        strategy=request.strategy,
        dry_run=request.dry_run,
        batch_size=request.batch_size,
        create_backup=request.create_backup,
    )
    
    return CleanupResultResponse(**result.to_dict())


@router.get(
    "/scan-history",
    response_model=List[Dict[str, Any]],
    summary="Get scan history",
    description="Returns history of orphan scan operations."
)
async def get_scan_history(
    table_name: Optional[str] = Query(None, description="Filter by table"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get scan history."""
    scanner = await get_orphan_scanner()
    history = await scanner.get_scan_history(table_name, limit)
    return history


@router.get(
    "/cleanup-history",
    response_model=List[Dict[str, Any]],
    summary="Get cleanup history",
    description="Returns history of cleanup operations."
)
async def get_cleanup_history(
    table_name: Optional[str] = Query(None, description="Filter by table"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get cleanup history."""
    scanner = await get_orphan_scanner()
    history = await scanner.get_cleanup_history(table_name, limit)
    return history


@router.get(
    "/statistics",
    response_model=OrphanScannerStatsResponse,
    summary="Get scanner statistics",
    description="Returns overall orphan scanner statistics."
)
async def get_statistics(
    current_user: Any = Depends(require_admin)
) -> OrphanScannerStatsResponse:
    """Get orphan scanner statistics."""
    scanner = await get_orphan_scanner()
    stats = await scanner.get_statistics()
    return OrphanScannerStatsResponse(**stats)


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize orphan scanner",
    description="Initializes scanner and discovers relationships."
)
async def initialize_scanner(
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Initialize orphan scanner."""
    scanner = await get_orphan_scanner()
    await scanner.initialize()
    return {
        "status": "initialized",
        "relationships_discovered": str(len(scanner._relationships)),
    }
