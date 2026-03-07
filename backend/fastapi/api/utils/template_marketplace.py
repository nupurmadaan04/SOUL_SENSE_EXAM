"""
Template Marketplace for Report Exports Module

This module provides a marketplace for report templates with support for:
- Template creation, versioning, and management
- Marketplace with categories, ratings, and reviews
- Export format support (PDF, Excel, CSV, HTML, etc.)
- Template validation and preview generation
- Usage analytics and popularity tracking
- Template sharing and licensing
"""

import asyncio
import json
import hashlib
import uuid
import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class TemplateFormat(str, Enum):
    """Supported export formats."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"
    WORD = "word"
    POWERPOINT = "powerpoint"


class TemplateCategory(str, Enum):
    """Template categories."""
    ASSESSMENT = "assessment"
    ANALYTICS = "analytics"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    EDUCATIONAL = "educational"
    BUSINESS = "business"
    TECHNICAL = "technical"
    CUSTOM = "custom"
    DASHBOARD = "dashboard"
    INVOICE = "invoice"
    REPORT_CARD = "report_card"
    CERTIFICATE = "certificate"


class TemplateStatus(str, Enum):
    """Template status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class LicenseType(str, Enum):
    """Template license types."""
    FREE = "free"
    PAID = "paid"
    SUBSCRIPTION = "subscription"
    ENTERPRISE = "enterprise"
    TRIAL = "trial"
    CUSTOM = "custom"


class ReviewStatus(str, Enum):
    """Review status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


@dataclass
class TemplateVariable:
    """Template variable definition."""
    name: str
    display_name: str
    description: str
    variable_type: str  # string, number, date, boolean, array, object
    required: bool = False
    default_value: Optional[Any] = None
    validation_regex: Optional[str] = None
    allowed_values: List[str] = field(default_factory=list)
    placeholder: Optional[str] = None
    help_text: Optional[str] = None


@dataclass
class TemplateStyle:
    """Template styling configuration."""
    primary_color: str = "#007bff"
    secondary_color: str = "#6c757d"
    font_family: str = "Arial"
    font_size: int = 12
    header_style: Dict[str, Any] = field(default_factory=dict)
    footer_style: Dict[str, Any] = field(default_factory=dict)
    page_size: str = "A4"
    orientation: str = "portrait"
    margins: Dict[str, float] = field(default_factory=lambda: {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0})
    custom_css: Optional[str] = None
    logo_url: Optional[str] = None
    watermark: Optional[str] = None


@dataclass
class TemplateVersion:
    """Template version information."""
    version_id: str
    version_number: str  # semver: 1.0.0
    template_id: str
    created_by: str
    created_at: datetime
    changes_description: str
    status: TemplateStatus
    content: str  # Template content (HTML, markdown, etc.)
    variables: List[TemplateVariable] = field(default_factory=list)
    preview_url: Optional[str] = None
    download_count: int = 0
    is_current: bool = False


@dataclass
class TemplateReview:
    """Template review/rating."""
    review_id: str
    template_id: str
    user_id: str
    rating: int  # 1-5 stars
    title: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    helpful_count: int = 0
    status: ReviewStatus = ReviewStatus.APPROVED


@dataclass
class Template:
    """Report template."""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    formats: List[TemplateFormat]
    status: TemplateStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    license_type: LicenseType = LicenseType.FREE
    price: float = 0.0
    currency: str = "USD"
    tags: List[str] = field(default_factory=list)
    icon_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    demo_data_url: Optional[str] = None
    documentation_url: Optional[str] = None
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    requires_authentication: bool = False
    allowed_user_roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    versions: List[TemplateVersion] = field(default_factory=list)
    reviews: List[TemplateReview] = field(default_factory=list)
    average_rating: float = 0.0
    total_reviews: int = 0
    download_count: int = 0
    view_count: int = 0
    is_featured: bool = False
    is_public: bool = True


@dataclass
class UserTemplateLibrary:
    """User's template library/subscriptions."""
    library_id: str
    user_id: str
    template_id: str
    version_id: str
    acquired_at: datetime
    expires_at: Optional[datetime] = None
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    is_favorite: bool = False
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TemplateExportJob:
    """Template export job."""
    job_id: str
    template_id: str
    version_id: str
    user_id: str
    output_format: TemplateFormat
    data: Dict[str, Any]  # Data to populate template
    status: str  # pending, processing, completed, failed
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


