"""
Regional Compliance Profile Packs Module

This module provides a framework for managing regional compliance requirements
including GDPR (EU), CCPA (California), LGPD (Brazil), PIPEDA (Canada), and others.

Features:
- Regional compliance profile management
- Data residency controls
- Consent management workflows
- Data retention policies by region
- Right to deletion (RTD) handling
- Data portability exports
- Compliance auditing and reporting
"""

import asyncio
import json
import hashlib
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import re

# Configure logging
logger = logging.getLogger(__name__)


class ComplianceRegion(str, Enum):
    """Supported compliance regions."""
    EU = "eu"  # GDPR
    USA_CALIFORNIA = "usa_california"  # CCPA/CPRA
    USA = "usa"  # US Federal
    BRAZIL = "brazil"  # LGPD
    CANADA = "canada"  # PIPEDA
    UK = "uk"  # UK GDPR
    AUSTRALIA = "australia"  # Privacy Act
    JAPAN = "japan"  # APPI
    SINGAPORE = "singapore"  # PDPA
    INDIA = "india"  # DPDP Act
    GLOBAL = "global"  # Generic fallback


class DataCategory(str, Enum):
    """Categories of personal data."""
    IDENTIFIERS = "identifiers"  # Name, email, phone
    BIOMETRIC = "biometric"  # Fingerprints, facial recognition
    HEALTH = "health"  # Medical records
    FINANCIAL = "financial"  # Payment info
    BEHAVIORAL = "behavioral"  # Browsing history, preferences
    LOCATION = "location"  # Geolocation data
    DEMOGRAPHIC = "demographic"  # Age, gender
    SENSITIVE = "sensitive"  # Race, religion, politics
    CHILDREN = "children"  # Data about minors


class ComplianceAction(str, Enum):
    """Compliance-related actions."""
    DATA_COLLECTION = "data_collection"
    DATA_PROCESSING = "data_processing"
    DATA_SHARING = "data_sharing"
    DATA_RETENTION = "data_retention"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    CONSENT_WITHDRAWAL = "consent_withdrawal"
    ACCESS_REQUEST = "access_request"
    RECTIFICATION = "rectification"


class ConsentStatus(str, Enum):
    """Consent status values."""
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"
    NOT_REQUIRED = "not_required"


