from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from ..services.db_service import get_db
from ..services.tamper_evident_audit_service import TamperEvidentAuditService
from ..services.audit_service import AuditService
from ..middleware.api_key_middleware import require_scopes
from ..schemas import AuditLogResponse, AuditLogListResponse

router = APIRouter(prefix="/tamper-evident-audit", tags=["tamper-evident-audit"])

@router.get("/chain-status", response_model=Dict[str, Any], dependencies=[Depends(require_scopes(["audit:read"]))])
async def get_chain_status(db: AsyncSession = Depends(get_db)):
    """
    Get comprehensive status of the tamper-evident audit log chain (#1265).

    Returns information about chain integrity, total entries, and validation status.
    Requires audit:read scope.
    """
    try:
        status = await TamperEvidentAuditService.get_chain_status(db)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chain status: {str(e)}")

@router.post("/validate-chain", response_model=Dict[str, Any], dependencies=[Depends(require_scopes(["audit:admin"]))])
async def validate_chain_integrity(max_entries: int = 1000, db: AsyncSession = Depends(get_db)):
    """
    Validate the integrity of the audit log chain (#1265).

    Performs cryptographic validation of hash links and content integrity.
    Requires audit:admin scope.

    - max_entries: Maximum number of entries to validate (default: 1000)
    """
    try:
        is_valid, errors = await TamperEvidentAuditService.validate_chain_integrity(db, max_entries)
        return {
            "valid": is_valid,
            "errors": errors,
            "entries_validated": min(max_entries, len(errors) if errors else max_entries)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chain validation failed: {str(e)}")

@router.get("/detect-tampering", response_model=List[Dict[str, Any]], dependencies=[Depends(require_scopes(["audit:admin"]))])
async def detect_tampering(db: AsyncSession = Depends(get_db)):
    """
    Detect potential tampering in the audit log chain (#1265).

    Returns list of suspicious entries that may have been tampered with.
    Requires audit:admin scope.
    """
    try:
        suspicious_entries = await TamperEvidentAuditService.detect_tampering(db)
        return suspicious_entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tampering detection failed: {str(e)}")

@router.get("/logs/{user_id}", response_model=AuditLogListResponse, dependencies=[Depends(require_scopes(["audit:read"]))])
async def get_user_audit_logs(
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get tamper-evident audit logs for a specific user (#1265).

    Returns paginated list of audit logs with hash chain information.
    Requires audit:read scope.

    - user_id: User ID to get logs for
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    """
    if per_page > 100:
        per_page = 100

    try:
        logs = await AuditService.get_user_logs(user_id, page, per_page, db)

        # Convert to response format with hash information
        log_responses = []
        for log in logs:
            log_responses.append(AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                details=log.details,
                timestamp=log.timestamp,
                previous_hash=log.previous_hash,
                current_hash=log.current_hash,
                chain_hash=log.chain_hash
            ))

        return AuditLogListResponse(
            logs=log_responses,
            page=page,
            per_page=per_page,
            total=len(log_responses)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")

@router.get("/genesis-hash")
async def get_genesis_hash():
    """
    Get the genesis hash used for the tamper-evident audit chain (#1265).

    Public endpoint - no authentication required.
    """
    return {
        "genesis_hash": TamperEvidentAuditService.GENESIS_HASH,
        "description": "SHA-256 genesis hash for tamper-evident audit logging chain"
    }