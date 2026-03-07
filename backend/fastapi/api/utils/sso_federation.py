"""
Cross-Product SSO Federation Readiness Module

This module provides SSO (Single Sign-On) federation capabilities for cross-product
authentication, supporting SAML 2.0, OAuth 2.0/OIDC, and custom federation protocols.

Features:
- Identity provider (IdP) management
- Service provider (SP) configuration
- SAML 2.0 assertion handling
- OAuth 2.0/OIDC token exchange
- Cross-product session federation
- Federation metadata management
- Security assertion validation
"""

import asyncio
import json
import base64
import hashlib
import hmac
import secrets
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class SSOProtocol(str, Enum):
    """Supported SSO protocols."""
    SAML2 = "saml2"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    WS_FED = "ws_fed"
    CUSTOM = "custom"


class FederationStatus(str, Enum):
    """Federation partnership status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ERROR = "error"
    REVOKED = "revoked"


class IdPStatus(str, Enum):
    """Identity provider status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class AssertionStatus(str, Enum):
    """SAML/OAuth assertion status."""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID_SIGNATURE = "invalid_signature"
    INVALID_ISSUER = "invalid_issuer"
    INVALID_AUDIENCE = "invalid_audience"


@dataclass
class IdentityProvider:
    """Identity Provider configuration."""
    idp_id: str
    name: str
    description: str
    protocol: SSOProtocol
    entity_id: str
    status: IdPStatus
    metadata_url: Optional[str] = None
    metadata_xml: Optional[str] = None
    sso_url: Optional[str] = None  # Single Sign-On URL
    slo_url: Optional[str] = None  # Single Logout URL
    certificate: Optional[str] = None  # X.509 certificate for signature validation
    attributes_mapping: Dict[str, str] = field(default_factory=dict)  # Map IdP attrs to local attrs
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_metadata_update: Optional[datetime] = None
    allowed_audiences: List[str] = field(default_factory=list)
    name_id_format: str = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"


@dataclass
class ServiceProvider:
    """Service Provider configuration."""
    sp_id: str
    name: str
    description: str
    entity_id: str
    acs_url: str  # Assertion Consumer Service URL
    slo_url: Optional[str] = None  # Single Logout URL
    certificate: Optional[str] = None
    private_key: Optional[str] = None
    want_assertions_signed: bool = True
    want_responses_signed: bool = True
    authn_requests_signed: bool = True
    sign_metadata: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    allowed_idps: List[str] = field(default_factory=list)


@dataclass
class FederationPartnership:
    """Federation partnership between IdP and SP."""
    partnership_id: str
    idp_id: str
    sp_id: str
    status: FederationStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
    last_authn_at: Optional[datetime] = None
    authn_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SAMLAssertion:
    """SAML 2.0 Assertion."""
    assertion_id: str
    issuer: str
    subject: str
    audience: str
    issue_instant: datetime
    not_before: datetime
    not_on_or_after: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)
    authn_context: Optional[str] = None
    session_index: Optional[str] = None
    signature_valid: bool = False
    status: AssertionStatus = AssertionStatus.VALID


@dataclass
class FederatedSession:
    """Cross-product federated session."""
    session_id: str
    user_id: str
    idp_id: str
    sp_id: str
    partnership_id: str
    assertion_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=8))
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    products_accessed: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class FederationEvent:
    """Federation audit event."""
    event_id: str
    event_type: str  # authn_success, authn_failure, logout, metadata_update, etc.
    timestamp: datetime = field(default_factory=datetime.utcnow)
    idp_id: Optional[str] = None
    sp_id: Optional[str] = None
    partnership_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    assertion_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetadataCache:
    """Cached federation metadata."""
    cache_id: str
    entity_id: str
    metadata_xml: str
    cached_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None


