"""
SSO Federation API Router

Provides REST API endpoints for SSO federation management including:
- Identity provider management
- Service provider configuration
- Federation partnerships
- SAML assertion processing
- Session management
- Audit logging
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.fastapi.api.utils.sso_federation import (
    SSOFederationManager,
    get_federation_manager,
    SSOProtocol,
    IdPStatus,
    FederationStatus,
    IdentityProvider,
    ServiceProvider,
    FederationPartnership,
    FederatedSession,
    FederationEvent
)

router = APIRouter(prefix="/sso-federation", tags=["sso-federation"])


# Pydantic Models

class IdPCreate(BaseModel):
    name: str
    description: str
    protocol: SSOProtocol
    entity_id: str
    metadata_url: Optional[str] = None
    metadata_xml: Optional[str] = None
    sso_url: Optional[str] = None
    slo_url: Optional[str] = None
    certificate: Optional[str] = None
    attributes_mapping: Dict[str, str] = Field(default_factory=dict)


class IdPResponse(BaseModel):
    idp_id: str
    name: str
    description: str
    protocol: str
    entity_id: str
    status: str
    sso_url: Optional[str]
    slo_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class SPCreate(BaseModel):
    name: str
    description: str
    entity_id: str
    acs_url: str
    slo_url: Optional[str] = None
    want_assertions_signed: bool = True


class SPResponse(BaseModel):
    sp_id: str
    name: str
    description: str
    entity_id: str
    acs_url: str
    slo_url: Optional[str]
    want_assertions_signed: bool
    created_at: datetime
    updated_at: datetime


class PartnershipCreate(BaseModel):
    idp_id: str
    sp_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PartnershipResponse(BaseModel):
    partnership_id: str
    idp_id: str
    sp_id: str
    status: str
    created_at: datetime
    activated_at: Optional[datetime]
    authn_count: int


class SAMLProcessRequest(BaseModel):
    saml_response: str
    sp_id: str


class SAMLProcessResponse(BaseModel):
    success: bool
    session_id: Optional[str]
    user_id: Optional[str]
    error: Optional[str]


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    idp_id: str
    sp_id: str
    created_at: datetime
    expires_at: datetime
    last_accessed_at: datetime
    access_count: int
    products_accessed: List[str]
    is_active: bool


class EventQuery(BaseModel):
    event_type: Optional[str] = None
    idp_id: Optional[str] = None
    sp_id: Optional[str] = None
    user_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100


# Identity Provider Endpoints

@router.post("/idps", response_model=IdPResponse, status_code=status.HTTP_201_CREATED)
async def create_idp(
    data: IdPCreate,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Create a new identity provider."""
    idp = await manager.create_idp(
        name=data.name,
        description=data.description,
        protocol=data.protocol,
        entity_id=data.entity_id,
        metadata_url=data.metadata_url,
        metadata_xml=data.metadata_xml,
        sso_url=data.sso_url,
        slo_url=data.slo_url,
        certificate=data.certificate,
        attributes_mapping=data.attributes_mapping
    )
    return _idp_to_response(idp)