@dataclass
class MarketplaceAnalytics:
    """Marketplace analytics entry."""
    analytics_id: str
    template_id: str
    event_type: str  # view, download, purchase, rating
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class TemplateValidator:
    """Template validation utilities."""
    
    VALID_VARIABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    @classmethod
    def validate_variable_name(cls, name: str) -> bool:
        """Validate variable name format."""
        return bool(cls.VALID_VARIABLE_NAME_PATTERN.match(name))
    
    @classmethod
    def validate_template_content(cls, content: str, variables: List[TemplateVariable]) -> List[Dict[str, Any]]:
        """Validate template content against variable definitions."""
        errors = []
        
        # Find all variable references in content
        # Pattern: {{variable_name}} or {{variable_name|filter}}
        pattern = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\|?[^}]*\}\}'
        referenced_vars = set(re.findall(pattern, content))
        
        defined_vars = {v.name for v in variables}
        
        # Check for undefined variables
        for var in referenced_vars:
            if var not in defined_vars:
                errors.append({
                    "type": "undefined_variable",
                    "variable": var,
                    "message": f"Variable '{var}' is used but not defined"
                })
        
        # Check for unused variables
        for var in defined_vars:
            if var not in referenced_vars:
                errors.append({
                    "type": "unused_variable",
                    "variable": var,
                    "message": f"Variable '{var}' is defined but not used"
                })
        
        return errors
    
    @classmethod
    def validate_variable_value(cls, variable: TemplateVariable, value: Any) -> Optional[str]:
        """Validate a value against variable definition."""
        if value is None:
            if variable.required:
                return f"Required variable '{variable.name}' is missing"
            return None
        
        # Type validation
        type_validators = {
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)),
            "boolean": lambda v: isinstance(v, bool),
            "date": lambda v: isinstance(v, (str, datetime)),
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict)
        }
        
        validator = type_validators.get(variable.variable_type)
        if validator and not validator(value):
            return f"Variable '{variable.name}' should be of type {variable.variable_type}"
        
        # Regex validation
        if variable.validation_regex and isinstance(value, str):
            if not re.match(variable.validation_regex, value):
                return f"Variable '{variable.name}' does not match required pattern"
        
        # Allowed values validation
        if variable.allowed_values and str(value) not in variable.allowed_values:
            return f"Variable '{variable.name}' must be one of: {', '.join(variable.allowed_values)}"
        
        return None


