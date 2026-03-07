"""
Template Marketplace API Router

Provides REST API endpoints for template marketplace operations including:
- Template browsing and search
- Template management (CRUD)
- Version management
- User library management
- Export job processing
- Reviews and ratings
- Analytics
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field

from backend.fastapi.api.utils.template_marketplace import (
    TemplateMarketplaceManager,
    get_marketplace_manager,
    TemplateFormat,
    TemplateCategory,
    TemplateStatus,
    LicenseType,
    ReviewStatus,
    Template,
    TemplateVersion,
    TemplateReview,
    UserTemplateLibrary,
    TemplateExportJob,
    TemplateVariable,
    TemplateStyle
)

router = APIRouter(prefix="/template-marketplace", tags=["template-marketplace"])


# Pydantic Models

class TemplateCreate(BaseModel):
    name: str
    description: str
    category: TemplateCategory
    formats: List[TemplateFormat]
    license_type: LicenseType = LicenseType.FREE
    price: float = 0.0
    tags: List[str] = Field(default_factory=list)
    icon_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    supported_languages: List[str] = Field(default_factory=lambda: ["en"])
    is_public: bool = True


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: str
    category: str
    formats: List[str]
    status: str
    license_type: str
    price: float
    currency: str
    tags: List[str]
    average_rating: float
    total_reviews: int
    download_count: int
    view_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_featured: bool
    is_public: bool


class VersionCreate(BaseModel):
    version_number: str
    content: str
    changes_description: str
    variables: List[Dict[str, Any]] = Field(default_factory=list)
    make_current: bool = True


class VersionResponse(BaseModel):
    version_id: str
    version_number: str
    template_id: str
    created_by: str
    created_at: datetime
    status: str
    is_current: bool
    download_count: int


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    review_id: str
    template_id: str
    user_id: str
    rating: int
    title: Optional[str]
    comment: Optional[str]
    created_at: datetime
    helpful_count: int


class ExportJobCreate(BaseModel):
    template_id: str
    output_format: TemplateFormat
    data: Dict[str, Any]
    version_id: Optional[str] = None


class ExportJobResponse(BaseModel):
    job_id: str
    template_id: str
    output_format: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    output_url: Optional[str]
    file_size_bytes: Optional[int]


class LibraryEntryResponse(BaseModel):
    library_id: str
    template_id: str
    version_id: str
    acquired_at: datetime
    expires_at: Optional[datetime]
    usage_count: int
    is_favorite: bool


# Template Endpoints

@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    user_id: str,  # In production, get from auth token
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Create a new template."""
    template = await manager.create_template(
        name=data.name,
        description=data.description,
        category=data.category,
        formats=data.formats,
        created_by=user_id,
        license_type=data.license_type,
        price=data.price,
        tags=data.tags,
        icon_url=data.icon_url,
        thumbnail_url=data.thumbnail_url,
        supported_languages=data.supported_languages,
        is_public=data.is_public
    )
    return _template_to_response(template)


