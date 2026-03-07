"""
Disaster Recovery Runbook API Routes

Provides REST API endpoints for disaster recovery runbook execution,
check management, and recovery validation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

from backend.fastapi.api.utils.disaster_recovery_runbook import (
    CheckStatus, CheckSeverity, CheckCategory, RunbookType,
    CheckStep, DRCheck, CheckExecution, RecoveryObjective, RunbookExecution,
    BackupVerification, DisasterRecoveryManager, get_dr_manager
)
from backend.fastapi.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/disaster-recovery", tags=["disaster-recovery"])


# Pydantic Models

class CheckStepRequest(BaseModel):
    """Request for check step."""
    step_id: str
    name: str
    description: str
    command: str
    expected_result: str
    timeout_seconds: int = 300


class CheckCreateRequest(BaseModel):
    """Request to create DR check."""
    check_id: str
    name: str
    description: str
    category: CheckCategory
    severity: CheckSeverity
    runbook_type: RunbookType
    steps: List[CheckStepRequest]
    schedule_cron: Optional[str] = None


class CheckResponse(BaseModel):
    """Response model for DR check."""
    check_id: str
    name: str
    description: str
    category: CheckCategory
    severity: CheckSeverity
    runbook_type: RunbookType
    enabled: bool
    schedule_cron: Optional[str] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime
    created_by: str


class StepResultResponse(BaseModel):
    """Response model for step result."""
    step_id: str
    name: str
    status: CheckStatus
    expected_result: str
    actual_result: str
    execution_time_ms: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    logs: List[str]


class ExecutionResponse(BaseModel):
    """Response model for check execution."""
    execution_id: str
    check_id: str
    status: CheckStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    passed_steps: int
    failed_steps: int
    skipped_steps: int
    total_execution_time_ms: int
    error_message: str
    rto_seconds: Optional[int] = None
    rpo_seconds: Optional[int] = None


class ExecutionDetailResponse(ExecutionResponse):
    """Detailed execution response with steps."""
    steps_results: List[StepResultResponse]


class RunbookExecutionRequest(BaseModel):
    """Request to execute runbook."""
    runbook_type: RunbookType
    check_ids: List[str]


class RunbookExecutionResponse(BaseModel):
    """Response model for runbook execution."""
    runbook_id: str
    execution_id: str
    runbook_type: RunbookType
    status: CheckStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    overall_rto_met: bool
    overall_rpo_met: bool
    total_downtime_seconds: int
    data_loss_seconds: int


class BackupVerificationRequest(BaseModel):
    """Request to verify backup."""
    backup_id: str
    backup_type: str
    source_system: str
    backup_timestamp: datetime
    size_bytes: int
    integrity_hash: str


class BackupVerificationResponse(BaseModel):
    """Response model for backup verification."""
    backup_id: str
    backup_type: str
    source_system: str
    backup_timestamp: datetime
    verification_status: CheckStatus
    size_bytes: int
    restoration_tested: bool
    restoration_time_seconds: Optional[int] = None
    verified_at: Optional[datetime] = None


class RecoveryObjectiveResponse(BaseModel):
    """Response model for recovery objective."""
    objective_id: str
    name: str
    objective_type: str
    target_seconds: int
    severity: CheckSeverity
    current_value_seconds: Optional[int] = None
    last_measured_at: Optional[datetime] = None
    compliant: bool


class RecoveryObjectiveUpdateRequest(BaseModel):
    """Request to update recovery objective."""
    current_value_seconds: int


class StatisticsResponse(BaseModel):
    """Response model for statistics."""
    checks: Dict[str, Any]
    categories: Dict[str, int]
    backups: Dict[str, int]
    recovery_objectives: Dict[str, Any]
    severity_breakdown: Dict[str, int]


# Helper Functions

def _check_to_response(check: DRCheck) -> CheckResponse:
    """Convert DRCheck to response model."""
    return CheckResponse(
        check_id=check.check_id,
        name=check.name,
        description=check.description,
        category=check.category,
        severity=check.severity,
        runbook_type=check.runbook_type,
        enabled=check.enabled,
        schedule_cron=check.schedule_cron,
        last_run_at=check.last_run_at,
        created_at=check.created_at,
        created_by=check.created_by
    )


def _execution_to_response(execution: CheckExecution) -> ExecutionResponse:
    """Convert CheckExecution to response model."""
    return ExecutionResponse(
        execution_id=execution.execution_id,
        check_id=execution.check_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        passed_steps=execution.passed_steps,
        failed_steps=execution.failed_steps,
        skipped_steps=execution.skipped_steps,
        total_execution_time_ms=execution.total_execution_time_ms,
        error_message=execution.error_message,
        rto_seconds=execution.rto_seconds,
        rpo_seconds=execution.rpo_seconds
    )


# API Routes

@router.post("/checks", response_model=CheckResponse, status_code=status.HTTP_201_CREATED)
async def create_check(
    request: CheckCreateRequest,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(require_admin)
):
    """
    Create a new disaster recovery check.
    
    Requires admin privileges.
    """
    steps = [
        CheckStep(
            step_id=s.step_id,
            name=s.name,
            description=s.description,
            command=s.command,
            expected_result=s.expected_result,
            timeout_seconds=s.timeout_seconds
        ) for s in request.steps
    ]
    
    check = await manager.create_check(
        check_id=request.check_id,
        name=request.name,
        description=request.description,
        category=request.category,
        severity=request.severity,
        runbook_type=request.runbook_type,
        steps=steps,
        schedule_cron=request.schedule_cron,
        created_by=user.get("email", "unknown")
    )
    
    return _check_to_response(check)


@router.get("/checks", response_model=List[CheckResponse])
async def list_checks(
    category: Optional[CheckCategory] = None,
    severity: Optional[CheckSeverity] = None,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """List disaster recovery checks."""
    checks = await manager.list_checks(category=category, severity=severity)
    return [_check_to_response(c) for c in checks]


@router.get("/checks/{check_id}", response_model=CheckResponse)
async def get_check(
    check_id: str,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """Get DR check by ID."""
    check = await manager.get_check(check_id)
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check {check_id} not found"
        )
    
    return _check_to_response(check)


@router.post("/checks/{check_id}/execute", response_model=ExecutionDetailResponse)
async def execute_check(
    check_id: str,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(require_admin)
):
    """
    Execute a disaster recovery check.
    
    Requires admin privileges.
    """
    execution = await manager.execute_check(
        check_id=check_id,
        triggered_by=user.get("email", "unknown")
    )
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Check {check_id} not found"
        )
    
    return ExecutionDetailResponse(
        **_execution_to_response(execution).dict(),
        steps_results=[
            StepResultResponse(
                step_id=s.step_id,
                name=s.name,
                status=s.status,
                expected_result=s.expected_result,
                actual_result=s.actual_result,
                execution_time_ms=s.execution_time_ms,
                started_at=s.started_at,
                completed_at=s.completed_at,
                logs=s.logs
            ) for s in execution.steps_results
        ]
    )


@router.get("/executions", response_model=List[ExecutionResponse])
async def list_executions(
    check_id: Optional[str] = None,
    status: Optional[CheckStatus] = None,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """List check executions."""
    executions = await manager.list_executions(check_id=check_id, status=status)
    return [_execution_to_response(e) for e in executions]


@router.get("/executions/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution(
    execution_id: str,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """Get execution details by ID."""
    execution = await manager.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )
    
    return ExecutionDetailResponse(
        **_execution_to_response(execution).dict(),
        steps_results=[
            StepResultResponse(
                step_id=s.step_id,
                name=s.name,
                status=s.status,
                expected_result=s.expected_result,
                actual_result=s.actual_result,
                execution_time_ms=s.execution_time_ms,
                started_at=s.started_at,
                completed_at=s.completed_at,
                logs=s.logs
            ) for s in execution.steps_results
        ]
    )


@router.post("/runbooks/execute", response_model=RunbookExecutionResponse)
async def execute_runbook(
    request: RunbookExecutionRequest,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(require_admin)
):
    """
    Execute a disaster recovery runbook.
    
    Requires admin privileges.
    """
    runbook_exec = await manager.execute_runbook(
        runbook_type=request.runbook_type,
        check_ids=request.check_ids,
        triggered_by=user.get("email", "unknown")
    )
    
    return RunbookExecutionResponse(
        runbook_id=runbook_exec.runbook_id,
        execution_id=runbook_exec.execution_id,
        runbook_type=runbook_exec.runbook_type,
        status=runbook_exec.status,
        started_at=runbook_exec.started_at,
        completed_at=runbook_exec.completed_at,
        overall_rto_met=runbook_exec.overall_rto_met,
        overall_rpo_met=runbook_exec.overall_rpo_met,
        total_downtime_seconds=runbook_exec.total_downtime_seconds,
        data_loss_seconds=runbook_exec.data_loss_seconds
    )


@router.post("/backups/verify", response_model=BackupVerificationResponse, status_code=status.HTTP_201_CREATED)
async def verify_backup(
    request: BackupVerificationRequest,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(require_admin)
):
    """
    Verify backup integrity.
    
    Requires admin privileges.
    """
    verification = await manager.verify_backup(
        backup_id=request.backup_id,
        backup_type=request.backup_type,
        source_system=request.source_system,
        backup_timestamp=request.backup_timestamp,
        size_bytes=request.size_bytes,
        integrity_hash=request.integrity_hash
    )
    
    return BackupVerificationResponse(
        backup_id=verification.backup_id,
        backup_type=verification.backup_type,
        source_system=verification.source_system,
        backup_timestamp=verification.backup_timestamp,
        verification_status=verification.verification_status,
        size_bytes=verification.size_bytes,
        restoration_tested=verification.restoration_tested,
        restoration_time_seconds=verification.restoration_time_seconds,
        verified_at=verification.verified_at
    )


@router.get("/backups/{backup_id}", response_model=BackupVerificationResponse)
async def get_backup_verification(
    backup_id: str,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """Get backup verification by ID."""
    verification = await manager.get_backup_verification(backup_id)
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup verification {backup_id} not found"
        )
    
    return BackupVerificationResponse(
        backup_id=verification.backup_id,
        backup_type=verification.backup_type,
        source_system=verification.source_system,
        backup_timestamp=verification.backup_timestamp,
        verification_status=verification.verification_status,
        size_bytes=verification.size_bytes,
        restoration_tested=verification.restoration_tested,
        restoration_time_seconds=verification.restoration_time_seconds,
        verified_at=verification.verified_at
    )


@router.get("/recovery-objectives", response_model=List[RecoveryObjectiveResponse])
async def list_recovery_objectives(
    objective_type: Optional[str] = None,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """List recovery objectives."""
    objectives = await manager.list_recovery_objectives(objective_type=objective_type)
    
    return [
        RecoveryObjectiveResponse(
            objective_id=o.objective_id,
            name=o.name,
            objective_type=o.objective_type,
            target_seconds=o.target_seconds,
            severity=o.severity,
            current_value_seconds=o.current_value_seconds,
            last_measured_at=o.last_measured_at,
            compliant=o.compliant
        ) for o in objectives
    ]


@router.get("/recovery-objectives/{objective_id}", response_model=RecoveryObjectiveResponse)
async def get_recovery_objective(
    objective_id: str,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """Get recovery objective by ID."""
    objective = await manager.get_recovery_objective(objective_id)
    
    if not objective:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery objective {objective_id} not found"
        )
    
    return RecoveryObjectiveResponse(
        objective_id=objective.objective_id,
        name=objective.name,
        objective_type=objective.objective_type,
        target_seconds=objective.target_seconds,
        severity=objective.severity,
        current_value_seconds=objective.current_value_seconds,
        last_measured_at=objective.last_measured_at,
        compliant=objective.compliant
    )


@router.post("/recovery-objectives/{objective_id}", response_model=RecoveryObjectiveResponse)
async def update_recovery_objective(
    objective_id: str,
    request: RecoveryObjectiveUpdateRequest,
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(require_admin)
):
    """
    Update recovery objective measurement.
    
    Requires admin privileges.
    """
    objective = await manager.update_recovery_objective(
        objective_id=objective_id,
        current_value_seconds=request.current_value_seconds
    )
    
    if not objective:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery objective {objective_id} not found"
        )
    
    return RecoveryObjectiveResponse(
        objective_id=objective.objective_id,
        name=objective.name,
        objective_type=objective.objective_type,
        target_seconds=objective.target_seconds,
        severity=objective.severity,
        current_value_seconds=objective.current_value_seconds,
        last_measured_at=objective.last_measured_at,
        compliant=objective.compliant
    )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    manager: DisasterRecoveryManager = Depends(get_dr_manager),
    user: Dict = Depends(get_current_user)
):
    """Get disaster recovery statistics."""
    stats = await manager.get_statistics()
    
    return StatisticsResponse(
        checks=stats["checks"],
        categories=stats["categories"],
        backups=stats["backups"],
        recovery_objectives=stats["recovery_objectives"],
        severity_breakdown=stats["severity_breakdown"]
    )


@router.get("/health")
async def health_check(
    manager: DisasterRecoveryManager = Depends(get_dr_manager)
):
    """Health check endpoint for disaster recovery service."""
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "total_checks": len(manager.checks),
        "total_executions": len(manager.executions),
        "total_runbooks": len(manager.runbook_executions)
    }
