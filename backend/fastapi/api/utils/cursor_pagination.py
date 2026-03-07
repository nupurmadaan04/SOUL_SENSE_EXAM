"""
Cursor-based Pagination Utilities

Provides cursor encoding/decoding and validation for stable pagination
under concurrent writes. Cursors are encoded as URL-safe base64 strings
containing the pagination state.

Features:
- Cursor encoding/decoding with signature verification
- Tamper-proof tokens with HMAC validation
- Expiration support for security
- Stable ordering under concurrent writes
- Backward compatibility with offset-based pagination

Example:
    # Encoding a cursor
    cursor = CursorEncoder.encode(
        cursor_data=CursorData(
            id=123,
            timestamp="2026-03-07T12:00:00Z",
            sort_value="example"
        ),
        secret_key=settings.secret_key
    )
    
    # Decoding and validating
    cursor_data = CursorEncoder.decode(
        cursor=cursor,
        secret_key=settings.secret_key,
        max_age=3600  # 1 hour expiration
    )
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union, List, TypeVar, Generic
from enum import Enum

# Type variable for generic pagination
T = TypeVar('T')


class CursorError(Exception):
    """Base exception for cursor-related errors."""
    pass


class InvalidCursorError(CursorError):
    """Raised when cursor is invalid or tampered with."""
    pass


class ExpiredCursorError(CursorError):
    """Raised when cursor has expired."""
    pass


class CursorValidationError(CursorError):
    """Raised when cursor validation fails."""
    pass


@dataclass
class CursorData:
    """
    Data structure for cursor content.
    
    Attributes:
        id: The unique identifier of the last item (primary cursor)
        timestamp: ISO format timestamp for temporal ordering
        sort_value: Value used for sorting (optional, for non-ID sorts)
        filters: Additional filter state (optional)
        created_at: Unix timestamp when cursor was created
    """
    id: Union[int, str]
    timestamp: Optional[str] = None
    sort_value: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    created_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CursorData':
        """Create CursorData from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PaginationResult(Generic[T]):
    """
    Generic pagination result with cursor support.
    
    Attributes:
        items: List of paginated items
        next_cursor: Cursor for next page (None if no more items)
        has_more: Whether more items are available
        total: Total count (optional, may be expensive to compute)
    """
    items: List[T]
    next_cursor: Optional[str]
    has_more: bool
    total: Optional[int] = None