@router.get("/idps", response_model=List[IdPResponse])
async def list_idps(
    status: Optional[IdPStatus] = None,
    protocol: Optional[SSOProtocol] = None,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """List identity providers."""
    idps = await manager.list_idps(status=status, protocol=protocol)
    return [_idp_to_response(i) for i in idps]


@router.get("/idps/{idp_id}", response_model=IdPResponse)
async def get_idp(
    idp_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get an identity provider by ID."""
    idp = await manager.get_idp(idp_id)
    if not idp:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    return _idp_to_response(idp)


@router.patch("/idps/{idp_id}")
async def update_idp(
    idp_id: str,
    updates: Dict[str, Any],
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Update an identity provider."""
    idp = await manager.update_idp(idp_id, updates)
    if not idp:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    return _idp_to_response(idp)


@router.delete("/idps/{idp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_idp(
    idp_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Delete an identity provider."""
    success = await manager.delete_idp(idp_id)
    if not success:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    return None


# Service Provider Endpoints

@router.post("/sps", response_model=SPResponse, status_code=status.HTTP_201_CREATED)
async def create_sp(
    data: SPCreate,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Create a new service provider."""
    sp = await manager.create_sp(
        name=data.name,
        description=data.description,
        entity_id=data.entity_id,
        acs_url=data.acs_url,
        slo_url=data.slo_url,
        want_assertions_signed=data.want_assertions_signed
    )
    return _sp_to_response(sp)


@router.get("/sps", response_model=List[SPResponse])
async def list_sps(
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """List service providers."""
    sps = list(manager.sps.values())
    return [_sp_to_response(s) for s in sps]


@router.get("/sps/{sp_id}", response_model=SPResponse)
async def get_sp(
    sp_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get a service provider by ID."""
    sp = await manager.get_sp(sp_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Service provider not found")
    return _sp_to_response(sp)


@router.patch("/sps/{sp_id}")
async def update_sp(
    sp_id: str,
    updates: Dict[str, Any],
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Update a service provider."""
    sp = await manager.update_sp(sp_id, updates)
    if not sp:
        raise HTTPException(status_code=404, detail="Service provider not found")
    return _sp_to_response(sp)


@router.get("/sps/{sp_id}/metadata")
async def get_sp_metadata(
    sp_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get SAML metadata for a service provider."""
    metadata = await manager.generate_sp_metadata(sp_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Service provider not found")
    return {"metadata_xml": metadata}


# Federation Partnership Endpoints

@router.post("/partnerships", response_model=PartnershipResponse, status_code=status.HTTP_201_CREATED)
async def create_partnership(
    data: PartnershipCreate,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Create a federation partnership."""
    partnership = await manager.create_partnership(
        idp_id=data.idp_id,
        sp_id=data.sp_id,
        metadata=data.metadata
    )
    if not partnership:
        raise HTTPException(status_code=404, detail="IdP or SP not found")
    return _partnership_to_response(partnership)


@router.get("/partnerships", response_model=List[PartnershipResponse])
async def list_partnerships(
    idp_id: Optional[str] = None,
    sp_id: Optional[str] = None,
    status: Optional[FederationStatus] = None,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """List federation partnerships."""
    partnerships = await manager.list_partnerships(
        idp_id=idp_id,
        sp_id=sp_id,
        status=status
    )
    return [_partnership_to_response(p) for p in partnerships]


@router.get("/partnerships/{partnership_id}", response_model=PartnershipResponse)
async def get_partnership(
    partnership_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get a federation partnership."""
    partnership = await manager.get_partnership(partnership_id)
    if not partnership:
        raise HTTPException(status_code=404, detail="Partnership not found")
    return _partnership_to_response(partnership)


@router.post("/partnerships/{partnership_id}/activate")
async def activate_partnership(
    partnership_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Activate a federation partnership."""
    success = await manager.activate_partnership(partnership_id)
    if not success:
        raise HTTPException(status_code=404, detail="Partnership not found")
    return {"message": "Partnership activated successfully"}


@router.post("/partnerships/{partnership_id}/suspend")
async def suspend_partnership(
    partnership_id: str,
    reason: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Suspend a federation partnership."""
    success = await manager.suspend_partnership(partnership_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Partnership not found")
    return {"message": "Partnership suspended successfully"}


# SAML Processing Endpoints

@router.post("/saml/process", response_model=SAMLProcessResponse)
async def process_saml_response(
    data: SAMLProcessRequest,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Process a SAML response."""
    success, session, error = await manager.process_saml_response(
        encoded_response=data.saml_response,
        sp_id=data.sp_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {
        "success": success,
        "session_id": session.session_id if session else None,
        "user_id": session.user_id if session else None,
        "error": error
    }


@router.post("/saml/acs/{sp_id}")
async def saml_assertion_consumer_service(
    sp_id: str,
    saml_response: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """SAML Assertion Consumer Service endpoint."""
    success, session, error = await manager.process_saml_response(
        encoded_response=saml_response,
        sp_id=sp_id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "message": "Authentication successful"
    }


# Session Management Endpoints

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get a federated session."""
    session = manager.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_response(session)


@router.post("/sessions/{session_id}/validate")
async def validate_session(
    session_id: str,
    product: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Validate a federated session for a product."""
    valid, session = await manager.validate_session(session_id, product)
    
    if not valid:
        raise HTTPException(status_code=401, detail="Session invalid or expired")
    
    return {
        "valid": True,
        "session": _session_to_response(session)
    }


@router.post("/sessions/{session_id}/terminate")
async def terminate_session(
    session_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Terminate a federated session."""
    success = await manager.terminate_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session terminated successfully"}


@router.get("/users/{user_id}/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    user_id: str,
    active_only: bool = True,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get all sessions for a user."""
    sessions = await manager.get_user_sessions(user_id, active_only)
    return [_session_to_response(s) for s in sessions]


@router.post("/users/{user_id}/logout-all")
async def logout_all_sessions(
    user_id: str,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Terminate all sessions for a user."""
    sessions = await manager.get_user_sessions(user_id, active_only=True)
    terminated = 0
    
    for session in sessions:
        if await manager.terminate_session(session.session_id):
            terminated += 1
    
    return {"terminated_sessions": terminated}


# Audit Log Endpoints

@router.post("/events/query")
async def query_events(
    query: EventQuery,
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Query federation audit events."""
    events = await manager.get_events(
        event_type=query.event_type,
        idp_id=query.idp_id,
        sp_id=query.sp_id,
        user_id=query.user_id,
        start_time=query.start_time,
        end_time=query.end_time,
        limit=query.limit
    )
    
    return {
        "events": [_event_to_dict(e) for e in events],
        "count": len(events)
    }


# Statistics Endpoints

@router.get("/statistics")
async def get_federation_statistics(
    manager: SSOFederationManager = Depends(get_federation_manager)
):
    """Get federation statistics."""
    stats = await manager.get_statistics()
    return stats


@router.get("/protocols")
async def list_protocols():
    """List supported SSO protocols."""
    return {
        "protocols": [
            {"id": p.value, "name": p.value.upper()}
            for p in SSOProtocol
        ]
    }


# Helper Functions

def _idp_to_response(idp: IdentityProvider) -> Dict[str, Any]:
    """Convert IdentityProvider to response dict."""
    return {
        "idp_id": idp.idp_id,
        "name": idp.name,
        "description": idp.description,
        "protocol": idp.protocol.value,
        "entity_id": idp.entity_id,
        "status": idp.status.value,
        "sso_url": idp.sso_url,
        "slo_url": idp.slo_url,
        "created_at": idp.created_at,
        "updated_at": idp.updated_at
    }


def _sp_to_response(sp: ServiceProvider) -> Dict[str, Any]:
    """Convert ServiceProvider to response dict."""
    return {
        "sp_id": sp.sp_id,
        "name": sp.name,
        "description": sp.description,
        "entity_id": sp.entity_id,
        "acs_url": sp.acs_url,
        "slo_url": sp.slo_url,
        "want_assertions_signed": sp.want_assertions_signed,
        "created_at": sp.created_at,
        "updated_at": sp.updated_at
    }


def _partnership_to_response(partnership: FederationPartnership) -> Dict[str, Any]:
    """Convert FederationPartnership to response dict."""
    return {
        "partnership_id": partnership.partnership_id,
        "idp_id": partnership.idp_id,
        "sp_id": partnership.sp_id,
        "status": partnership.status.value,
        "created_at": partnership.created_at,
        "activated_at": partnership.activated_at,
        "authn_count": partnership.authn_count
    }


def _session_to_response(session: FederatedSession) -> Dict[str, Any]:
    """Convert FederatedSession to response dict."""
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "idp_id": session.idp_id,
        "sp_id": session.sp_id,
        "created_at": session.created_at,
        "expires_at": session.expires_at,
        "last_accessed_at": session.last_accessed_at,
        "access_count": session.access_count,
        "products_accessed": session.products_accessed,
        "is_active": session.is_active
    }


def _event_to_dict(event: FederationEvent) -> Dict[str, Any]:
    """Convert FederationEvent to dict."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp,
        "idp_id": event.idp_id,
        "sp_id": event.sp_id,
        "partnership_id": event.partnership_id,
        "user_id": event.user_id,
        "session_id": event.session_id,
        "success": event.success,
        "error_code": event.error_code,
        "error_message": event.error_message
    }
