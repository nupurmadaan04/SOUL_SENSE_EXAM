"""
Cursor Pagination Service

Provides service-level support for cursor-based pagination with automatic
cursor encoding/decoding and validation.

This service wraps the cursor pagination utilities for easy integration
with existing service classes.
"""

from typing import List, Optional, TypeVar, Generic, Callable, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from datetime import datetime, timezone
import time

from ..utils.cursor_pagination import (
    CursorEncoder,
    CursorData,
    CursorPaginator,
    PaginationResult,
    create_cursor_from_item,
    InvalidCursorError,
    ExpiredCursorError
)
from ..config import get_settings

T = TypeVar('T')


class CursorPaginationService:
    """
    Service for handling cursor-based pagination in database queries.
    
    Provides stable pagination that handles concurrent writes correctly.
    
    Example:
        pagination_service = CursorPaginationService()
        
        result = await pagination_service.paginate_query(
            query=select(Journal).where(Journal.user_id == user_id).order_by(Journal.id.desc()),
            cursor=cursor,
            page_size=20,
            db_session=db
        )
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize pagination service.
        
        Args:
            secret_key: Secret key for cursor signing (auto-loaded from settings if None)
        """
        if secret_key is None:
            settings = get_settings()
            # Use JWT secret as fallback for cursor signing
            secret_key = getattr(settings, 'jwt_secret_key', 'default_cursor_secret')
        
        self.secret_key = secret_key
        self.paginator = CursorPaginator(
            secret_key=secret_key,
            default_page_size=20,
            max_page_size=100,
            cursor_expires_in=3600  # 1 hour
        )
    
    async def paginate_query(
        self,
        query,
        db_session: AsyncSession,
        cursor: Optional[str] = None,
        page_size: Optional[int] = None,
        cursor_fields: Optional[Dict[str, str]] = None
    ) -> PaginationResult:
        """
        Execute a query with cursor-based pagination.
        
        Args:
            query: SQLAlchemy select query (should be ordered)
            db_session: Database session
            cursor: Encoded cursor string or None
            page_size: Items per page
            cursor_fields: Mapping of cursor fields {'id': 'id_field', 'timestamp': 'ts_field'}
            
        Returns:
            PaginationResult with items and next cursor
        """
        page_size = self.paginator.validate_page_size(page_size)
        cursor_data = self.paginator.decode_cursor(cursor) if cursor else None
        
        # Apply cursor filter if provided
        if cursor_data:
            query = self._apply_cursor_filter(query, cursor_data, cursor_fields)
        
        # Limit to page_size + 1 to detect has_more
        query = query.limit(page_size + 1)
        
        # Execute query
        result = await db_session.execute(query)
        items = result.scalars().all()
        
        # Check if there are more items
        has_more = len(items) > page_size
        items = list(items[:page_size])
        
        # Generate next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor_data = self._create_cursor_data(last_item, cursor_fields)
            next_cursor = self.paginator.encode_cursor(next_cursor_data)
        
        return PaginationResult(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more
        )
    
    def _apply_cursor_filter(
        self,
        query,
        cursor_data: CursorData,
        cursor_fields: Optional[Dict[str, str]] = None
    ):
        """
        Apply cursor filter to query.
        
        Uses WHERE clause to get items after the cursor position.
        """
        id_field = cursor_fields.get('id', 'id') if cursor_fields else 'id'
        
        # Get the model from query
        # For simple cases, filter by ID > cursor_id
        # For more complex sorting, additional logic would be needed
        if hasattr(query, 'where'):
            cursor_id = cursor_data.id
            # This assumes the model has an 'id' column
            # In production, this would need to be more sophisticated
            # to handle different sort orders
            model_class = self._get_model_from_query(query)
            if model_class:
                id_column = getattr(model_class, id_field, None)
                if id_column:
                    query = query.where(id_column > cursor_id)
        
        return query
    
    def _get_model_from_query(self, query) -> Optional[Any]:
        """Extract model class from SQLAlchemy query."""
        try:
            # Try to get the primary entity from the query
            if hasattr(query, '_entity_from_pre_ent_zero'):
                return query._entity_from_pre_ent_zero()
            elif hasattr(query, '_entities') and query._entities:
                return query._entities[0].entity_zero_or_one()
        except:
            pass
        return None
    
    def _create_cursor_data(
        self,
        item: Any,
        cursor_fields: Optional[Dict[str, str]] = None
    ) -> CursorData:
        """Create cursor data from an item."""
        if cursor_fields is None:
            cursor_fields = {}
        
        id_field = cursor_fields.get('id', 'id')
        timestamp_field = cursor_fields.get('timestamp', 'created_at')
        sort_field = cursor_fields.get('sort_value')
        
        # Handle both dict and ORM model
        if isinstance(item, dict):
            item_id = item.get(id_field)
            timestamp = item.get(timestamp_field)
            sort_value = item.get(sort_field) if sort_field else None
        else:
            item_id = getattr(item, id_field, None)
            timestamp = getattr(item, timestamp_field, None)
            sort_value = getattr(item, sort_field, None) if sort_field else None
        
        # Format timestamp
        if timestamp and isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        return CursorData(
            id=item_id,
            timestamp=timestamp,
            sort_value=str(sort_value) if sort_value is not None else None,
            created_at=time.time()
        )
    
    def validate_cursor(self, cursor: Optional[str]) -> Optional[CursorData]:
        """
        Validate and decode a cursor.
        
        Args:
            cursor: Encoded cursor string
            
        Returns:
            CursorData if valid, None if cursor is None
            
        Raises:
            InvalidCursorError: If cursor is invalid
            ExpiredCursorError: If cursor has expired
        """
        return self.paginator.decode_cursor(cursor)
    
    def create_cursor(
        self,
        item_id: Any,
        timestamp: Optional[str] = None,
        sort_value: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new cursor.
        
        Args:
            item_id: The ID of the item
            timestamp: ISO format timestamp
            sort_value: Optional sort value
            filters: Optional filter state
            
        Returns:
            Encoded cursor string
        """
        cursor_data = CursorData(
            id=item_id,
            timestamp=timestamp,
            sort_value=sort_value,
            filters=filters,
            created_at=time.time()
        )
        return self.paginator.encode_cursor(cursor_data)


# Convenience function for quick pagination
async def paginate_with_cursor(
    query,
    db_session: AsyncSession,
    cursor: Optional[str] = None,
    page_size: Optional[int] = 20,
    secret_key: Optional[str] = None
) -> PaginationResult:
    """
    Quick pagination function for simple use cases.
    
    Example:
        result = await paginate_with_cursor(
            query=select(Model).order_by(Model.id),
            db_session=db,
            cursor=request.cursor,
            page_size=20
        )
    """
    service = CursorPaginationService(secret_key=secret_key)
    return await service.paginate_query(
        query=query,
        db_session=db_session,
        cursor=cursor,
        page_size=page_size
    )