@router.get("/templates", response_model=Dict[str, Any])
async def list_templates(
    category: Optional[TemplateCategory] = None,
    status: Optional[TemplateStatus] = TemplateStatus.PUBLISHED,
    license_type: Optional[LicenseType] = None,
    tags: Optional[List[str]] = Query(None),
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """List templates with filtering and pagination."""
    result = await manager.list_templates(
        category=category,
        status=status,
        license_type=license_type,
        tags=tags,
        search_query=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    
    return {
        "templates": [_template_to_response(t) for t in result["templates"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
        "has_more": result["has_more"]
    }


@router.get("/templates/featured", response_model=List[TemplateResponse])
async def get_featured_templates(
    limit: int = Query(10, ge=1, le=50),
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get featured templates."""
    result = await manager.list_templates(
        status=TemplateStatus.PUBLISHED,
        limit=limit
    )
    
    # Filter featured or sort by popularity
    templates = sorted(
        result["templates"],
        key=lambda t: (t.is_featured, t.download_count, t.average_rating),
        reverse=True
    )[:limit]
    
    return [_template_to_response(t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    background_tasks: BackgroundTasks,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get a template by ID."""
    template = await manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Track view in background
    background_tasks.add_task(manager.track_event, template_id, "view")
    
    return _template_to_response(template)


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    updates: Dict[str, Any],
    user_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Update a template."""
    template = await manager.update_template(template_id, updates, user_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Delete a template."""
    success = await manager.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return None


@router.post("/templates/{template_id}/publish")
async def publish_template(
    template_id: str,
    user_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Publish a template."""
    template = await manager.update_template(
        template_id,
        {"status": TemplateStatus.PUBLISHED},
        user_id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_to_response(template)


# Version Endpoints

@router.post("/templates/{template_id}/versions", response_model=VersionResponse)
async def create_version(
    template_id: str,
    data: VersionCreate,
    user_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Create a new template version."""
    # Convert dict variables to TemplateVariable objects
    variables = [TemplateVariable(**v) for v in data.variables]
    
    version = await manager.create_version(
        template_id=template_id,
        version_number=data.version_number,
        content=data.content,
        changes_description=data.changes_description,
        created_by=user_id,
        variables=variables,
        make_current=data.make_current
    )
    
    if not version:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return _version_to_response(version)


@router.get("/templates/{template_id}/versions", response_model=List[VersionResponse])
async def list_versions(
    template_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """List all versions of a template."""
    template = await manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return [_version_to_response(v) for v in template.versions]


@router.get("/templates/{template_id}/versions/current", response_model=VersionResponse)
async def get_current_version(
    template_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get the current version of a template."""
    version = await manager.get_current_version(template_id)
    if not version:
        raise HTTPException(status_code=404, detail="No version found for template")
    return _version_to_response(version)


@router.post("/templates/{template_id}/versions/{version_id}/set-current")
async def set_current_version(
    template_id: str,
    version_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Set a specific version as current."""
    success = await manager.set_current_version(template_id, version_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template or version not found")
    return {"message": "Version set as current"}


# Review Endpoints

@router.post("/templates/{template_id}/reviews", response_model=ReviewResponse)
async def add_review(
    template_id: str,
    data: ReviewCreate,
    user_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Add a review to a template."""
    review = await manager.add_review(
        template_id=template_id,
        user_id=user_id,
        rating=data.rating,
        title=data.title,
        comment=data.comment
    )
    
    if not review:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return _review_to_response(review)


@router.get("/templates/{template_id}/reviews", response_model=List[ReviewResponse])
async def get_reviews(
    template_id: str,
    status: Optional[ReviewStatus] = ReviewStatus.APPROVED,
    limit: int = Query(50, ge=1, le=100),
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get reviews for a template."""
    reviews = await manager.get_reviews(template_id, status=status, limit=limit)
    return [_review_to_response(r) for r in reviews]


# User Library Endpoints

@router.post("/library", response_model=LibraryEntryResponse)
async def add_to_library(
    template_id: str,
    user_id: str,
    version_id: Optional[str] = None,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Add a template to user's library."""
    entry = await manager.add_to_library(user_id, template_id, version_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Template not found")
    return _library_to_response(entry)


@router.get("/library", response_model=List[LibraryEntryResponse])
async def get_user_library(
    user_id: str,
    include_expired: bool = False,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get user's template library."""
    library = await manager.get_user_library(user_id, include_expired=include_expired)
    return [_library_to_response(e) for e in library]


@router.delete("/library/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_library(
    library_id: str,
    user_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Remove a template from user's library."""
    success = await manager.remove_from_library(user_id, library_id)
    if not success:
        raise HTTPException(status_code=404, detail="Library entry not found")
    return None


# Export Job Endpoints

@router.post("/exports", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def create_export_job(
    data: ExportJobCreate,
    user_id: str,
    background_tasks: BackgroundTasks,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Create a template export job."""
    job = await manager.create_export_job(
        template_id=data.template_id,
        user_id=user_id,
        output_format=data.output_format,
        data=data.data,
        version_id=data.version_id
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Track download
    background_tasks.add_task(manager.track_event, data.template_id, "download", user_id)
    
    return _export_job_to_response(job)


@router.get("/exports/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    job_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get an export job by ID."""
    job = await manager.get_export_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return _export_job_to_response(job)


@router.get("/users/{user_id}/exports", response_model=List[ExportJobResponse])
async def get_user_export_jobs(
    user_id: str,
    status: Optional[str] = None,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get export jobs for a user."""
    jobs = [j for j in manager.export_jobs.values() if j.user_id == user_id]
    if status:
        jobs = [j for j in jobs if j.status == status]
    return [_export_job_to_response(j) for j in jobs]


# Category Endpoints

@router.get("/categories")
async def list_categories(
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """List all template categories."""
    return {
        "categories": [
            {
                "id": cat.value,
                "name": meta["name"],
                "description": meta["description"],
                "template_count": meta["template_count"]
            }
            for cat, meta in manager.categories.items()
        ]
    }


@router.get("/formats")
async def list_formats():
    """List all supported export formats."""
    return {
        "formats": [
            {
                "id": fmt.value,
                "name": fmt.value.upper(),
                "mime_type": _get_mime_type(fmt)
            }
            for fmt in TemplateFormat
        ]
    }


# Statistics Endpoints

@router.get("/statistics")
async def get_marketplace_statistics(
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get marketplace statistics."""
    stats = await manager.get_statistics()
    return stats


@router.get("/templates/{template_id}/statistics")
async def get_template_statistics(
    template_id: str,
    manager: TemplateMarketplaceManager = Depends(get_marketplace_manager)
):
    """Get statistics for a specific template."""
    template = await manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "template_id": template_id,
        "views": template.view_count,
        "downloads": template.download_count,
        "average_rating": template.average_rating,
        "total_reviews": template.total_reviews,
        "versions": len(template.versions)
    }


# Helper Functions

def _template_to_response(template: Template) -> Dict[str, Any]:
    """Convert Template to response dict."""
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "category": template.category.value,
        "formats": [f.value for f in template.formats],
        "status": template.status.value,
        "license_type": template.license_type.value,
        "price": template.price,
        "currency": template.currency,
        "tags": template.tags,
        "average_rating": template.average_rating,
        "total_reviews": template.total_reviews,
        "download_count": template.download_count,
        "view_count": template.view_count,
        "created_by": template.created_by,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "is_featured": template.is_featured,
        "is_public": template.is_public
    }


def _version_to_response(version: TemplateVersion) -> Dict[str, Any]:
    """Convert TemplateVersion to response dict."""
    return {
        "version_id": version.version_id,
        "version_number": version.version_number,
        "template_id": version.template_id,
        "created_by": version.created_by,
        "created_at": version.created_at,
        "status": version.status.value,
        "is_current": version.is_current,
        "download_count": version.download_count
    }


def _review_to_response(review: TemplateReview) -> Dict[str, Any]:
    """Convert TemplateReview to response dict."""
    return {
        "review_id": review.review_id,
        "template_id": review.template_id,
        "user_id": review.user_id,
        "rating": review.rating,
        "title": review.title,
        "comment": review.comment,
        "created_at": review.created_at,
        "helpful_count": review.helpful_count
    }


def _library_to_response(entry: UserTemplateLibrary) -> Dict[str, Any]:
    """Convert UserTemplateLibrary to response dict."""
    return {
        "library_id": entry.library_id,
        "template_id": entry.template_id,
        "version_id": entry.version_id,
        "acquired_at": entry.acquired_at,
        "expires_at": entry.expires_at,
        "usage_count": entry.usage_count,
        "is_favorite": entry.is_favorite
    }


def _export_job_to_response(job: TemplateExportJob) -> Dict[str, Any]:
    """Convert TemplateExportJob to response dict."""
    return {
        "job_id": job.job_id,
        "template_id": job.template_id,
        "output_format": job.output_format.value,
        "status": job.status,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "output_url": job.output_url,
        "file_size_bytes": job.file_size_bytes
    }


def _get_mime_type(fmt: TemplateFormat) -> str:
    """Get MIME type for format."""
    mime_types = {
        TemplateFormat.PDF: "application/pdf",
        TemplateFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        TemplateFormat.CSV: "text/csv",
        TemplateFormat.HTML: "text/html",
        TemplateFormat.JSON: "application/json",
        TemplateFormat.XML: "application/xml",
        TemplateFormat.MARKDOWN: "text/markdown",
        TemplateFormat.WORD: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        TemplateFormat.POWERPOINT: "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    }
    return mime_types.get(fmt, "application/octet-stream")