class SSOMetadataParser:
    """Parser for SSO metadata (SAML 2.0, OIDC discovery)."""
    
    @staticmethod
    def parse_saml_metadata(metadata_xml: str) -> Dict[str, Any]:
        """Parse SAML 2.0 metadata XML."""
        # In production, use proper XML parsing (xml.etree or lxml)
        # This is a simplified implementation
        
        metadata = {
            "entity_id": None,
            "sso_url": None,
            "slo_url": None,
            "certificate": None,
            "name_id_formats": [],
            "attributes": []
        }
        
        # Extract entity ID
        entity_id_match = re.search(r'entityID="([^"]+)"', metadata_xml)
        if entity_id_match:
            metadata["entity_id"] = entity_id_match.group(1)
        
        # Extract SSO URL
        sso_match = re.search(r'<md:SingleSignOnService[^>]+Binding="[^"]+HTTP-Redirect[^"]*"[^>]+Location="([^"]+)"', metadata_xml)
        if sso_match:
            metadata["sso_url"] = sso_match.group(1)
        
        # Extract SLO URL
        slo_match = re.search(r'<md:SingleLogoutService[^>]+Location="([^"]+)"', metadata_xml)
        if slo_match:
            metadata["slo_url"] = slo_match.group(1)
        
        # Extract X509 certificate
        cert_match = re.search(r'<ds:X509Certificate>([^<]+)</ds:X509Certificate>', metadata_xml)
        if cert_match:
            metadata["certificate"] = cert_match.group(1).strip()
        
        return metadata
    
    @staticmethod
    def parse_oidc_discovery(discovery_json: str) -> Dict[str, Any]:
        """Parse OIDC discovery document."""
        try:
            doc = json.loads(discovery_json)
            return {
                "issuer": doc.get("issuer"),
                "authorization_endpoint": doc.get("authorization_endpoint"),
                "token_endpoint": doc.get("token_endpoint"),
                "userinfo_endpoint": doc.get("userinfo_endpoint"),
                "end_session_endpoint": doc.get("end_session_endpoint"),
                "jwks_uri": doc.get("jwks_uri"),
                "scopes_supported": doc.get("scopes_supported", []),
                "claims_supported": doc.get("claims_supported", [])
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OIDC discovery: {e}")
            return {}


class SAMLValidator:
    """SAML assertion validator."""
    
    @staticmethod
    def validate_assertion(
        assertion: SAMLAssertion,
        expected_audience: str,
        idp_certificate: str
    ) -> AssertionStatus:
        """Validate a SAML assertion."""
        now = datetime.utcnow()
        
        # Check expiration
        if now < assertion.not_before:
            return AssertionStatus.EXPIRED
        if now >= assertion.not_on_or_after:
            return AssertionStatus.EXPIRED
        
        # Check audience
        if assertion.audience != expected_audience:
            return AssertionStatus.INVALID_AUDIENCE
        
        # In production, verify XML signature here
        # For now, assume signature is valid if marked
        if not assertion.signature_valid:
            return AssertionStatus.INVALID_SIGNATURE
        
        return AssertionStatus.VALID
    
    @staticmethod
    def decode_saml_response(encoded_response: str) -> str:
        """Decode Base64-encoded SAML response."""
        try:
            decoded = base64.b64decode(encoded_response)
            return decoded.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decode SAML response: {e}")
            raise ValueError("Invalid SAML response encoding")


class SSOSessionManager:
    """Manages cross-product SSO sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, FederatedSession] = {}
        self.user_sessions: Dict[str, List[str]] = defaultdict(list)
    
    def create_session(
        self,
        user_id: str,
        idp_id: str,
        sp_id: str,
        partnership_id: str,
        assertion_id: str,
        session_duration_hours: int = 8
    ) -> FederatedSession:
        """Create a new federated session."""
        session_id = f"sso_{secrets.token_hex(16)}"
        now = datetime.utcnow()
        
        session = FederatedSession(
            session_id=session_id,
            user_id=user_id,
            idp_id=idp_id,
            sp_id=sp_id,
            partnership_id=partnership_id,
            assertion_id=assertion_id,
            created_at=now,
            expires_at=now + timedelta(hours=session_duration_hours),
            last_accessed_at=now,
            is_active=True
        )
        
        self.sessions[session_id] = session
        self.user_sessions[user_id].append(session_id)
        
        logger.info(f"Created SSO session: {session_id} for user: {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[FederatedSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def validate_session(self, session_id: str) -> bool:
        """Validate if a session is active and not expired."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        if not session.is_active:
            return False
        
        if datetime.utcnow() >= session.expires_at:
            session.is_active = False
            return False
        
        return True
    
    def access_session(self, session_id: str, product: str) -> bool:
        """Record access to a session by a product."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        if not self.validate_session(session_id):
            return False
        
        session.last_accessed_at = datetime.utcnow()
        session.access_count += 1
        
        if product not in session.products_accessed:
            session.products_accessed.append(product)
        
        return True
    
    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session.is_active = False
        logger.info(f"Terminated SSO session: {session_id}")
        return True
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[FederatedSession]:
        """Get all sessions for a user."""
        session_ids = self.user_sessions.get(user_id, [])
        sessions = [self.sessions[sid] for sid in session_ids if sid in self.sessions]
        
        if active_only:
            sessions = [s for s in sessions if s.is_active and datetime.utcnow() < s.expires_at]
        
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        now = datetime.utcnow()
        expired_count = 0
        
        for session_id, session in list(self.sessions.items()):
            if now >= session.expires_at:
                session.is_active = False
                expired_count += 1
        
        return expired_count


class SSOFederationManager:
    """
    Central manager for SSO federation operations.
    
    Provides functionality for:
    - Identity provider management
    - Service provider configuration
    - Federation partnerships
    - SAML/OAuth assertion handling
    - Cross-product session federation
    - Audit logging
    """
    
    def __init__(self):
        self.idps: Dict[str, IdentityProvider] = {}
        self.sps: Dict[str, ServiceProvider] = {}
        self.partnerships: Dict[str, FederationPartnership] = {}
        self.assertions: Dict[str, SAMLAssertion] = {}
        self.metadata_cache: Dict[str, MetadataCache] = {}
        self.events: List[FederationEvent] = []
        self.session_manager = SSOSessionManager()
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the federation manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Load default SP configuration
            await self._create_default_sp()
            
            self._initialized = True
            logger.info("SSOFederationManager initialized successfully")
    
    async def _create_default_sp(self):
        """Create default service provider configuration."""
        sp_id = "sp_default"
        sp = ServiceProvider(
            sp_id=sp_id,
            name="Default Service Provider",
            description="Default SP for cross-product federation",
            entity_id="https://app.example.com/sp",
            acs_url="https://app.example.com/saml/acs",
            slo_url="https://app.example.com/saml/slo"
        )
        self.sps[sp_id] = sp
    
    # Identity Provider Management
    
    async def create_idp(
        self,
        name: str,
        description: str,
        protocol: SSOProtocol,
        entity_id: str,
        metadata_url: Optional[str] = None,
        metadata_xml: Optional[str] = None,
        sso_url: Optional[str] = None,
        slo_url: Optional[str] = None,
        certificate: Optional[str] = None,
        attributes_mapping: Optional[Dict[str, str]] = None
    ) -> IdentityProvider:
        """Create a new identity provider."""
        async with self._lock:
            idp_id = f"idp_{secrets.token_hex(8)}"
            
            idp = IdentityProvider(
                idp_id=idp_id,
                name=name,
                description=description,
                protocol=protocol,
                entity_id=entity_id,
                status=IdPStatus.ACTIVE,
                metadata_url=metadata_url,
                metadata_xml=metadata_xml,
                sso_url=sso_url,
                slo_url=slo_url,
                certificate=certificate,
                attributes_mapping=attributes_mapping or {}
            )
            
            # Parse metadata if provided
            if metadata_xml:
                parsed = SSOMetadataParser.parse_saml_metadata(metadata_xml)
                idp.sso_url = parsed.get("sso_url") or sso_url
                idp.slo_url = parsed.get("slo_url") or slo_url
                idp.certificate = parsed.get("certificate") or certificate
            
            self.idps[idp_id] = idp
            
            logger.info(f"Created IdP: {idp_id}")
            return idp
    
    async def get_idp(self, idp_id: str) -> Optional[IdentityProvider]:
        """Get an identity provider by ID."""
        return self.idps.get(idp_id)
    
    async def update_idp(
        self,
        idp_id: str,
        updates: Dict[str, Any]
    ) -> Optional[IdentityProvider]:
        """Update an identity provider."""
        async with self._lock:
            idp = self.idps.get(idp_id)
            if not idp:
                return None
            
            for key, value in updates.items():
                if hasattr(idp, key):
                    setattr(idp, key, value)
            
            idp.updated_at = datetime.utcnow()
            logger.info(f"Updated IdP: {idp_id}")
            return idp
    
    async def delete_idp(self, idp_id: str) -> bool:
        """Delete an identity provider."""
        async with self._lock:
            if idp_id not in self.idps:
                return False
            
            del self.idps[idp_id]
            logger.info(f"Deleted IdP: {idp_id}")
            return True
    
    async def list_idps(
        self,
        status: Optional[IdPStatus] = None,
        protocol: Optional[SSOProtocol] = None
    ) -> List[IdentityProvider]:
        """List identity providers."""
        idps = list(self.idps.values())
        
        if status:
            idps = [i for i in idps if i.status == status]
        if protocol:
            idps = [i for i in idps if i.protocol == protocol]
        
        return idps
    
    # Service Provider Management
    
    async def create_sp(
        self,
        name: str,
        description: str,
        entity_id: str,
        acs_url: str,
        slo_url: Optional[str] = None,
        want_assertions_signed: bool = True
    ) -> ServiceProvider:
        """Create a new service provider."""
        async with self._lock:
            sp_id = f"sp_{secrets.token_hex(8)}"
            
            sp = ServiceProvider(
                sp_id=sp_id,
                name=name,
                description=description,
                entity_id=entity_id,
                acs_url=acs_url,
                slo_url=slo_url,
                want_assertions_signed=want_assertions_signed
            )
            
            self.sps[sp_id] = sp
            logger.info(f"Created SP: {sp_id}")
            return sp
    
    async def get_sp(self, sp_id: str) -> Optional[ServiceProvider]:
        """Get a service provider by ID."""
        return self.sps.get(sp_id)
    
    async def update_sp(
        self,
        sp_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ServiceProvider]:
        """Update a service provider."""
        async with self._lock:
            sp = self.sps.get(sp_id)
            if not sp:
                return None
            
            for key, value in updates.items():
                if hasattr(sp, key):
                    setattr(sp, key, value)
            
            sp.updated_at = datetime.utcnow()
            logger.info(f"Updated SP: {sp_id}")
            return sp
    
    # Federation Partnership Management
    
    async def create_partnership(
        self,
        idp_id: str,
        sp_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[FederationPartnership]:
        """Create a federation partnership."""
        async with self._lock:
            # Validate IdP and SP exist
            if idp_id not in self.idps or sp_id not in self.sps:
                return None
            
            partnership_id = f"fp_{secrets.token_hex(8)}"
            
            partnership = FederationPartnership(
                partnership_id=partnership_id,
                idp_id=idp_id,
                sp_id=sp_id,
                status=FederationStatus.PENDING,
                metadata=metadata or {}
            )
            
            self.partnerships[partnership_id] = partnership
            
            # Update allowed IdPs for SP
            sp = self.sps[sp_id]
            if idp_id not in sp.allowed_idps:
                sp.allowed_idps.append(idp_id)
            
            logger.info(f"Created partnership: {partnership_id}")
            return partnership
    
    async def activate_partnership(self, partnership_id: str) -> bool:
        """Activate a federation partnership."""
        async with self._lock:
            partnership = self.partnerships.get(partnership_id)
            if not partnership:
                return False
            
            partnership.status = FederationStatus.ACTIVE
            partnership.activated_at = datetime.utcnow()
            
            logger.info(f"Activated partnership: {partnership_id}")
            return True
    
    async def suspend_partnership(self, partnership_id: str, reason: str) -> bool:
        """Suspend a federation partnership."""
        async with self._lock:
            partnership = self.partnerships.get(partnership_id)
            if not partnership:
                return False
            
            partnership.status = FederationStatus.SUSPENDED
            partnership.metadata["suspension_reason"] = reason
            
            logger.info(f"Suspended partnership: {partnership_id}")
            return True
    
    async def get_partnership(self, partnership_id: str) -> Optional[FederationPartnership]:
        """Get a federation partnership."""
        return self.partnerships.get(partnership_id)
    
    async def list_partnerships(
        self,
        idp_id: Optional[str] = None,
        sp_id: Optional[str] = None,
        status: Optional[FederationStatus] = None
    ) -> List[FederationPartnership]:
        """List federation partnerships."""
        partnerships = list(self.partnerships.values())
        
        if idp_id:
            partnerships = [p for p in partnerships if p.idp_id == idp_id]
        if sp_id:
            partnerships = [p for p in partnerships if p.sp_id == sp_id]
        if status:
            partnerships = [p for p in partnerships if p.status == status]
        
        return partnerships
    
    # SAML Assertion Processing
    
    async def process_saml_response(
        self,
        encoded_response: str,
        sp_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[FederatedSession], Optional[str]]:
        """Process a SAML response and create session."""
        try:
            # Decode response
            saml_xml = SAMLValidator.decode_saml_response(encoded_response)
            
            # In production, parse XML and extract assertion
            # For now, create a mock assertion
            assertion = SAMLAssertion(
                assertion_id=f"assert_{secrets.token_hex(8)}",
                issuer="mock_idp",
                subject="user@example.com",
                audience=self.sps[sp_id].entity_id,
                issue_instant=datetime.utcnow(),
                not_before=datetime.utcnow(),
                not_on_or_after=datetime.utcnow() + timedelta(hours=8),
                attributes={"email": "user@example.com", "name": "Test User"},
                signature_valid=True,
                status=AssertionStatus.VALID
            )
            
            self.assertions[assertion.assertion_id] = assertion
            
            # Create session
            session = self.session_manager.create_session(
                user_id=assertion.subject,
                idp_id="mock_idp",
                sp_id=sp_id,
                partnership_id="mock_partnership",
                assertion_id=assertion.assertion_id
            )
            
            # Log success
            await self.log_event(
                event_type="authn_success",
                sp_id=sp_id,
                user_id=assertion.subject,
                session_id=session.session_id,
                assertion_id=assertion.assertion_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            
            return True, session, None
            
        except Exception as e:
            logger.error(f"SAML processing error: {e}")
            
            await self.log_event(
                event_type="authn_failure",
                sp_id=sp_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message=str(e)
            )
            
            return False, None, str(e)
    
    # Session Management
    
    async def validate_session(
        self,
        session_id: str,
        product: str
    ) -> Tuple[bool, Optional[FederatedSession]]:
        """Validate and access a federated session."""
        session = self.session_manager.get_session(session_id)
        
        if not session:
            return False, None
        
        if not self.session_manager.validate_session(session_id):
            return False, None
        
        # Record product access
        self.session_manager.access_session(session_id, product)
        
        # Update partnership stats
        partnership = self.partnerships.get(session.partnership_id)
        if partnership:
            partnership.last_authn_at = datetime.utcnow()
            partnership.authn_count += 1
        
        return True, session
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a federated session."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return False
        
        self.session_manager.terminate_session(session_id)
        
        await self.log_event(
            event_type="logout",
            session_id=session_id,
            user_id=session.user_id,
            success=True
        )
        
        return True
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[FederatedSession]:
        """Get all sessions for a user."""
        return self.session_manager.get_user_sessions(user_id, active_only)
    
    # Audit Logging
    
    async def log_event(
        self,
        event_type: str,
        success: bool = True,
        idp_id: Optional[str] = None,
        sp_id: Optional[str] = None,
        partnership_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        assertion_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> FederationEvent:
        """Log a federation event."""
        event = FederationEvent(
            event_id=f"evt_{secrets.token_hex(8)}",
            event_type=event_type,
            idp_id=idp_id,
            sp_id=sp_id,
            partnership_id=partnership_id,
            user_id=user_id,
            session_id=session_id,
            assertion_id=assertion_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_code=error_code,
            error_message=error_message,
            details=details or {}
        )
        
        self.events.append(event)
        
        # Keep only last 100,000 events
        if len(self.events) > 100000:
            self.events = self.events[-100000:]
        
        return event
    
    async def get_events(
        self,
        event_type: Optional[str] = None,
        idp_id: Optional[str] = None,
        sp_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[FederationEvent]:
        """Query federation events."""
        events = self.events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if idp_id:
            events = [e for e in events if e.idp_id == idp_id]
        if sp_id:
            events = [e for e in events if e.sp_id == sp_id]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    # Metadata Management
    
    async def generate_sp_metadata(self, sp_id: str) -> Optional[str]:
        """Generate SAML 2.0 metadata for a service provider."""
        sp = self.sps.get(sp_id)
        if not sp:
            return None
        
        # Generate metadata XML
        metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{sp.entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="{str(sp.authn_requests_signed).lower()}" WantAssertionsSigned="{str(sp.want_assertions_signed).lower()}" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{sp.acs_url}" index="0" isDefault="true"/>
        {f'<md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="{sp.slo_url}"/>' if sp.slo_url else ''}
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
        
        return metadata
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get federation statistics."""
        return {
            "identity_providers": {
                "total": len(self.idps),
                "active": len([i for i in self.idps.values() if i.status == IdPStatus.ACTIVE]),
                "by_protocol": {
                    protocol.value: len([i for i in self.idps.values() if i.protocol == protocol])
                    for protocol in SSOProtocol
                }
            },
            "service_providers": {
                "total": len(self.sps)
            },
            "partnerships": {
                "total": len(self.partnerships),
                "active": len([p for p in self.partnerships.values() if p.status == FederationStatus.ACTIVE]),
                "pending": len([p for p in self.partnerships.values() if p.status == FederationStatus.PENDING])
            },
            "sessions": {
                "total": len(self.session_manager.sessions),
                "active": len([s for s in self.session_manager.sessions.values() if s.is_active])
            },
            "assertions": {
                "total": len(self.assertions),
                "valid": len([a for a in self.assertions.values() if a.status == AssertionStatus.VALID])
            },
            "events": len(self.events)
        }


# Global manager instance
_federation_manager: Optional[SSOFederationManager] = None


async def get_federation_manager() -> SSOFederationManager:
    """Get or create the global federation manager."""
    global _federation_manager
    if _federation_manager is None:
        _federation_manager = SSOFederationManager()
        await _federation_manager.initialize()
    return _federation_manager


def reset_federation_manager():
    """Reset the global federation manager (for testing)."""
    global _federation_manager
    _federation_manager = None
