"""
Vacuum Scheduler API Endpoints (#1415)

Provides REST API endpoints for adaptive vacuum/analyze scheduling,
table statistics monitoring, and maintenance operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db
from ..utils.vacuum_scheduler import (
    get_vacuum_scheduler,
    VacuumScheduler,
    VacuumStrategy,
    SchedulePriority,
    VacuumJob,
    VacuumSchedule,
    SchedulerConfig,
    TableStatistics,
)
from .auth import require_admin


router = APIRouter(tags=["Vacuum Scheduler"], prefix="/admin/vacuum")


# --- Pydantic Schemas ---

class TableStatisticsResponse(BaseModel):
    """Schema for table statistics response."""
    table_name: str
    schema_name: str
    total_size_mb: float
    size_category: str
    live_tuples: int
    dead_tuples: int
    dead_tuple_ratio: float
    bloat_ratio: float
    seq_scans: int
    idx_scans: int
    n_tup_ins: int
    n_tup_upd: int
    n_tup_del: int
    last_vacuum: Optional[str]
    last_analyze: Optional[str]
    vacuum_count: int
    analyze_count: int
    needs_vacuum: bool
    needs_analyze: bool
    collected_at: str


class VacuumJobRequest(BaseModel):
    """Schema for vacuum job request."""
    table_name: str = Field(..., description="Table to vacuum")
    strategy: VacuumStrategy = Field(default=VacuumStrategy.VACUUM_ANALYZE)
    dry_run: bool = Field(default=True, description="Simulate only")


class VacuumJobResponse(BaseModel):
    """Schema for vacuum job response."""
    table_name: str
    strategy: str
    priority: str
    scheduled_at: str
    estimated_duration_seconds: int
    reason: str
    dry_run: bool
    started_at: Optional[str]
    completed_at: Optional[str]
    status: str
    error_message: Optional[str]
    dead_tuples_before: int
    dead_tuples_after: int


class VacuumScheduleResponse(BaseModel):
    """Schema for vacuum schedule response."""
    jobs: List[VacuumJobResponse]
    created_at: str
    total_estimated_duration_seconds: int
    job_count: int


class SchedulerConfigRequest(BaseModel):
    """Schema for scheduler configuration."""
    dead_tuple_ratio_threshold: float = Field(default=20.0, ge=0, le=100)
    dead_tuple_count_threshold: int = Field(default=10000, ge=0)
    vacuum_interval_hours: int = Field(default=24, ge=1)
    analyze_interval_hours: int = Field(default=6, ge=1)
    maintenance_window_start: str = Field(default="02:00")
    maintenance_window_end: str = Field(default="06:00")
    max_concurrent_vacuums: int = Field(default=2, ge=1, le=10)
    dry_run_default: bool = Field(default=True)


class SchedulerStatisticsResponse(BaseModel):
    """Schema for scheduler statistics."""
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    recent_jobs_24h: int
    dead_tuples_removed: int
    tables_monitored: int


class AdaptiveVacuumResponse(BaseModel):
    """Schema for adaptive vacuum response."""
    success: bool
    message: str
    jobs_executed: int
    jobs_successful: int
    jobs_failed: int
    duration_seconds: float
    dry_run: bool
    jobs: List[VacuumJobResponse]


class VacuumSchedulerStatusResponse(BaseModel):
    """Schema for scheduler status."""
    status: str
    config: Dict[str, Any]
    statistics: SchedulerStatisticsResponse
    tables_with_stats: int


# --- API Endpoints ---

@router.get(
    "/status",
    response_model=VacuumSchedulerStatusResponse,
    summary="Get vacuum scheduler status",
    description="Returns scheduler status, configuration, and statistics."
)
async def get_scheduler_status(
    current_user: Any = Depends(require_admin)
) -> VacuumSchedulerStatusResponse:
    """Get vacuum scheduler status."""
    scheduler = await get_vacuum_scheduler()
    
    # Get statistics
    stats = await scheduler.get_statistics()
    
    return VacuumSchedulerStatusResponse(
        status="healthy",
        config=scheduler.config.to_dict(),
        statistics=SchedulerStatisticsResponse(**stats),
        tables_with_stats=len(scheduler._table_stats),
    )


@router.get(
    "/statistics",
    response_model=SchedulerStatisticsResponse,
    summary="Get scheduler statistics",
    description="Returns overall vacuum scheduler statistics."
)
async def get_statistics(
    current_user: Any = Depends(require_admin)
) -> SchedulerStatisticsResponse:
    """Get vacuum scheduler statistics."""
    scheduler = await get_vacuum_scheduler()
    stats = await scheduler.get_statistics()
    return SchedulerStatisticsResponse(**stats)


@router.get(
    "/tables/{table_name}/statistics",
    response_model=TableStatisticsResponse,
    summary="Get table statistics",
    description="Returns statistics for a specific table."
)
async def get_table_statistics(
    table_name: str,
    schema: str = Query(default="public", description="Schema name"),
    current_user: Any = Depends(require_admin)
) -> TableStatisticsResponse:
    """Get statistics for a specific table."""
    scheduler = await get_vacuum_scheduler()
    
    stats = await scheduler.collect_table_statistics(table_name, schema)
    
    if isinstance(stats, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table {schema}.{table_name} not found"
        )
    
    return TableStatisticsResponse(**stats.to_dict())


@router.get(
    "/tables/statistics",
    response_model=List[TableStatisticsResponse],
    summary="Get all table statistics",
    description="Returns statistics for all tables."
)
async def get_all_table_statistics(
    current_user: Any = Depends(require_admin)
) -> List[TableStatisticsResponse]:
    """Get statistics for all tables."""
    scheduler = await get_vacuum_scheduler()
    
    stats_dict = await scheduler.collect_table_statistics()
    
    return [
        TableStatisticsResponse(**stats.to_dict())
        for stats in stats_dict.values()
    ]


@router.post(
    "/collect-statistics",
    response_model=List[TableStatisticsResponse],
    summary="Collect table statistics",
    description="Collects fresh statistics for all tables."
)
async def collect_statistics(
    current_user: Any = Depends(require_admin)
) -> List[TableStatisticsResponse]:
    """Collect fresh statistics for all tables."""
    scheduler = await get_vacuum_scheduler()
    
    stats_dict = await scheduler.collect_table_statistics()
    
    return [
        TableStatisticsResponse(**stats.to_dict())
        for stats in stats_dict.values()
    ]


@router.post(
    "/generate-schedule",
    response_model=VacuumScheduleResponse,
    summary="Generate vacuum schedule",
    description="Generates adaptive vacuum schedule based on table statistics."
)
async def generate_schedule(
    dry_run: bool = Query(default=True, description="Generate dry-run schedule"),
    current_user: Any = Depends(require_admin)
) -> VacuumScheduleResponse:
    """Generate adaptive vacuum schedule."""
    scheduler = await get_vacuum_scheduler()
    
    # Ensure we have stats
    if not scheduler._table_stats:
        await scheduler.collect_table_statistics()
    
    schedule = await scheduler.generate_schedule(dry_run=dry_run)
    
    return VacuumScheduleResponse(
        jobs=[VacuumJobResponse(**job.to_dict()) for job in schedule.jobs],
        created_at=schedule.created_at.isoformat(),
        total_estimated_duration_seconds=schedule.total_estimated_duration_seconds,
        job_count=len(schedule.jobs),
    )


@router.post(
    "/execute-schedule",
    response_model=List[VacuumJobResponse],
    summary="Execute vacuum schedule",
    description="Executes the generated vacuum schedule."
)
async def execute_schedule(
    dry_run: bool = Query(default=True, description="Execute in dry-run mode"),
    max_concurrent: int = Query(default=2, ge=1, le=5),
    current_user: Any = Depends(require_admin)
) -> List[VacuumJobResponse]:
    """Execute the vacuum schedule."""
    scheduler = await get_vacuum_scheduler()
    
    # Generate and execute schedule
    schedule = await scheduler.generate_schedule(dry_run=dry_run)
    
    if not schedule.jobs:
        return []
    
    completed_jobs = await scheduler.execute_schedule(schedule, max_concurrent)
    
    return [VacuumJobResponse(**job.to_dict()) for job in completed_jobs]


@router.post(
    "/vacuum-table",
    response_model=VacuumJobResponse,
    summary="Vacuum specific table",
    description="Runs vacuum/analyze on a specific table."
)
async def vacuum_table(
    request: VacuumJobRequest,
    current_user: Any = Depends(require_admin)
) -> VacuumJobResponse:
    """Vacuum a specific table."""
    scheduler = await get_vacuum_scheduler()
    
    job = await scheduler.vacuum_table(
        table_name=request.table_name,
        strategy=request.strategy,
        dry_run=request.dry_run,
    )
    
    return VacuumJobResponse(**job.to_dict())


@router.post(
    "/adaptive-vacuum",
    response_model=AdaptiveVacuumResponse,
    summary="Run adaptive vacuum",
    description="Runs full adaptive vacuum cycle with statistics collection and scheduling."
)
async def run_adaptive_vacuum(
    dry_run: bool = Query(default=True, description="Run in dry-run mode"),
    max_concurrent: int = Query(default=2, ge=1, le=5),
    current_user: Any = Depends(require_admin)
) -> AdaptiveVacuumResponse:
    """Run full adaptive vacuum cycle."""
    scheduler = await get_vacuum_scheduler()
    
    result = await scheduler.run_adaptive_vacuum(
        dry_run=dry_run,
        max_concurrent=max_concurrent,
    )
    
    return AdaptiveVacuumResponse(
        success=result["success"],
        message=result["message"],
        jobs_executed=result["jobs_executed"],
        jobs_successful=result["jobs_successful"],
        jobs_failed=result["jobs_failed"],
        duration_seconds=result["duration_seconds"],
        dry_run=result["dry_run"],
        jobs=[VacuumJobResponse(**job) for job in result["jobs"]],
    )


@router.get(
    "/history",
    response_model=List[Dict[str, Any]],
    summary="Get job history",
    description="Returns history of vacuum/analyze jobs."
)
async def get_job_history(
    table_name: Optional[str] = Query(None, description="Filter by table"),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: Any = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """Get job execution history."""
    scheduler = await get_vacuum_scheduler()
    history = await scheduler.get_job_history(table_name, limit)
    return history


@router.post(
    "/initialize",
    status_code=status.HTTP_200_OK,
    summary="Initialize vacuum scheduler",
    description="Initializes scheduler and ensures history tables exist."
)
async def initialize_scheduler(
    current_user: Any = Depends(require_admin)
) -> Dict[str, str]:
    """Initialize vacuum scheduler."""
    scheduler = await get_vacuum_scheduler()
    await scheduler.initialize()
    return {
        "status": "initialized",
        "tables_monitored": str(len(scheduler._table_stats)),
    }


@router.get(
    "/tables/needs-maintenance",
    response_model=List[TableStatisticsResponse],
    summary="Get tables needing maintenance",
    description="Returns tables that need vacuum or analyze."
)
async def get_tables_needing_maintenance(
    current_user: Any = Depends(require_admin)
) -> List[TableStatisticsResponse]:
    """Get tables that need vacuum or analyze."""
    scheduler = await get_vacuum_scheduler()
    
    # Ensure we have stats
    if not scheduler._table_stats:
        await scheduler.collect_table_statistics()
    
    needs_maintenance = [
        stats for stats in scheduler._table_stats.values()
        if stats.needs_vacuum or stats.needs_analyze
    ]
    
    return [
        TableStatisticsResponse(**stats.to_dict())
        for stats in needs_maintenance
    ]