class CursorEncoder:
    """
    Encoder/decoder for pagination cursors with HMAC validation.
    
    Cursors are encoded as URL-safe base64 strings containing:
    - Payload: JSON-encoded cursor data
    - Timestamp: Creation time for expiration
    - Signature: HMAC-SHA256 for tamper detection
    
    Format: base64(payload.timestamp.signature)
    """
    
    ALGORITHM = "sha256"
    VERSION = "v1"
    
    @classmethod
    def encode(
        cls,
        cursor_data: CursorData,
        secret_key: str,
        expires_in: Optional[int] = None
    ) -> str:
        """
        Encode cursor data into a tamper-proof token.
        
        Args:
            cursor_data: The cursor data to encode
            secret_key: Secret key for HMAC signature
            expires_in: Optional expiration time in seconds
            
        Returns:
            URL-safe base64 encoded cursor string
            
        Raises:
            CursorError: If encoding fails
        """
        try:
            # Add creation timestamp
            data = cursor_data.to_dict()
            data['created_at'] = time.time()
            data['version'] = cls.VERSION
            
            if expires_in:
                data['expires_at'] = data['created_at'] + expires_in
            
            # Create payload
            payload = json.dumps(data, separators=(',', ':'))
            payload_bytes = payload.encode('utf-8')
            
            # Create signature
            signature = cls._create_signature(payload_bytes, secret_key)
            
            # Combine: version:payload:signature
            combined = f"{cls.VERSION}:{base64.urlsafe_b64encode(payload_bytes).decode('utf-8')}:{signature}"
            
            # Final base64 encoding
            return base64.urlsafe_b64encode(combined.encode('utf-8')).decode('utf-8').rstrip('=')
            
        except Exception as e:
            raise CursorError(f"Failed to encode cursor: {str(e)}") from e
    
    @classmethod
    def decode(
        cls,
        cursor: str,
        secret_key: str,
        max_age: Optional[int] = None
    ) -> CursorData:
        """
        Decode and validate a cursor token.
        
        Args:
            cursor: The encoded cursor string
            secret_key: Secret key for HMAC verification
            max_age: Maximum age in seconds (optional override)
            
        Returns:
            Decoded CursorData
            
        Raises:
            InvalidCursorError: If cursor is invalid or tampered
            ExpiredCursorError: If cursor has expired
            CursorValidationError: If validation fails
        """
        try:
            # Add padding if needed
            padding = 4 - len(cursor) % 4
            if padding != 4:
                cursor += '=' * padding
            
            # Decode outer base64
            combined = base64.urlsafe_b64decode(cursor.encode('utf-8')).decode('utf-8')
            
            # Split components
            parts = combined.split(':', 2)
            if len(parts) != 3:
                raise InvalidCursorError("Invalid cursor format")
            
            version, payload_b64, signature = parts
            
            # Check version
            if version != cls.VERSION:
                raise InvalidCursorError(f"Unsupported cursor version: {version}")
            
            # Decode payload
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
            
            # Verify signature
            expected_signature = cls._create_signature(payload_bytes, secret_key)
            if not hmac.compare_digest(signature, expected_signature):
                raise InvalidCursorError("Cursor signature mismatch - possible tampering")
            
            # Parse data
            data = json.loads(payload_bytes.decode('utf-8'))
            
            # Check expiration
            expires_at = data.get('expires_at')
            if expires_at and time.time() > expires_at:
                raise ExpiredCursorError("Cursor has expired")
            
            # Check max_age
            if max_age:
                created_at = data.get('created_at', 0)
                if time.time() - created_at > max_age:
                    raise ExpiredCursorError(f"Cursor exceeded max age of {max_age} seconds")
            
            # Remove internal fields
            data.pop('version', None)
            data.pop('expires_at', None)
            data.pop('created_at', None)
            
            return CursorData.from_dict(data)
            
        except (InvalidCursorError, ExpiredCursorError):
            raise
        except Exception as e:
            raise InvalidCursorError(f"Failed to decode cursor: {str(e)}") from e
    
    @classmethod
    def _create_signature(cls, payload: bytes, secret_key: str) -> str:
        """Create HMAC-SHA256 signature for payload."""
        return hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()[:32]  # Use first 32 chars for shorter cursors