class ComplianceStatus(str, Enum):
    """Overall compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    EXEMPT = "exempt"
    UNDER_REMEDIATION = "under_remediation"


@dataclass
class ComplianceRequirement:
    """Individual compliance requirement."""
    requirement_id: str
    name: str
    description: str
    region: ComplianceRegion
    data_categories: List[DataCategory]
    actions: List[ComplianceAction]
    requires_consent: bool = False
    requires_explicit_consent: bool = False
    min_age_requirement: Optional[int] = None
    retention_days: Optional[int] = None
    data_residency_required: bool = False
    allowed_processing_reasons: List[str] = field(default_factory=list)
    prohibited_processing_reasons: List[str] = field(default_factory=list)
    documentation_required: bool = False
    dpo_notification_required: bool = False
    data_protection_impact_assessment: bool = False
    cross_border_transfer_restrictions: bool = False
    audit_frequency_days: int = 365
    penalties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    active: bool = True


@dataclass
class ConsentRecord:
    """User consent record."""
    consent_id: str
    user_id: str
    region: ComplianceRegion
    data_categories: List[DataCategory]
    purposes: List[str]
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    consent_version: str = "1.0"
    consent_mechanism: str = "checkbox"  # checkbox, signature, verbal, etc.
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    proof_document_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataRetentionPolicy:
    """Data retention policy for a region."""
    policy_id: str
    region: ComplianceRegion
    data_category: DataCategory
    retention_period_days: int
    retention_basis: str  # legal_obligation, consent, contract, etc.
    auto_delete: bool = False
    archival_required: bool = False
    archival_period_days: Optional[int] = None
    review_required: bool = False
    review_frequency_days: int = 365
    exceptions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceProfile:
    """Complete compliance profile for a region."""
    profile_id: str
    name: str
    description: str
    region: ComplianceRegion
    jurisdiction: str
    effective_date: datetime
    requirements: List[ComplianceRequirement] = field(default_factory=list)
    retention_policies: List[DataRetentionPolicy] = field(default_factory=list)
    data_residency_zones: List[str] = field(default_factory=list)
    approved_transfer_mechanisms: List[str] = field(default_factory=list)
    dpo_contact: Optional[str] = None
    supervisory_authority: Optional[str] = None
    penalty_framework: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    active: bool = True


@dataclass
class RTDRequest:
    """Right to Deletion (RTD) request."""
    request_id: str
    user_id: str
    region: ComplianceRegion
    requested_at: datetime
    status: str  # pending, in_progress, completed, rejected
    data_categories: List[DataCategory] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)  # Legal holds, etc.
    verification_method: Optional[str] = None
    verification_completed_at: Optional[datetime] = None
    completion_deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deletion_scope: str = "all"  # all, specific_categories
    deletion_method: str = "hard"  # hard, soft, anonymize
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataExportRequest:
    """Data portability export request."""
    request_id: str
    user_id: str
    region: ComplianceRegion
    requested_at: datetime
    status: str  # pending, processing, ready, expired
    data_categories: List[DataCategory] = field(default_factory=list)
    format: str = "json"  # json, csv, xml
    encryption_required: bool = True
    expires_at: Optional[datetime] = None
    download_url: Optional[str] = None
    download_count: int = 0
    file_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class ComplianceAuditLog:
    """Compliance audit log entry."""
    log_id: str
    timestamp: datetime
    region: ComplianceRegion
    action: ComplianceAction
    user_id: Optional[str] = None
    data_subject_id: Optional[str] = None
    data_categories: List[DataCategory] = field(default_factory=list)
    legal_basis: Optional[str] = None
    consent_id: Optional[str] = None
    processing_purpose: Optional[str] = None
    data_residency_zone: Optional[str] = None
    recipient_third_parties: List[str] = field(default_factory=list)
    retention_period_days: Optional[int] = None
    automated_decision: bool = False
    risk_level: str = "low"  # low, medium, high
    checksum: Optional[str] = None
    verified: bool = False
    verification_timestamp: Optional[datetime] = None


class ComplianceProfilePack:
    """Predefined compliance profile pack."""
    
    PACKS = {
        "gdpr": {
            "name": "GDPR (EU)",
            "region": ComplianceRegion.EU,
            "description": "General Data Protection Regulation for European Union",
            "requirements": [
                {
                    "name": "Lawful Basis for Processing",
                    "description": "Must have valid legal basis for data processing",
                    "requires_consent": True,
                    "requires_explicit_consent": True,
                    "data_categories": [DataCategory.SENSITIVE, DataCategory.BIOMETRIC],
                    "actions": [ComplianceAction.DATA_PROCESSING],
                    "dpo_notification_required": True
                },
                {
                    "name": "Data Minimization",
                    "description": "Collect only necessary data",
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.DATA_COLLECTION],
                    "documentation_required": True
                },
                {
                    "name": "Right to Deletion",
                    "description": "Users can request deletion of their data",
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.DATA_DELETION],
                    "retention_days": 30  # Must respond within 30 days
                },
                {
                    "name": "Data Portability",
                    "description": "Users can request their data in portable format",
                    "data_categories": [DataCategory.IDENTIFIERS, DataCategory.BEHAVIORAL],
                    "actions": [ComplianceAction.DATA_EXPORT],
                    "retention_days": 30
                }
            ]
        },
        "ccpa": {
            "name": "CCPA/CPRA (California)",
            "region": ComplianceRegion.USA_CALIFORNIA,
            "description": "California Consumer Privacy Act / Privacy Rights Act",
            "requirements": [
                {
                    "name": "Right to Know",
                    "description": "Consumers have right to know what data is collected",
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.ACCESS_REQUEST],
                    "retention_days": 45
                },
                {
                    "name": "Right to Delete",
                    "description": "Consumers can request deletion",
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.DATA_DELETION],
                    "retention_days": 45
                },
                {
                    "name": "Right to Opt-Out",
                    "description": "Consumers can opt-out of sale/sharing",
                    "data_categories": [DataCategory.IDENTIFIERS, DataCategory.BEHAVIORAL],
                    "actions": [ComplianceAction.DATA_SHARING],
                    "requires_consent": False
                },
                {
                    "name": "Sensitive Personal Information",
                    "description": "Special handling for sensitive data",
                    "requires_explicit_consent": True,
                    "data_categories": [DataCategory.SENSITIVE, DataCategory.BIOMETRIC, DataCategory.HEALTH],
                    "actions": [ComplianceAction.DATA_PROCESSING, ComplianceAction.DATA_SHARING]
                }
            ]
        },
        "lgpd": {
            "name": "LGPD (Brazil)",
            "region": ComplianceRegion.BRAZIL,
            "description": "Lei Geral de Proteção de Dados",
            "requirements": [
                {
                    "name": "Legal Basis",
                    "description": "Must have legal basis for processing",
                    "requires_consent": True,
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.DATA_PROCESSING],
                    "dpo_notification_required": True
                },
                {
                    "name": "Data Subject Rights",
                    "description": "Comprehensive data subject rights",
                    "data_categories": list(DataCategory),
                    "actions": [
                        ComplianceAction.ACCESS_REQUEST,
                        ComplianceAction.RECTIFICATION,
                        ComplianceAction.DATA_DELETION,
                        ComplianceAction.DATA_EXPORT
                    ],
                    "retention_days": 15
                }
            ]
        },
        "pipeda": {
            "name": "PIPEDA (Canada)",
            "region": ComplianceRegion.CANADA,
            "description": "Personal Information Protection and Electronic Documents Act",
            "requirements": [
                {
                    "name": "Consent Principle",
                    "description": "Knowledge and consent required",
                    "requires_consent": True,
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.DATA_COLLECTION, ComplianceAction.DATA_PROCESSING]
                },
                {
                    "name": "Limited Collection",
                    "description": "Collect only necessary information",
                    "data_categories": list(DataCategory),
                    "actions": [ComplianceAction.DATA_COLLECTION],
                    "documentation_required": True
                }
            ]
        }
    }

    @classmethod
    def get_pack(cls, pack_name: str) -> Optional[Dict[str, Any]]:
        """Get a predefined compliance pack."""
        return cls.PACKS.get(pack_name.lower())

    @classmethod
    def list_packs(cls) -> List[str]:
        """List available compliance packs."""
        return list(cls.PACKS.keys())


class RegionalComplianceManager:
    """
    Central manager for regional compliance operations.
    
    Provides functionality for:
    - Managing compliance profiles
    - Handling consent management
    - Processing RTD (Right to Deletion) requests
    - Managing data exports
    - Compliance auditing
    - Data residency enforcement
    """
    
    def __init__(self):
        self.profiles: Dict[str, ComplianceProfile] = {}
        self.requirements: Dict[str, ComplianceRequirement] = {}
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.retention_policies: Dict[str, DataRetentionPolicy] = {}
        self.rtd_requests: Dict[str, RTDRequest] = {}
        self.export_requests: Dict[str, DataExportRequest] = {}
        self.audit_logs: List[ComplianceAuditLog] = []
        self.user_consents: Dict[str, List[str]] = defaultdict(list)  # user_id -> consent_ids
        self.region_profiles: Dict[ComplianceRegion, List[str]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the compliance manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Load default compliance packs
            await self._load_default_profiles()
            
            self._initialized = True
            logger.info("RegionalComplianceManager initialized successfully")
    
    async def _load_default_profiles(self):
        """Load default compliance profiles from packs."""
        for pack_name, pack_data in ComplianceProfilePack.PACKS.items():
            profile_id = f"profile_{pack_name}_{datetime.utcnow().strftime('%Y%m%d')}"
            
            requirements = []
            for idx, req_data in enumerate(pack_data["requirements"]):
                req = ComplianceRequirement(
                    requirement_id=f"req_{pack_name}_{idx}",
                    name=req_data["name"],
                    description=req_data["description"],
                    region=pack_data["region"],
                    data_categories=req_data.get("data_categories", []),
                    actions=req_data.get("actions", []),
                    requires_consent=req_data.get("requires_consent", False),
                    requires_explicit_consent=req_data.get("requires_explicit_consent", False),
                    retention_days=req_data.get("retention_days"),
                    dpo_notification_required=req_data.get("dpo_notification_required", False),
                    documentation_required=req_data.get("documentation_required", False)
                )
                requirements.append(req)
                self.requirements[req.requirement_id] = req
            
            profile = ComplianceProfile(
                profile_id=profile_id,
                name=pack_data["name"],
                description=pack_data["description"],
                region=pack_data["region"],
                jurisdiction=pack_data["region"].value,
                effective_date=datetime.utcnow(),
                requirements=requirements,
                data_residency_zones=self._get_residency_zones(pack_data["region"])
            )
            
            self.profiles[profile_id] = profile
            self.region_profiles[pack_data["region"]].append(profile_id)
    
    def _get_residency_zones(self, region: ComplianceRegion) -> List[str]:
        """Get data residency zones for a region."""
        zones = {
            ComplianceRegion.EU: ["eu-west-1", "eu-central-1", "eu-north-1"],
            ComplianceRegion.USA_CALIFORNIA: ["us-west-1", "us-west-2"],
            ComplianceRegion.USA: ["us-east-1", "us-west-1", "us-west-2"],
            ComplianceRegion.BRAZIL: ["sa-east-1"],
            ComplianceRegion.CANADA: ["ca-central-1"],
            ComplianceRegion.UK: ["eu-west-2"],
            ComplianceRegion.AUSTRALIA: ["ap-southeast-2"],
            ComplianceRegion.JAPAN: ["ap-northeast-1"],
            ComplianceRegion.SINGAPORE: ["ap-southeast-1"],
            ComplianceRegion.INDIA: ["ap-south-1"],
            ComplianceRegion.GLOBAL: ["global"]
        }
        return zones.get(region, ["global"])
    
    # Profile Management
    
    async def create_profile(
        self,
        name: str,
        description: str,
        region: ComplianceRegion,
        jurisdiction: str,
        requirements: Optional[List[ComplianceRequirement]] = None
    ) -> ComplianceProfile:
        """Create a new compliance profile."""
        async with self._lock:
            profile_id = f"profile_{region.value}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            profile = ComplianceProfile(
                profile_id=profile_id,
                name=name,
                description=description,
                region=region,
                jurisdiction=jurisdiction,
                effective_date=datetime.utcnow(),
                requirements=requirements or [],
                data_residency_zones=self._get_residency_zones(region)
            )
            
            self.profiles[profile_id] = profile
            self.region_profiles[region].append(profile_id)
            
            logger.info(f"Created compliance profile: {profile_id}")
            return profile
    
    async def get_profile(self, profile_id: str) -> Optional[ComplianceProfile]:
        """Get a compliance profile by ID."""
        return self.profiles.get(profile_id)
    
    async def get_profiles_by_region(
        self,
        region: ComplianceRegion
    ) -> List[ComplianceProfile]:
        """Get all compliance profiles for a region."""
        profile_ids = self.region_profiles.get(region, [])
        return [self.profiles[pid] for pid in profile_ids if pid in self.profiles]
    
    async def list_profiles(
        self,
        active_only: bool = True
    ) -> List[ComplianceProfile]:
        """List all compliance profiles."""
        profiles = list(self.profiles.values())
        if active_only:
            profiles = [p for p in profiles if p.active]
        return profiles
    
    async def update_profile(
        self,
        profile_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ComplianceProfile]:
        """Update a compliance profile."""
        async with self._lock:
            profile = self.profiles.get(profile_id)
            if not profile:
                return None
            
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.utcnow()
            logger.info(f"Updated compliance profile: {profile_id}")
            return profile
    
    async def deactivate_profile(self, profile_id: str) -> bool:
        """Deactivate a compliance profile."""
        async with self._lock:
            profile = self.profiles.get(profile_id)
            if not profile:
                return False
            
            profile.active = False
            profile.updated_at = datetime.utcnow()
            logger.info(f"Deactivated compliance profile: {profile_id}")
            return True
    
    # Consent Management
    
    async def record_consent(
        self,
        user_id: str,
        region: ComplianceRegion,
        data_categories: List[DataCategory],
        purposes: List[str],
        consent_mechanism: str = "checkbox",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_days: Optional[int] = None
    ) -> ConsentRecord:
        """Record user consent."""
        async with self._lock:
            consent_id = f"consent_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            
            now = datetime.utcnow()
            expires_at = now + timedelta(days=expires_days) if expires_days else None
            
            consent = ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                region=region,
                data_categories=data_categories,
                purposes=purposes,
                status=ConsentStatus.GRANTED,
                granted_at=now,
                expires_at=expires_at,
                consent_mechanism=consent_mechanism,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.consent_records[consent_id] = consent
            self.user_consents[user_id].append(consent_id)
            
            logger.info(f"Recorded consent: {consent_id} for user: {user_id}")
            return consent
    
    async def withdraw_consent(
        self,
        consent_id: str,
        reason: Optional[str] = None
    ) -> Optional[ConsentRecord]:
        """Withdraw user consent."""
        async with self._lock:
            consent = self.consent_records.get(consent_id)
            if not consent:
                return None
            
            consent.status = ConsentStatus.WITHDRAWN
            consent.withdrawn_at = datetime.utcnow()
            consent.updated_at = datetime.utcnow()
            
            if reason:
                consent.metadata["withdrawal_reason"] = reason
            
            logger.info(f"Withdrawn consent: {consent_id}")
            return consent
    
    async def get_consent(self, consent_id: str) -> Optional[ConsentRecord]:
        """Get a consent record by ID."""
        return self.consent_records.get(consent_id)
    
    async def get_user_consents(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        consent_ids = self.user_consents.get(user_id, [])
        consents = [self.consent_records[cid] for cid in consent_ids if cid in self.consent_records]
        
        if active_only:
            consents = [c for c in consents if c.status == ConsentStatus.GRANTED]
        
        return consents
    
    async def check_consent(
        self,
        user_id: str,
        data_categories: List[DataCategory],
        purpose: str
    ) -> bool:
        """Check if user has given consent for data categories and purpose."""
        consents = await self.get_user_consents(user_id, active_only=True)
        
        for consent in consents:
            # Check if consent covers all required data categories
            if not all(dc in consent.data_categories for dc in data_categories):
                continue
            
            # Check if consent covers the purpose
            if purpose not in consent.purposes:
                continue
            
            # Check if consent is expired
            if consent.expires_at and consent.expires_at < datetime.utcnow():
                consent.status = ConsentStatus.EXPIRED
                continue
            
            return True
        
        return False
    
    # RTD (Right to Deletion) Management
    
    async def create_rtd_request(
        self,
        user_id: str,
        region: ComplianceRegion,
        data_categories: Optional[List[DataCategory]] = None,
        deletion_scope: str = "all",
        verification_method: Optional[str] = None
    ) -> RTDRequest:
        """Create a Right to Deletion request."""
        async with self._lock:
            request_id = f"rtd_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Get retention period from profile
            profiles = await self.get_profiles_by_region(region)
            retention_days = 30  # Default
            for profile in profiles:
                for req in profile.requirements:
                    if ComplianceAction.DATA_DELETION in req.actions and req.retention_days:
                        retention_days = min(retention_days, req.retention_days)
            
            request = RTDRequest(
                request_id=request_id,
                user_id=user_id,
                region=region,
                requested_at=datetime.utcnow(),
                status="pending",
                data_categories=data_categories if data_categories is not None else list(DataCategory),
                deletion_scope=deletion_scope,
                verification_method=verification_method,
                completion_deadline=datetime.utcnow() + timedelta(days=retention_days),
                audit_trail=[{
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "request_created",
                    "details": f"RTD request created for user {user_id}"
                }]
            )
            
            self.rtd_requests[request_id] = request
            logger.info(f"Created RTD request: {request_id}")
            return request
    
    async def get_rtd_request(self, request_id: str) -> Optional[RTDRequest]:
        """Get an RTD request by ID."""
        return self.rtd_requests.get(request_id)
    
    async def update_rtd_status(
        self,
        request_id: str,
        status: str,
        details: Optional[str] = None
    ) -> Optional[RTDRequest]:
        """Update RTD request status."""
        async with self._lock:
            request = self.rtd_requests.get(request_id)
            if not request:
                return None
            
            request.status = status
            request.updated_at = datetime.utcnow()
            
            if status == "completed":
                request.completed_at = datetime.utcnow()
            
            request.audit_trail.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": f"status_updated_to_{status}",
                "details": details or f"Status updated to {status}"
            })
            
            logger.info(f"Updated RTD request {request_id} to status: {status}")
            return request
    
    # Data Export Management
    
    async def create_export_request(
        self,
        user_id: str,
        region: ComplianceRegion,
        data_categories: Optional[List[DataCategory]] = None,
        format: str = "json"
    ) -> DataExportRequest:
        """Create a data export request."""
        async with self._lock:
            request_id = f"export_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Get retention period from profile
            profiles = await self.get_profiles_by_region(region)
            retention_days = 30  # Default
            for profile in profiles:
                for req in profile.requirements:
                    if ComplianceAction.DATA_EXPORT in req.actions and req.retention_days:
                        retention_days = min(retention_days, req.retention_days)
            
            request = DataExportRequest(
                request_id=request_id,
                user_id=user_id,
                region=region,
                requested_at=datetime.utcnow(),
                status="pending",
                data_categories=data_categories or [DataCategory.IDENTIFIERS, DataCategory.BEHAVIORAL],
                format=format,
                expires_at=datetime.utcnow() + timedelta(days=retention_days)
            )
            
            self.export_requests[request_id] = request
            logger.info(f"Created export request: {request_id}")
            return request
    
    async def get_export_request(self, request_id: str) -> Optional[DataExportRequest]:
        """Get an export request by ID."""
        return self.export_requests.get(request_id)
    
    async def complete_export_request(
        self,
        request_id: str,
        download_url: str,
        file_size_bytes: int,
        checksum: str
    ) -> Optional[DataExportRequest]:
        """Mark an export request as complete."""
        async with self._lock:
            request = self.export_requests.get(request_id)
            if not request:
                return None
            
            request.status = "ready"
            request.download_url = download_url
            request.file_size_bytes = file_size_bytes
            request.checksum = checksum
            request.completed_at = datetime.utcnow()
            
            logger.info(f"Completed export request: {request_id}")
            return request
    
    # Compliance Auditing
    
    async def log_compliance_action(
        self,
        region: ComplianceRegion,
        action: ComplianceAction,
        user_id: Optional[str] = None,
        data_subject_id: Optional[str] = None,
        data_categories: Optional[List[DataCategory]] = None,
        legal_basis: Optional[str] = None,
        processing_purpose: Optional[str] = None,
        risk_level: str = "low"
    ) -> ComplianceAuditLog:
        """Log a compliance-related action."""
        log_id = f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        log_entry = ComplianceAuditLog(
            log_id=log_id,
            timestamp=datetime.utcnow(),
            region=region,
            action=action,
            user_id=user_id,
            data_subject_id=data_subject_id,
            data_categories=data_categories or [],
            legal_basis=legal_basis,
            processing_purpose=processing_purpose,
            risk_level=risk_level
        )
        
        # Generate checksum for integrity
        log_data = json.dumps({
            "log_id": log_id,
            "timestamp": log_entry.timestamp.isoformat(),
            "region": region.value,
            "action": action.value,
            "user_id": user_id,
            "data_subject_id": data_subject_id
        }, sort_keys=True)
        log_entry.checksum = hashlib.sha256(log_data.encode()).hexdigest()
        
        self.audit_logs.append(log_entry)
        
        # Keep only last 100,000 logs in memory
        if len(self.audit_logs) > 100000:
            self.audit_logs = self.audit_logs[-100000:]
        
        return log_entry
    
    async def get_audit_logs(
        self,
        region: Optional[ComplianceRegion] = None,
        action: Optional[ComplianceAction] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ComplianceAuditLog]:
        """Query compliance audit logs."""
        logs = self.audit_logs
        
        if region:
            logs = [l for l in logs if l.region == region]
        if action:
            logs = [l for l in logs if l.action == action]
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]
        
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    # Compliance Validation
    
    async def validate_processing(
        self,
        region: ComplianceRegion,
        action: ComplianceAction,
        data_categories: List[DataCategory],
        user_id: Optional[str] = None,
        purpose: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate if a data processing action is compliant."""
        result = {
            "compliant": True,
            "violations": [],
            "requirements": [],
            "recommendations": []
        }
        
        # Get applicable profiles
        profiles = await self.get_profiles_by_region(region)
        
        for profile in profiles:
            for requirement in profile.requirements:
                # Check if requirement applies to this action
                if action not in requirement.actions:
                    continue
                
                # Check if requirement applies to data categories
                if not any(dc in requirement.data_categories for dc in data_categories):
                    continue
                
                result["requirements"].append({
                    "requirement_id": requirement.requirement_id,
                    "name": requirement.name,
                    "description": requirement.description
                })
                
                # Check consent requirement
                if requirement.requires_consent and user_id:
                    has_consent = await self.check_consent(user_id, data_categories, purpose or "default")
                    if not has_consent:
                        result["compliant"] = False
                        result["violations"].append({
                            "type": "missing_consent",
                            "requirement": requirement.name,
                            "message": f"Consent required for {action.value} of {', '.join(dc.value for dc in data_categories)}"
                        })
                
                # Check explicit consent for sensitive data
                if requirement.requires_explicit_consent:
                    result["recommendations"].append({
                        "type": "explicit_consent_recommended",
                        "message": f"Explicit consent recommended for processing {', '.join(dc.value for dc in data_categories)}"
                    })
        
        return result
    
    # Data Residency
    
    async def get_allowed_residency_zones(
        self,
        region: ComplianceRegion
    ) -> List[str]:
        """Get allowed data residency zones for a region."""
        profiles = await self.get_profiles_by_region(region)
        zones = set()
        for profile in profiles:
            zones.update(profile.data_residency_zones)
        return list(zones)
    
    async def validate_data_residency(
        self,
        region: ComplianceRegion,
        current_zone: str
    ) -> bool:
        """Validate if data is in an allowed residency zone."""
        allowed_zones = await self.get_allowed_residency_zones(region)
        
        if not allowed_zones or "global" in allowed_zones:
            return True
        
        return current_zone in allowed_zones
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get compliance statistics."""
        return {
            "profiles": {
                "total": len(self.profiles),
                "active": len([p for p in self.profiles.values() if p.active]),
                "by_region": {
                    region.value: len(profiles)
                    for region, profiles in self.region_profiles.items()
                }
            },
            "consents": {
                "total": len(self.consent_records),
                "granted": len([c for c in self.consent_records.values() if c.status == ConsentStatus.GRANTED]),
                "withdrawn": len([c for c in self.consent_records.values() if c.status == ConsentStatus.WITHDRAWN]),
                "expired": len([c for c in self.consent_records.values() if c.status == ConsentStatus.EXPIRED])
            },
            "rtd_requests": {
                "total": len(self.rtd_requests),
                "pending": len([r for r in self.rtd_requests.values() if r.status == "pending"]),
                "in_progress": len([r for r in self.rtd_requests.values() if r.status == "in_progress"]),
                "completed": len([r for r in self.rtd_requests.values() if r.status == "completed"])
            },
            "export_requests": {
                "total": len(self.export_requests),
                "pending": len([e for e in self.export_requests.values() if e.status == "pending"]),
                "ready": len([e for e in self.export_requests.values() if e.status == "ready"])
            },
            "audit_logs": len(self.audit_logs)
        }


# Global manager instance
_compliance_manager: Optional[RegionalComplianceManager] = None


async def get_compliance_manager() -> RegionalComplianceManager:
    """Get or create the global compliance manager."""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = RegionalComplianceManager()
        await _compliance_manager.initialize()
    return _compliance_manager


def reset_compliance_manager():
    """Reset the global compliance manager (for testing)."""
    global _compliance_manager
    _compliance_manager = None
