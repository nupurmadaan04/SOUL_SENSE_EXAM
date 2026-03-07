"""
Regional Compliance API Router

Provides REST API endpoints for managing regional compliance profiles,
consent management, RTD requests, data exports, and compliance auditing.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from pydantic import BaseModel, Field

from backend.fastapi.api.utils.regional_compliance import (
    RegionalComplianceManager,
    get_compliance_manager,
    ComplianceRegion,
    ComplianceAction,
    DataCategory,
    ConsentStatus,
    ComplianceProfile,
    ComplianceRequirement,
    ConsentRecord,
    DataRetentionPolicy,
    RTDRequest,
    DataExportRequest,
    ComplianceAuditLog,
    ComplianceProfilePack
)

router = APIRouter(prefix="/regional-compliance", tags=["regional-compliance"])


# Pydantic Models for Request/Response

class ComplianceProfileCreate(BaseModel):
    name: str
    description: str
    region: ComplianceRegion
    jurisdiction: str


class ComplianceProfileResponse(BaseModel):
    profile_id: str
    name: str
    description: str
    region: str
    jurisdiction: str
    effective_date: datetime
    version: str
    active: bool
    created_at: datetime
    updated_at: datetime


class ConsentRecordCreate(BaseModel):
    user_id: str
    region: ComplianceRegion
    data_categories: List[DataCategory]
    purposes: List[str]
    consent_mechanism: str = "checkbox"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_days: Optional[int] = None


class ConsentRecordResponse(BaseModel):
    consent_id: str
    user_id: str
    region: str
    data_categories: List[str]
    purposes: List[str]
    status: str
    granted_at: Optional[datetime]
    expires_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    consent_mechanism: str
    created_at: datetime


class RTDRequestCreate(BaseModel):
    user_id: str
    region: ComplianceRegion
    data_categories: Optional[List[DataCategory]] = None
    deletion_scope: str = "all"
    verification_method: Optional[str] = None


class RTDRequestResponse(BaseModel):
    request_id: str
    user_id: str
    region: str
    requested_at: datetime
    status: str
    data_categories: List[str]
    deletion_scope: str
    completion_deadline: Optional[datetime]
    completed_at: Optional[datetime]


class ExportRequestCreate(BaseModel):
    user_id: str
    region: ComplianceRegion
    data_categories: Optional[List[DataCategory]] = None
    format: str = "json"


class ExportRequestResponse(BaseModel):
    request_id: str
    user_id: str
    region: str
    requested_at: datetime
    status: str
    data_categories: List[str]
    format: str
    download_url: Optional[str]
    file_size_bytes: Optional[int]
    expires_at: Optional[datetime]


class ComplianceValidationRequest(BaseModel):
    region: ComplianceRegion
    action: ComplianceAction
    data_categories: List[DataCategory]
    user_id: Optional[str] = None
    purpose: Optional[str] = None


class ComplianceValidationResponse(BaseModel):
    compliant: bool
    violations: List[Dict[str, Any]]
    requirements: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]


class AuditLogQuery(BaseModel):
    region: Optional[ComplianceRegion] = None
    action: Optional[ComplianceAction] = None
    user_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100


# Profile Management Endpoints

@router.post("/profiles", response_model=ComplianceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_compliance_profile(
    data: ComplianceProfileCreate,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Create a new compliance profile."""
    profile = await manager.create_profile(
        name=data.name,
        description=data.description,
        region=data.region,
        jurisdiction=data.jurisdiction
    )
    return _profile_to_response(profile)


