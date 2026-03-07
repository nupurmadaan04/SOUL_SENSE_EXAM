"""
Pagination Schemas

Provides unified pagination schemas supporting both offset and cursor-based pagination.
Cursor-based pagination is preferred for stability under concurrent writes.

Usage:
    # Cursor-based response
    return CursorPaginatedResponse[ItemType](
        items=items,
        next_cursor="eyJpZCI6IDEyM30",
        has_more=True,
        total=1000
    )
    
    # Offset-based response (legacy)
    return OffsetPaginatedResponse[ItemType](
        items=items,
        page=1,
        page_size=20,
        total=1000
    )
"""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    Common pagination parameters.
    
    Supports both cursor and offset-based pagination.
    Cursor takes precedence if provided.
    """
    cursor: Optional[str] = Field(
        None,
        description="Cursor token for cursor-based pagination (preferred)"
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number for offset-based pagination (legacy)"
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    
    model_config = ConfigDict(extra="forbid")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """
    Cursor-based paginated response.
    
    Provides stable pagination under concurrent writes.
    Use this for new endpoints.
    
    Attributes:
        items: List of items for current page
        next_cursor: Cursor to fetch next page (null if no more items)
        has_more: Whether more items are available
        total: Total count (optional, may be null if expensive to compute)
    """
    items: List[T] = Field(
        ...,
        description="List of items for the current page"
    )
    next_cursor: Optional[str] = Field(
        None,
        description="Cursor token to fetch the next page"
    )
    has_more: bool = Field(
        ...,
        description="Whether more items are available"
    )
    total: Optional[int] = Field(
        None,
        description="Total number of items (may be null if expensive to compute)"
    )
    
    model_config = ConfigDict(from_attributes=True)


class OffsetPaginatedResponse(BaseModel, Generic[T]):
    """
    Offset-based paginated response.
    
    Legacy pagination format. May show duplicates/skipped items
    under concurrent writes. Prefer CursorPaginatedResponse for new code.
    
    Attributes:
        items: List of items for current page
        page: Current page number (1-indexed)
        page_size: Items per page
        total: Total number of items
    """
    items: List[T] = Field(
        ...,
        description="List of items for the current page"
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number"
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of items per page"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items"
    )
    
    model_config = ConfigDict(from_attributes=True)


class HybridPaginatedResponse(BaseModel, Generic[T]):
    """
    Hybrid paginated response supporting both cursor and offset.
    
    Use during migration from offset to cursor-based pagination.
    Provides both formats for backward compatibility.
    
    Attributes:
        items: List of items for current page
        next_cursor: Cursor for next page (preferred navigation method)
        has_more: Whether more items are available
        page: Current page number (legacy)
        page_size: Items per page
        total: Total number of items
    """
    items: List[T] = Field(
        ...,
        description="List of items for the current page"
    )
    next_cursor: Optional[str] = Field(
        None,
        description="Cursor token to fetch the next page (preferred)"
    )
    has_more: bool = Field(
        ...,
        description="Whether more items are available"
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (legacy, for backward compatibility)"
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of items per page"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items"
    )
    
    model_config = ConfigDict(from_attributes=True)


class CursorValidationError(BaseModel):
    """Error response for invalid cursor."""
    error: str = "invalid_cursor"
    message: str
    details: Optional[str] = None


class PaginationMetadata(BaseModel):
    """
    Metadata for paginated responses.
    
    Can be included in response headers or body for debugging.
    """
    request_id: Optional[str] = None
    cursor_version: str = "v1"
    cursor_expires_at: Optional[str] = None
    generated_at: str = Field(
        ...,
        description="ISO 8601 timestamp when pagination was computed"
    )
    
    model_config = ConfigDict(from_attributes=True)


# Generic type aliases for convenience
PaginatedItems = CursorPaginatedResponse
LegacyPaginatedItems = OffsetPaginatedResponse


# Request/Response examples for documentation
class PaginationExamples:
    """Example values for API documentation."""
    
    CURSOR_REQUEST = {
        "cursor": "eyJpZCI6IDEyMywgInRpbWVzdGFtcCI6ICIyMDI2LTAzLTA3VDEyOjAwOjAwWiJ9",
        "page_size": 20
    }
    
    OFFSET_REQUEST = {
        "page": 1,
        "page_size": 20
    }
    
    CURSOR_RESPONSE = {
        "items": [],
        "next_cursor": "eyJpZCI6IDEyMywgInRpbWVzdGFtcCI6ICIyMDI2LTAzLTA3VDEyOjAwOjAwWiJ9",
        "has_more": True,
        "total": 1000
    }
    
    OFFSET_RESPONSE = {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 1000
    }