class CursorPaginator:
    """
    Generic cursor-based paginator for database queries.
    
    Provides stable pagination that handles concurrent writes correctly.
    Uses cursor-based navigation instead of offset for consistency.
    
    Example:
        paginator = CursorPaginator(
            secret_key=settings.secret_key,
            default_page_size=20
        )
        
        result = await paginator.paginate(
            query=select(Model).order_by(Model.id),
            cursor=cursor,
            page_size=20,
            db_session=db
        )
    """
    
    def __init__(
        self,
        secret_key: str,
        default_page_size: int = 20,
        max_page_size: int = 100,
        cursor_expires_in: int = 3600
    ):
        """
        Initialize paginator.
        
        Args:
            secret_key: Secret key for cursor signing
            default_page_size: Default items per page
            max_page_size: Maximum allowed items per page
            cursor_expires_in: Default cursor expiration in seconds
        """
        self.secret_key = secret_key
        self.default_page_size = default_page_size
        self.max_page_size = max(max_page_size, default_page_size)
        self.cursor_expires_in = cursor_expires_in
    
    def validate_page_size(self, page_size: Optional[int]) -> int:
        """Validate and normalize page size."""
        if page_size is None:
            return self.default_page_size
        if page_size < 1:
            return self.default_page_size
        return min(page_size, self.max_page_size)
    
    def decode_cursor(self, cursor: Optional[str]) -> Optional[CursorData]:
        """
        Decode cursor if provided.
        
        Args:
            cursor: Encoded cursor string or None
            
        Returns:
            CursorData or None
            
        Raises:
            InvalidCursorError: If cursor is invalid
        """
        if not cursor:
            return None
        return CursorEncoder.decode(cursor, self.secret_key)
    
    def encode_cursor(self, cursor_data: CursorData) -> str:
        """Encode cursor data with default expiration."""
        return CursorEncoder.encode(
            cursor_data=cursor_data,
            secret_key=self.secret_key,
            expires_in=self.cursor_expires_in
        )
    
    async def paginate(
        self,
        items: List[Any],
        get_cursor_data: callable,
        cursor: Optional[str] = None,
        page_size: Optional[int] = None
    ) -> PaginationResult:
        """
        Apply cursor pagination to a list of items.
        
        Args:
            items: List of items to paginate
            get_cursor_data: Function to extract CursorData from an item
            cursor: Optional cursor for next page
            page_size: Items per page
            
        Returns:
            PaginationResult with items and next cursor
        """
        page_size = self.validate_page_size(page_size)
        
        # Decode cursor if provided
        cursor_data = self.decode_cursor(cursor) if cursor else None
        
        # Filter items based on cursor
        if cursor_data:
            # Find position after cursor
            start_idx = 0
            for idx, item in enumerate(items):
                item_cursor = get_cursor_data(item)
                if item_cursor.id == cursor_data.id:
                    start_idx = idx + 1
                    break
            items = items[start_idx:]
        
        # Get current page
        page_items = items[:page_size]
        has_more = len(items) > page_size
        
        # Generate next cursor
        next_cursor = None
        if has_more and page_items:
            last_item = page_items[-1]
            next_cursor_data = get_cursor_data(last_item)
            next_cursor_data.created_at = time.time()
            next_cursor = self.encode_cursor(next_cursor_data)
        
        return PaginationResult(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more
        )


def create_cursor_from_item(
    item: Any,
    id_field: str = "id",
    timestamp_field: Optional[str] = "created_at",
    sort_field: Optional[str] = None
) -> CursorData:
    """
    Helper to create cursor data from an item.
    
    Args:
        item: The item to create cursor from (dict or object)
        id_field: Field name for ID
        timestamp_field: Field name for timestamp
        sort_field: Optional field for sort value
        
    Returns:
        CursorData
    """
    # Handle both dict and object
    if isinstance(item, dict):
        item_id = item.get(id_field)
        timestamp = item.get(timestamp_field) if timestamp_field else None
        sort_value = item.get(sort_field) if sort_field else None
    else:
        item_id = getattr(item, id_field, None)
        timestamp = getattr(item, timestamp_field, None) if timestamp_field else None
        sort_value = getattr(item, sort_field, None) if sort_field else None
    
    # Format timestamp if datetime
    if timestamp and isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()
    
    return CursorData(
        id=item_id,
        timestamp=timestamp,
        sort_value=str(sort_value) if sort_value is not None else None
    )


# Backward compatibility: Offset to Cursor adapter
class OffsetCursorAdapter:
    """
    Adapter for backward compatibility with offset-based pagination.
    
    Allows gradual migration from offset to cursor-based pagination.
    """
    
    @staticmethod
    def offset_to_cursor(offset: int) -> str:
        """Convert offset to cursor format."""
        data = CursorData(
            id=offset,
            sort_value="offset"
        )
        # Use empty secret for backward compatibility
        return CursorEncoder.encode(data, secret_key="offset_compat")
    
    @staticmethod
    def cursor_to_offset(cursor: Optional[str]) -> int:
        """Convert cursor back to offset."""
        if not cursor:
            return 0
        try:
            data = CursorEncoder.decode(cursor, secret_key="offset_compat")
            if data.sort_value == "offset":
                return int(data.id)
        except:
            pass
        return 0