@router.get("/profiles", response_model=List[ComplianceProfileResponse])
async def list_compliance_profiles(
    region: Optional[ComplianceRegion] = None,
    active_only: bool = True,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """List compliance profiles."""
    if region:
        profiles = await manager.get_profiles_by_region(region)
    else:
        profiles = await manager.list_profiles(active_only=active_only)
    return [_profile_to_response(p) for p in profiles]


@router.get("/profiles/{profile_id}", response_model=ComplianceProfileResponse)
async def get_compliance_profile(
    profile_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get a compliance profile by ID."""
    profile = await manager.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_to_response(profile)


@router.patch("/profiles/{profile_id}")
async def update_compliance_profile(
    profile_id: str,
    updates: Dict[str, Any],
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Update a compliance profile."""
    profile = await manager.update_profile(profile_id, updates)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profile_to_response(profile)


@router.post("/profiles/{profile_id}/deactivate")
async def deactivate_compliance_profile(
    profile_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Deactivate a compliance profile."""
    success = await manager.deactivate_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deactivated successfully"}


@router.get("/packs")
async def list_compliance_packs():
    """List available predefined compliance packs."""
    packs = ComplianceProfilePack.list_packs()
    return {"packs": packs}


@router.get("/packs/{pack_name}")
async def get_compliance_pack(pack_name: str):
    """Get details of a predefined compliance pack."""
    pack = ComplianceProfilePack.get_pack(pack_name)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    return pack


# Consent Management Endpoints

@router.post("/consent", response_model=ConsentRecordResponse, status_code=status.HTTP_201_CREATED)
async def record_consent(
    data: ConsentRecordCreate,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Record user consent."""
    consent = await manager.record_consent(
        user_id=data.user_id,
        region=data.region,
        data_categories=data.data_categories,
        purposes=data.purposes,
        consent_mechanism=data.consent_mechanism,
        ip_address=data.ip_address,
        user_agent=data.user_agent,
        expires_days=data.expires_days
    )
    return _consent_to_response(consent)


@router.post("/consent/{consent_id}/withdraw")
async def withdraw_consent(
    consent_id: str,
    reason: Optional[str] = None,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Withdraw user consent."""
    consent = await manager.withdraw_consent(consent_id, reason)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")
    return _consent_to_response(consent)


@router.get("/consent/{consent_id}", response_model=ConsentRecordResponse)
async def get_consent_record(
    consent_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get a consent record by ID."""
    consent = await manager.get_consent(consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")
    return _consent_to_response(consent)


@router.get("/users/{user_id}/consent", response_model=List[ConsentRecordResponse])
async def get_user_consents(
    user_id: str,
    active_only: bool = True,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get all consent records for a user."""
    consents = await manager.get_user_consents(user_id, active_only=active_only)
    return [_consent_to_response(c) for c in consents]


@router.post("/consent/check")
async def check_consent(
    user_id: str,
    data_categories: List[DataCategory],
    purpose: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Check if user has given consent for specific data categories and purpose."""
    has_consent = await manager.check_consent(user_id, data_categories, purpose)
    return {"has_consent": has_consent, "user_id": user_id, "purpose": purpose}


# RTD (Right to Deletion) Endpoints

@router.post("/rtd", response_model=RTDRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_rtd_request(
    data: RTDRequestCreate,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Create a Right to Deletion request."""
    request = await manager.create_rtd_request(
        user_id=data.user_id,
        region=data.region,
        data_categories=data.data_categories,
        deletion_scope=data.deletion_scope,
        verification_method=data.verification_method
    )
    return _rtd_to_response(request)


@router.get("/rtd/{request_id}", response_model=RTDRequestResponse)
async def get_rtd_request(
    request_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get an RTD request by ID."""
    request = await manager.get_rtd_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="RTD request not found")
    return _rtd_to_response(request)


@router.patch("/rtd/{request_id}/status")
async def update_rtd_status(
    request_id: str,
    status: str,
    details: Optional[str] = None,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Update RTD request status."""
    request = await manager.update_rtd_status(request_id, status, details)
    if not request:
        raise HTTPException(status_code=404, detail="RTD request not found")
    return _rtd_to_response(request)


@router.get("/users/{user_id}/rtd", response_model=List[RTDRequestResponse])
async def get_user_rtd_requests(
    user_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get all RTD requests for a user."""
    requests = [r for r in manager.rtd_requests.values() if r.user_id == user_id]
    return [_rtd_to_response(r) for r in requests]


# Data Export Endpoints

@router.post("/exports", response_model=ExportRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_export_request(
    data: ExportRequestCreate,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Create a data export request."""
    request = await manager.create_export_request(
        user_id=data.user_id,
        region=data.region,
        data_categories=data.data_categories,
        format=data.format
    )
    return _export_to_response(request)


@router.get("/exports/{request_id}", response_model=ExportRequestResponse)
async def get_export_request(
    request_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get an export request by ID."""
    request = await manager.get_export_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Export request not found")
    return _export_to_response(request)


@router.post("/exports/{request_id}/complete")
async def complete_export_request(
    request_id: str,
    download_url: str,
    file_size_bytes: int,
    checksum: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Mark an export request as complete."""
    request = await manager.complete_export_request(
        request_id, download_url, file_size_bytes, checksum
    )
    if not request:
        raise HTTPException(status_code=404, detail="Export request not found")
    return _export_to_response(request)


@router.get("/users/{user_id}/exports", response_model=List[ExportRequestResponse])
async def get_user_export_requests(
    user_id: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get all export requests for a user."""
    requests = [e for e in manager.export_requests.values() if e.user_id == user_id]
    return [_export_to_response(r) for r in requests]


# Compliance Validation Endpoints

@router.post("/validate", response_model=ComplianceValidationResponse)
async def validate_processing(
    data: ComplianceValidationRequest,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Validate if a data processing action is compliant."""
    result = await manager.validate_processing(
        region=data.region,
        action=data.action,
        data_categories=data.data_categories,
        user_id=data.user_id,
        purpose=data.purpose
    )
    return result


@router.post("/validate/residency")
async def validate_data_residency(
    region: ComplianceRegion,
    current_zone: str,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Validate if data is in an allowed residency zone."""
    is_valid = await manager.validate_data_residency(region, current_zone)
    zones = await manager.get_allowed_residency_zones(region)
    return {
        "valid": is_valid,
        "region": region.value,
        "current_zone": current_zone,
        "allowed_zones": zones
    }


# Audit Log Endpoints

@router.post("/audit/logs")
async def query_audit_logs(
    query: AuditLogQuery,
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Query compliance audit logs."""
    logs = await manager.get_audit_logs(
        region=query.region,
        action=query.action,
        user_id=query.user_id,
        start_time=query.start_time,
        end_time=query.end_time,
        limit=query.limit
    )
    return {
        "logs": [_audit_to_dict(log) for log in logs],
        "count": len(logs)
    }


@router.post("/audit/log")
async def log_compliance_action(
    region: ComplianceRegion,
    action: ComplianceAction,
    user_id: Optional[str] = None,
    data_subject_id: Optional[str] = None,
    data_categories: Optional[List[DataCategory]] = None,
    legal_basis: Optional[str] = None,
    processing_purpose: Optional[str] = None,
    risk_level: str = "low",
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Log a compliance-related action."""
    log_entry = await manager.log_compliance_action(
        region=region,
        action=action,
        user_id=user_id,
        data_subject_id=data_subject_id,
        data_categories=data_categories,
        legal_basis=legal_basis,
        processing_purpose=processing_purpose,
        risk_level=risk_level
    )
    return _audit_to_dict(log_entry)


# Statistics Endpoints

@router.get("/statistics")
async def get_compliance_statistics(
    manager: RegionalComplianceManager = Depends(get_compliance_manager)
):
    """Get compliance statistics."""
    stats = await manager.get_statistics()
    return stats


@router.get("/regions")
async def list_regions():
    """List all supported compliance regions."""
    return {"regions": [r.value for r in ComplianceRegion]}


@router.get("/data-categories")
async def list_data_categories():
    """List all data categories."""
    return {"categories": [c.value for c in DataCategory]}


@router.get("/compliance-actions")
async def list_compliance_actions():
    """List all compliance actions."""
    return {"actions": [a.value for a in ComplianceAction]}


# Helper Functions

def _profile_to_response(profile: ComplianceProfile) -> Dict[str, Any]:
    """Convert ComplianceProfile to response dict."""
    return {
        "profile_id": profile.profile_id,
        "name": profile.name,
        "description": profile.description,
        "region": profile.region.value,
        "jurisdiction": profile.jurisdiction,
        "effective_date": profile.effective_date,
        "version": profile.version,
        "active": profile.active,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


def _consent_to_response(consent: ConsentRecord) -> Dict[str, Any]:
    """Convert ConsentRecord to response dict."""
    return {
        "consent_id": consent.consent_id,
        "user_id": consent.user_id,
        "region": consent.region.value,
        "data_categories": [dc.value for dc in consent.data_categories],
        "purposes": consent.purposes,
        "status": consent.status.value,
        "granted_at": consent.granted_at,
        "expires_at": consent.expires_at,
        "withdrawn_at": consent.withdrawn_at,
        "consent_mechanism": consent.consent_mechanism,
        "created_at": consent.created_at
    }


def _rtd_to_response(request: RTDRequest) -> Dict[str, Any]:
    """Convert RTDRequest to response dict."""
    return {
        "request_id": request.request_id,
        "user_id": request.user_id,
        "region": request.region.value,
        "requested_at": request.requested_at,
        "status": request.status,
        "data_categories": [dc.value for dc in request.data_categories],
        "deletion_scope": request.deletion_scope,
        "completion_deadline": request.completion_deadline,
        "completed_at": request.completed_at
    }


def _export_to_response(request: DataExportRequest) -> Dict[str, Any]:
    """Convert DataExportRequest to response dict."""
    return {
        "request_id": request.request_id,
        "user_id": request.user_id,
        "region": request.region.value,
        "requested_at": request.requested_at,
        "status": request.status,
        "data_categories": [dc.value for dc in request.data_categories],
        "format": request.format,
        "download_url": request.download_url,
        "file_size_bytes": request.file_size_bytes,
        "expires_at": request.expires_at
    }


def _audit_to_dict(log: ComplianceAuditLog) -> Dict[str, Any]:
    """Convert ComplianceAuditLog to dict."""
    return {
        "log_id": log.log_id,
        "timestamp": log.timestamp,
        "region": log.region.value,
        "action": log.action.value,
        "user_id": log.user_id,
        "data_subject_id": log.data_subject_id,
        "data_categories": [dc.value for dc in log.data_categories],
        "legal_basis": log.legal_basis,
        "processing_purpose": log.processing_purpose,
        "risk_level": log.risk_level,
        "checksum": log.checksum,
        "verified": log.verified
    }
