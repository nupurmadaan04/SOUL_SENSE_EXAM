"""
API Deprecation Header Standardization Module

This module provides standardized API deprecation handling with RFC-compliant
headers, sunset dates, and migration guidance for API versioning lifecycle.

Features:
- RFC 8594 compliant deprecation headers
- Sunset date tracking
- Migration path documentation
- Client notification system
- Deprecation policy enforcement
- API version lifecycle management
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logger = logging.getLogger(__name__)


class DeprecationStatus(str, Enum):
    """Deprecation lifecycle status."""
    ACTIVE = "active"              # Fully supported
    DEPRECATED = "deprecated"      # Deprecated but functional
    SUNSET = "sunset"              # Sunset period (limited support)
    REMOVED = "removed"            # No longer available


class DeprecationSeverity(str, Enum):
    """Severity of deprecation notice."""
    INFO = "info"          # Informational, no immediate action
    WARNING = "warning"    # Action recommended soon
    CRITICAL = "critical"  # Action required immediately


class ApiVersionStatus(str, Enum):
    """Status of an API version."""
    STABLE = "stable"          # Current stable version
    MAINTENANCE = "maintenance"  # Maintenance mode only
    DEPRECATED = "deprecated"    # Deprecated, migration needed
    END_OF_LIFE = "end_of_life"  # No longer supported


@dataclass
class ApiVersion:
    """API version definition."""
    version: str
    base_path: str
    status: ApiVersionStatus
    
    # Lifecycle dates
    released_at: datetime
    deprecated_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    
    # Documentation
    documentation_url: str = ""
    release_notes_url: str = ""
    
    # Statistics
    request_count: int = 0
    unique_clients: Set[str] = field(default_factory=set)


@dataclass
class DeprecationNotice:
    """Deprecation notice for an endpoint or field."""
    notice_id: str
    endpoint_path: str
    http_method: str
    
    # Deprecation details
    status: DeprecationStatus
    severity: DeprecationSeverity
    
    # Timeline
    deprecated_since: datetime
    sunset_date: Optional[datetime] = None
    removal_date: Optional[datetime] = None
    
    # Migration guidance
    alternative_endpoint: str = ""
    alternative_version: str = ""
    migration_guide_url: str = ""
    breaking_changes: List[str] = field(default_factory=list)
    
    # Communication
    notice_message: str = ""
    suggested_action: str = ""
    
    # Client tracking
    affected_clients: Set[str] = field(default_factory=set)
    notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None


@dataclass
class DeprecatedField:
    """Deprecated field in a request/response."""
    field_name: str
    field_location: str  # request_body, response_body, query_param, header
    
    # Deprecation info
    deprecated_since: datetime
    removal_version: str = ""
    
    # Migration
    replacement_field: str = ""
    transformation_required: bool = False
    transformation_logic: str = ""  # Description of transformation needed


@dataclass
class ClientDeprecationNotice:
    """Deprecation notice sent to a specific client."""
    client_id: str
    notice_id: str
    sent_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


class DeprecationHeaders:
    """
    Standardized deprecation headers following RFC 8594.
    
    Headers:
    - Deprecation: true (indicates deprecation)
    - Sunset: <date> (when endpoint will be removed)
    - Link: </new/endpoint>; rel="successor-version" (migration path)
    """
    
    DEPRECATION = "Deprecation"
    SUNSET = "Sunset"
    LINK = "Link"
    API_DEPRECATED = "API-Deprecated"
    API_SUNSET = "API-Sunset"
    API_ALTERNATIVE = "API-Alternative"


class ApiDeprecationManager:
    """
    Central manager for API deprecation standardization.
    
    Provides functionality for:
    - RFC-compliant deprecation header management
    - API version lifecycle tracking
    - Deprecation notice management
    - Client notification tracking
    - Migration path documentation
    """
    
    def __init__(self):
        self.api_versions: Dict[str, ApiVersion] = {}
        self.deprecation_notices: Dict[str, DeprecationNotice] = {}
        self.deprecated_fields: Dict[str, List[DeprecatedField]] = {}
        self.client_notices: Dict[str, List[ClientDeprecationNotice]] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Default deprecation policy
        self.default_deprecation_period_days = 90
        self.default_sunset_period_days = 30
        self.notification_lead_time_days = 30
    
    async def initialize(self):
        """Initialize the API deprecation manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default API versions
            await self._create_default_versions()
            
            self._initialized = True
            logger.info("ApiDeprecationManager initialized successfully")
    
    async def _create_default_versions(self):
        """Create default API versions."""
        versions = [
            ApiVersion(
                version="v1",
                base_path="/api/v1",
                status=ApiVersionStatus.DEPRECATED,
                released_at=datetime(2024, 1, 1),
                deprecated_at=datetime(2025, 1, 1),
                sunset_at=datetime(2025, 6, 1),
                documentation_url="/docs/api/v1"
            ),
            ApiVersion(
                version="v2",
                base_path="/api/v2",
                status=ApiVersionStatus.STABLE,
                released_at=datetime(2025, 1, 1),
                documentation_url="/docs/api/v2"
            ),
        ]
        
        for version in versions:
            self.api_versions[version.version] = version
    
    # API Version Management
    
    async def register_api_version(
        self,
        version: str,
        base_path: str,
        status: ApiVersionStatus,
        released_at: Optional[datetime] = None,
        deprecated_at: Optional[datetime] = None,
        sunset_at: Optional[datetime] = None,
        documentation_url: str = ""
    ) -> ApiVersion:
        """Register a new API version."""
        async with self._lock:
            api_version = ApiVersion(
                version=version,
                base_path=base_path,
                status=status,
                released_at=released_at or datetime.utcnow(),
                deprecated_at=deprecated_at,
                sunset_at=sunset_at,
                documentation_url=documentation_url
            )
            
            self.api_versions[version] = api_version
            logger.info(f"Registered API version: {version}")
            return api_version
    
    async def get_api_version(self, version: str) -> Optional[ApiVersion]:
        """Get API version by version string."""
        return self.api_versions.get(version)
    
    async def list_api_versions(
        self,
        status: Optional[ApiVersionStatus] = None
    ) -> List[ApiVersion]:
        """List API versions with optional filtering."""
        versions = list(self.api_versions.values())
        
        if status:
            versions = [v for v in versions if v.status == status]
        
        return sorted(versions, key=lambda v: v.released_at, reverse=True)
    
    async def deprecate_version(
        self,
        version: str,
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None
    ) -> Optional[ApiVersion]:
        """Mark an API version as deprecated."""
        async with self._lock:
            api_version = self.api_versions.get(version)
            if not api_version:
                return None
            
            api_version.status = ApiVersionStatus.DEPRECATED
            api_version.deprecated_at = deprecation_date or datetime.utcnow()
            
            if sunset_date:
                api_version.sunset_at = sunset_date
            else:
                api_version.sunset_at = api_version.deprecated_at + timedelta(
                    days=self.default_deprecation_period_days
                )
            
            logger.info(f"Deprecated API version: {version}")
            return api_version
    
    # Deprecation Notice Management
    
    async def create_deprecation_notice(
        self,
        notice_id: str,
        endpoint_path: str,
        http_method: str,
        status: DeprecationStatus,
        severity: DeprecationSeverity,
        deprecated_since: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None,
        alternative_endpoint: str = "",
        alternative_version: str = "",
        migration_guide_url: str = "",
        notice_message: str = "",
        breaking_changes: Optional[List[str]] = None
    ) -> DeprecationNotice:
        """Create a deprecation notice for an endpoint."""
        async with self._lock:
            # Calculate default dates if not provided
            deprecated_since = deprecated_since or datetime.utcnow()
            
            if not sunset_date and status in [DeprecationStatus.DEPRECATED, DeprecationStatus.SUNSET]:
                sunset_date = deprecated_since + timedelta(days=self.default_deprecation_period_days)
            
            notice = DeprecationNotice(
                notice_id=notice_id,
                endpoint_path=endpoint_path,
                http_method=http_method,
                status=status,
                severity=severity,
                deprecated_since=deprecated_since,
                sunset_date=sunset_date,
                removal_date=sunset_date + timedelta(days=self.default_sunset_period_days) if sunset_date else None,
                alternative_endpoint=alternative_endpoint,
                alternative_version=alternative_version,
                migration_guide_url=migration_guide_url,
                notice_message=notice_message,
                breaking_changes=breaking_changes or []
            )
            
            self.deprecation_notices[notice_id] = notice
            logger.info(f"Created deprecation notice: {notice_id} for {http_method} {endpoint_path}")
            return notice
    
    async def get_deprecation_notice(self, notice_id: str) -> Optional[DeprecationNotice]:
        """Get deprecation notice by ID."""
        return self.deprecation_notices.get(notice_id)
    
    async def find_deprecation_notice(
        self,
        endpoint_path: str,
        http_method: str
    ) -> Optional[DeprecationNotice]:
        """Find deprecation notice for an endpoint."""
        for notice in self.deprecation_notices.values():
            if notice.endpoint_path == endpoint_path and notice.http_method == http_method:
                return notice
        return None
    
    async def list_deprecation_notices(
        self,
        status: Optional[DeprecationStatus] = None,
        severity: Optional[DeprecationSeverity] = None
    ) -> List[DeprecationNotice]:
        """List deprecation notices with optional filtering."""
        notices = list(self.deprecation_notices.values())
        
        if status:
            notices = [n for n in notices if n.status == status]
        
        if severity:
            notices = [n for n in notices if n.severity == severity]
        
        return sorted(notices, key=lambda n: n.deprecated_since, reverse=True)
    
    # Header Generation
    
    async def get_deprecation_headers(
        self,
        endpoint_path: str,
        http_method: str,
        client_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Get RFC-compliant deprecation headers for an endpoint."""
        headers = {}
        
        notice = await self.find_deprecation_notice(endpoint_path, http_method)
        if not notice:
            return headers
        
        # Deprecation header (RFC 8594)
        if notice.status in [DeprecationStatus.DEPRECATED, DeprecationStatus.SUNSET]:
            headers[DeprecationHeaders.DEPRECATION] = "true"
            headers[DeprecationHeaders.API_DEPRECATED] = notice.deprecated_since.isoformat()
        
        # Sunset header (RFC 8594)
        if notice.sunset_date:
            headers[DeprecationHeaders.SUNSET] = notice.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
            headers[DeprecationHeaders.API_SUNSET] = notice.sunset_date.isoformat()
        
        # Alternative endpoint
        if notice.alternative_endpoint:
            headers[DeprecationHeaders.API_ALTERNATIVE] = notice.alternative_endpoint
            
            # Link header with successor-version relation
            link_value = f'<{notice.alternative_endpoint}>; rel="successor-version"'
            if notice.migration_guide_url:
                link_value += f', <{notice.migration_guide_url}>; rel="migration-guide"'
            headers[DeprecationHeaders.LINK] = link_value
        
        return headers
    
    # Deprecated Field Management
    
    async def register_deprecated_field(
        self,
        endpoint_path: str,
        field_name: str,
        field_location: str,
        deprecated_since: datetime,
        removal_version: str = "",
        replacement_field: str = ""
    ) -> DeprecatedField:
        """Register a deprecated field for an endpoint."""
        field = DeprecatedField(
            field_name=field_name,
            field_location=field_location,
            deprecated_since=deprecated_since,
            removal_version=removal_version,
            replacement_field=replacement_field
        )
        
        if endpoint_path not in self.deprecated_fields:
            self.deprecated_fields[endpoint_path] = []
        
        self.deprecated_fields[endpoint_path].append(field)
        logger.info(f"Registered deprecated field: {field_name} on {endpoint_path}")
        return field
    
    async def get_deprecated_fields(self, endpoint_path: str) -> List[DeprecatedField]:
        """Get deprecated fields for an endpoint."""
        return self.deprecated_fields.get(endpoint_path, [])
    
    # Client Notification
    
    async def notify_client(
        self,
        client_id: str,
        notice_id: str
    ) -> Optional[ClientDeprecationNotice]:
        """Record that a client has been notified of deprecation."""
        notice = self.deprecation_notices.get(notice_id)
        if not notice:
            return None
        
        client_notice = ClientDeprecationNotice(
            client_id=client_id,
            notice_id=notice_id,
            sent_at=datetime.utcnow()
        )
        
        if client_id not in self.client_notices:
            self.client_notices[client_id] = []
        
        self.client_notices[client_id].append(client_notice)
        
        notice.affected_clients.add(client_id)
        notice.notification_sent = True
        notice.notification_sent_at = datetime.utcnow()
        
        logger.info(f"Client {client_id} notified of deprecation: {notice_id}")
        return client_notice
    
    async def acknowledge_notice(
        self,
        client_id: str,
        notice_id: str
    ) -> bool:
        """Mark a deprecation notice as acknowledged by a client."""
        client_notice_list = self.client_notices.get(client_id, [])
        
        for client_notice in client_notice_list:
            if client_notice.notice_id == notice_id:
                client_notice.acknowledged = True
                client_notice.acknowledged_at = datetime.utcnow()
                logger.info(f"Client {client_id} acknowledged deprecation: {notice_id}")
                return True
        
        return False
    
    # Request/Response Middleware Support
    
    async def process_request(
        self,
        request: Request,
        client_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Process request and return deprecation headers for response."""
        endpoint_path = request.url.path
        http_method = request.method
        
        # Track API version usage
        for version in self.api_versions.values():
            if endpoint_path.startswith(version.base_path):
                version.request_count += 1
                if client_id:
                    version.unique_clients.add(client_id)
                break
        
        # Get deprecation headers
        headers = await self.get_deprecation_headers(endpoint_path, http_method, client_id)
        
        # Notify client if applicable
        notice = await self.find_deprecation_notice(endpoint_path, http_method)
        if notice and client_id and not notice.notification_sent:
            await self.notify_client(client_id, notice.notice_id)
        
        return headers
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get API deprecation statistics."""
        notices = list(self.deprecation_notices.values())
        versions = list(self.api_versions.values())
        
        # Calculate days until sunset for deprecated endpoints
        now = datetime.utcnow()
        upcoming_sunsets = [
            n for n in notices
            if n.sunset_date and n.sunset_date > now
        ]
        
        return {
            "api_versions": {
                "total": len(versions),
                "by_status": {
                    status.value: len([v for v in versions if v.status == status])
                    for status in ApiVersionStatus
                }
            },
            "deprecation_notices": {
                "total": len(notices),
                "by_status": {
                    status.value: len([n for n in notices if n.status == status])
                    for status in DeprecationStatus
                },
                "by_severity": {
                    severity.value: len([n for n in notices if n.severity == severity])
                    for severity in DeprecationSeverity
                },
                "upcoming_sunsets_30_days": len([
                    n for n in upcoming_sunsets
                    if (n.sunset_date - now).days <= 30
                ]),
                "upcoming_sunsets_90_days": len([
                    n for n in upcoming_sunsets
                    if (n.sunset_date - now).days <= 90
                ])
            },
            "affected_clients": sum(len(n.affected_clients) for n in notices),
            "notification_coverage": len([
                n for n in notices if n.notification_sent
            ]) / len(notices) * 100 if notices else 0
        }


# Global manager instance
_deprecation_manager: Optional[ApiDeprecationManager] = None


async def get_deprecation_manager() -> ApiDeprecationManager:
    """Get or create the global API deprecation manager."""
    global _deprecation_manager
    if _deprecation_manager is None:
        _deprecation_manager = ApiDeprecationManager()
        await _deprecation_manager.initialize()
    return _deprecation_manager


def reset_deprecation_manager():
    """Reset the global API deprecation manager (for testing)."""
    global _deprecation_manager
    _deprecation_manager = None


# FastAPI Middleware

class DeprecationMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically add deprecation headers to responses."""
    
    def __init__(self, app, client_id_header: str = "X-Client-ID"):
        super().__init__(app)
        self.client_id_header = client_id_header
        self._manager: Optional[ApiDeprecationManager] = None
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add deprecation headers to response."""
        # Get or initialize manager
        if self._manager is None:
            self._manager = await get_deprecation_manager()
        
        # Get client ID from header
        client_id = request.headers.get(self.client_id_header)
        
        # Process request
        headers = await self._manager.process_request(request, client_id)
        
        # Get response
        response = await call_next(request)
        
        # Add deprecation headers
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        
        return response


# Helper decorator for deprecated endpoints

def deprecated(
    notice_id: str,
    alternative_endpoint: str = "",
    sunset_date: Optional[datetime] = None,
    severity: DeprecationSeverity = DeprecationSeverity.WARNING
):
    """
    Decorator to mark a FastAPI endpoint as deprecated.
    
    Usage:
        @router.get("/old-endpoint")
        @deprecated(
            notice_id="deprecate-old-endpoint",
            alternative_endpoint="/api/v2/new-endpoint",
            sunset_date=datetime(2025, 6, 1)
        )
        async def old_endpoint():
            return {"message": "This endpoint is deprecated"}
    """
    def decorator(func):
        func._deprecated = True
        func._deprecation_notice_id = notice_id
        func._alternative_endpoint = alternative_endpoint
        func._sunset_date = sunset_date
        func._severity = severity
        return func
    return decorator