class TemplateMarketplaceManager:
    """
    Central manager for template marketplace operations.
    
    Provides functionality for:
    - Template CRUD operations
    - Version management
    - Marketplace browsing and search
    - User library management
    - Export job processing
    - Analytics tracking
    - Review and rating system
    """
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self.user_libraries: Dict[str, List[UserTemplateLibrary]] = defaultdict(list)
        self.export_jobs: Dict[str, TemplateExportJob] = {}
        self.analytics: List[MarketplaceAnalytics] = []
        self.categories: Dict[TemplateCategory, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Initialize default categories
        self._init_categories()
    
    def _init_categories(self):
        """Initialize default category metadata."""
        for category in TemplateCategory:
            self.categories[category] = {
                "name": category.value.replace("_", " ").title(),
                "description": f"Templates for {category.value}",
                "icon": f"icon-{category.value}",
                "template_count": 0,
                "popular_tags": []
            }
    
    async def initialize(self):
        """Initialize the marketplace manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Load sample templates
            await self._load_sample_templates()
            
            self._initialized = True
            logger.info("TemplateMarketplaceManager initialized successfully")
    
    async def _load_sample_templates(self):
        """Load sample templates for demonstration."""
        sample_templates = [
            {
                "name": "Basic Assessment Report",
                "description": "Standard assessment report template",
                "category": TemplateCategory.ASSESSMENT,
                "formats": [TemplateFormat.PDF, TemplateFormat.HTML],
                "license_type": LicenseType.FREE,
                "tags": ["assessment", "basic", "standard"]
            },
            {
                "name": "Analytics Dashboard",
                "description": "Interactive analytics dashboard template",
                "category": TemplateCategory.ANALYTICS,
                "formats": [TemplateFormat.HTML, TemplateFormat.EXCEL],
                "license_type": LicenseType.FREE,
                "tags": ["analytics", "dashboard", "charts"]
            },
            {
                "name": "Financial Summary Report",
                "description": "Professional financial report template",
                "category": TemplateCategory.FINANCIAL,
                "formats": [TemplateFormat.PDF, TemplateFormat.EXCEL],
                "license_type": LicenseType.PAID,
                "price": 29.99,
                "tags": ["financial", "professional", "summary"]
            }
        ]
        
        for template_data in sample_templates:
            await self.create_template(
                name=template_data["name"],
                description=template_data["description"],
                category=template_data["category"],
                formats=template_data["formats"],
                created_by="system",
                license_type=template_data.get("license_type", LicenseType.FREE),
                price=template_data.get("price", 0.0),
                tags=template_data.get("tags", [])
            )
    
    # Template CRUD Operations
    
    async def create_template(
        self,
        name: str,
        description: str,
        category: TemplateCategory,
        formats: List[TemplateFormat],
        created_by: str,
        license_type: LicenseType = LicenseType.FREE,
        price: float = 0.0,
        tags: Optional[List[str]] = None,
        icon_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        supported_languages: Optional[List[str]] = None,
        is_public: bool = True
    ) -> Template:
        """Create a new template."""
        async with self._lock:
            template_id = f"tpl_{uuid.uuid4().hex[:12]}"
            now = datetime.utcnow()
            
            template = Template(
                template_id=template_id,
                name=name,
                description=description,
                category=category,
                formats=formats,
                status=TemplateStatus.DRAFT,
                created_by=created_by,
                created_at=now,
                updated_at=now,
                license_type=license_type,
                price=price,
                tags=tags or [],
                icon_url=icon_url,
                thumbnail_url=thumbnail_url,
                supported_languages=supported_languages or ["en"],
                is_public=is_public
            )
            
            self.templates[template_id] = template
            self.categories[category]["template_count"] += 1
            
            logger.info(f"Created template: {template_id}")
            return template
    
    async def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any],
        updated_by: str
    ) -> Optional[Template]:
        """Update a template."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)
            
            template.updated_at = datetime.utcnow()
            
            logger.info(f"Updated template: {template_id}")
            return template
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return False
            
            del self.templates[template_id]
            self.categories[template.category]["template_count"] -= 1
            
            logger.info(f"Deleted template: {template_id}")
            return True
    
    async def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
        license_type: Optional[LicenseType] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List templates with filtering and pagination."""
        templates = list(self.templates.values())
        
        # Apply filters
        if category:
            templates = [t for t in templates if t.category == category]
        if status:
            templates = [t for t in templates if t.status == status]
        if license_type:
            templates = [t for t in templates if t.license_type == license_type]
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        if search_query:
            query_lower = search_query.lower()
            templates = [
                t for t in templates
                if query_lower in t.name.lower()
                or query_lower in t.description.lower()
                or any(query_lower in tag.lower() for tag in t.tags)
            ]
        
        # Sort
        reverse = sort_order == "desc"
        if sort_by == "rating":
            templates.sort(key=lambda t: t.average_rating, reverse=reverse)
        elif sort_by == "downloads":
            templates.sort(key=lambda t: t.download_count, reverse=reverse)
        elif sort_by == "name":
            templates.sort(key=lambda t: t.name.lower(), reverse=reverse)
        else:
            templates.sort(key=lambda t: t.created_at, reverse=reverse)
        
        total = len(templates)
        templates = templates[offset:offset + limit]
        
        return {
            "templates": templates,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    
    # Version Management
    
    async def create_version(
        self,
        template_id: str,
        version_number: str,
        content: str,
        changes_description: str,
        created_by: str,
        variables: Optional[List[TemplateVariable]] = None,
        make_current: bool = True
    ) -> Optional[TemplateVersion]:
        """Create a new template version."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            version_id = f"ver_{uuid.uuid4().hex[:12]}"
            
            # Validate content
            validation_errors = TemplateValidator.validate_template_content(content, variables or [])
            if validation_errors:
                logger.warning(f"Template validation errors: {validation_errors}")
            
            version = TemplateVersion(
                version_id=version_id,
                version_number=version_number,
                template_id=template_id,
                created_by=created_by,
                created_at=datetime.utcnow(),
                changes_description=changes_description,
                status=TemplateStatus.PENDING_REVIEW,
                content=content,
                variables=variables or [],
                is_current=make_current
            )
            
            # If making current, unset other current versions
            if make_current:
                for v in template.versions:
                    v.is_current = False
            
            template.versions.append(version)
            template.updated_at = datetime.utcnow()
            
            logger.info(f"Created version {version_number} for template: {template_id}")
            return version
    
    async def get_current_version(self, template_id: str) -> Optional[TemplateVersion]:
        """Get the current version of a template."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        for version in template.versions:
            if version.is_current:
                return version
        
        # Return latest if no current set
        if template.versions:
            return sorted(template.versions, key=lambda v: v.created_at, reverse=True)[0]
        
        return None
    
    async def set_current_version(
        self,
        template_id: str,
        version_id: str
    ) -> bool:
        """Set a specific version as current."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return False
            
            found = False
            for version in template.versions:
                if version.version_id == version_id:
                    version.is_current = True
                    found = True
                else:
                    version.is_current = False
            
            if found:
                template.updated_at = datetime.utcnow()
                logger.info(f"Set version {version_id} as current for template: {template_id}")
            
            return found
    
    # Review and Rating System
    
    async def add_review(
        self,
        template_id: str,
        user_id: str,
        rating: int,
        title: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[TemplateReview]:
        """Add a review to a template."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            if not 1 <= rating <= 5:
                raise ValueError("Rating must be between 1 and 5")
            
            review_id = f"rev_{uuid.uuid4().hex[:12]}"
            
            review = TemplateReview(
                review_id=review_id,
                template_id=template_id,
                user_id=user_id,
                rating=rating,
                title=title,
                comment=comment
            )
            
            template.reviews.append(review)
            template.total_reviews = len(template.reviews)
            template.average_rating = sum(r.rating for r in template.reviews) / template.total_reviews
            template.updated_at = datetime.utcnow()
            
            logger.info(f"Added review {review_id} to template: {template_id}")
            return review
    
    async def get_reviews(
        self,
        template_id: str,
        status: Optional[ReviewStatus] = None,
        limit: int = 50
    ) -> List[TemplateReview]:
        """Get reviews for a template."""
        template = self.templates.get(template_id)
        if not template:
            return []
        
        reviews = template.reviews
        if status:
            reviews = [r for r in reviews if r.status == status]
        
        return sorted(reviews, key=lambda r: r.created_at, reverse=True)[:limit]
    
    # User Library Management
    
    async def add_to_library(
        self,
        user_id: str,
        template_id: str,
        version_id: Optional[str] = None
    ) -> Optional[UserTemplateLibrary]:
        """Add a template to user's library."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            # Get version to use
            if version_id:
                version = next((v for v in template.versions if v.version_id == version_id), None)
            else:
                version = await self.get_current_version(template_id)
            
            if not version:
                return None
            
            library_id = f"lib_{uuid.uuid4().hex[:12]}"
            
            library_entry = UserTemplateLibrary(
                library_id=library_id,
                user_id=user_id,
                template_id=template_id,
                version_id=version.version_id,
                acquired_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365) if template.license_type == LicenseType.SUBSCRIPTION else None
            )
            
            self.user_libraries[user_id].append(library_entry)
            
            logger.info(f"Added template {template_id} to library for user: {user_id}")
            return library_entry
    
    async def get_user_library(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[UserTemplateLibrary]:
        """Get user's template library."""
        library = self.user_libraries.get(user_id, [])
        
        if not include_expired:
            now = datetime.utcnow()
            library = [l for l in library if l.expires_at is None or l.expires_at > now]
        
        return library
    
    async def remove_from_library(
        self,
        user_id: str,
        library_id: str
    ) -> bool:
        """Remove a template from user's library."""
        async with self._lock:
            library = self.user_libraries.get(user_id, [])
            
            for i, entry in enumerate(library):
                if entry.library_id == library_id:
                    library.pop(i)
                    logger.info(f"Removed {library_id} from library for user: {user_id}")
                    return True
            
            return False
    
    # Export Job Processing
    
    async def create_export_job(
        self,
        template_id: str,
        user_id: str,
        output_format: TemplateFormat,
        data: Dict[str, Any],
        version_id: Optional[str] = None
    ) -> Optional[TemplateExportJob]:
        """Create a template export job."""
        async with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            # Validate format is supported
            if output_format not in template.formats:
                raise ValueError(f"Format {output_format.value} not supported by template")
            
            # Get version
            if version_id:
                version = next((v for v in template.versions if v.version_id == version_id), None)
            else:
                version = await self.get_current_version(template_id)
            
            if not version:
                return None
            
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            
            job = TemplateExportJob(
                job_id=job_id,
                template_id=template_id,
                version_id=version.version_id,
                user_id=user_id,
                output_format=output_format,
                data=data,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            self.export_jobs[job_id] = job
            
            logger.info(f"Created export job: {job_id}")
            return job
    
    async def get_export_job(self, job_id: str) -> Optional[TemplateExportJob]:
        """Get an export job by ID."""
        return self.export_jobs.get(job_id)
    
    async def update_export_job_status(
        self,
        job_id: str,
        status: str,
        output_url: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        checksum: Optional[str] = None,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> Optional[TemplateExportJob]:
        """Update export job status."""
        async with self._lock:
            job = self.export_jobs.get(job_id)
            if not job:
                return None
            
            job.status = status
            
            if status == "processing" and not job.started_at:
                job.started_at = datetime.utcnow()
            
            if status in ["completed", "failed"]:
                job.completed_at = datetime.utcnow()
            
            if output_url:
                job.output_url = output_url
            if file_size_bytes:
                job.file_size_bytes = file_size_bytes
            if checksum:
                job.checksum = checksum
            if error_message:
                job.error_message = error_message
            if processing_time_ms:
                job.processing_time_ms = processing_time_ms
            
            logger.info(f"Updated export job {job_id} to status: {status}")
            return job
    
    # Analytics
    
    async def track_event(
        self,
        template_id: str,
        event_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Track a marketplace event."""
        analytics_id = f"anl_{uuid.uuid4().hex[:12]}"
        
        event = MarketplaceAnalytics(
            analytics_id=analytics_id,
            template_id=template_id,
            event_type=event_type,
            user_id=user_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.analytics.append(event)
        
        # Update template counters
        template = self.templates.get(template_id)
        if template:
            if event_type == "view":
                template.view_count += 1
            elif event_type == "download":
                template.download_count += 1
        
        # Keep only last 100,000 analytics entries
        if len(self.analytics) > 100000:
            self.analytics = self.analytics[-100000:]
    
    async def get_analytics(
        self,
        template_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[MarketplaceAnalytics]:
        """Get analytics entries."""
        events = self.analytics
        
        if template_id:
            events = [e for e in events if e.template_id == template_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        total_templates = len(self.templates)
        published_templates = len([t for t in self.templates.values() if t.status == TemplateStatus.PUBLISHED])
        
        total_downloads = sum(t.download_count for t in self.templates.values())
        total_views = sum(t.view_count for t in self.templates.values())
        
        category_distribution = {}
        for category in TemplateCategory:
            count = len([t for t in self.templates.values() if t.category == category])
            category_distribution[category.value] = count
        
        license_distribution = {}
        for license_type in LicenseType:
            count = len([t for t in self.templates.values() if t.license_type == license_type])
            license_distribution[license_type.value] = count
        
        top_templates = sorted(
            self.templates.values(),
            key=lambda t: t.download_count,
            reverse=True
        )[:10]
        
        return {
            "templates": {
                "total": total_templates,
                "published": published_templates,
                "by_category": category_distribution,
                "by_license": license_distribution
            },
            "engagement": {
                "total_downloads": total_downloads,
                "total_views": total_views,
                "average_rating": sum(t.average_rating for t in self.templates.values()) / total_templates if total_templates > 0 else 0,
                "total_reviews": sum(t.total_reviews for t in self.templates.values())
            },
            "jobs": {
                "total": len(self.export_jobs),
                "pending": len([j for j in self.export_jobs.values() if j.status == "pending"]),
                "processing": len([j for j in self.export_jobs.values() if j.status == "processing"]),
                "completed": len([j for j in self.export_jobs.values() if j.status == "completed"]),
                "failed": len([j for j in self.export_jobs.values() if j.status == "failed"])
            },
            "top_templates": [
                {
                    "template_id": t.template_id,
                    "name": t.name,
                    "downloads": t.download_count,
                    "rating": t.average_rating
                }
                for t in top_templates
            ]
        }


# Global manager instance
_marketplace_manager: Optional[TemplateMarketplaceManager] = None


async def get_marketplace_manager() -> TemplateMarketplaceManager:
    """Get or create the global marketplace manager."""
    global _marketplace_manager
    if _marketplace_manager is None:
        _marketplace_manager = TemplateMarketplaceManager()
        await _marketplace_manager.initialize()
    return _marketplace_manager


def reset_marketplace_manager():
    """Reset the global marketplace manager (for testing)."""
    global _marketplace_manager
    _marketplace_manager = None
