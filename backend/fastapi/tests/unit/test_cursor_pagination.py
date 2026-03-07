"""
Unit tests for Cursor-based Pagination (#1365).

Tests cursor encoding/decoding, validation, and pagination stability
under concurrent writes.
"""
import pytest
import time
import base64
import json
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import asdict

from api.utils.cursor_pagination import (
    CursorEncoder,
    CursorData,
    CursorPaginator,
    PaginationResult,
    create_cursor_from_item,
    OffsetCursorAdapter,
    CursorError,
    InvalidCursorError,
    ExpiredCursorError,
    CursorValidationError
)


class TestCursorEncoder:
    """Test cursor encoding and decoding."""

    def test_encode_decode_basic(self):
        """Test basic cursor encoding and decoding."""
        secret_key = "test_secret_key"
        cursor_data = CursorData(
            id=123,
            timestamp="2026-03-07T12:00:00Z",
            sort_value="test_value"
        )
        
        # Encode
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        assert cursor is not None
        assert isinstance(cursor, str)
        
        # Decode
        decoded = CursorEncoder.decode(cursor, secret_key)
        assert decoded.id == 123
        assert decoded.timestamp == "2026-03-07T12:00:00Z"
        assert decoded.sort_value == "test_value"

    def test_encode_with_expiration(self):
        """Test cursor encoding with expiration."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=456)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key, expires_in=3600)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.id == 456

    def test_decode_expired_cursor(self):
        """Test decoding an expired cursor raises error."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=789)
        
        # Create cursor with very short expiration
        cursor = CursorEncoder.encode(cursor_data, secret_key, expires_in=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        with pytest.raises(ExpiredCursorError):
            CursorEncoder.decode(cursor, secret_key)

    def test_decode_with_max_age(self):
        """Test decoding with max_age parameter."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=999)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Should succeed with generous max_age
        decoded = CursorEncoder.decode(cursor, secret_key, max_age=3600)
        assert decoded.id == 999
        
        # Should fail with very short max_age after waiting
        time.sleep(0.1)
        with pytest.raises(ExpiredCursorError):
            CursorEncoder.decode(cursor, secret_key, max_age=0.05)

    def test_tampered_cursor_detection(self):
        """Test detection of tampered cursor."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=111)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Tamper with cursor - modify a character
        tampered = cursor[:-5] + ("X" if cursor[-5] != "X" else "Y") + cursor[-4:]
        
        with pytest.raises(InvalidCursorError, match="signature mismatch"):
            CursorEncoder.decode(tampered, secret_key)

    def test_invalid_cursor_format(self):
        """Test decoding invalid cursor format."""
        secret_key = "test_secret"
        
        with pytest.raises(InvalidCursorError):
            CursorEncoder.decode("invalid_cursor", secret_key)
        
        with pytest.raises(InvalidCursorError):
            CursorEncoder.decode("aW52YWxpZA", secret_key)  # base64 of "invalid"

    def test_different_secret_keys(self):
        """Test that different secret keys produce different cursors."""
        cursor_data = CursorData(id=222)
        
        cursor1 = CursorEncoder.encode(cursor_data, "secret1")
        cursor2 = CursorEncoder.encode(cursor_data, "secret2")
        
        assert cursor1 != cursor2
        
        # Each can be decoded with its own secret
        assert CursorEncoder.decode(cursor1, "secret1").id == 222
        assert CursorEncoder.decode(cursor2, "secret2").id == 222
        
        # Cannot decode with wrong secret
        with pytest.raises(InvalidCursorError):
            CursorEncoder.decode(cursor1, "secret2")

    def test_cursor_with_filters(self):
        """Test cursor encoding with filter data."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id=333,
            filters={"user_id": 1, "status": "active", "tags": ["a", "b"]}
        )
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.id == 333
        assert decoded.filters == {"user_id": 1, "status": "active", "tags": ["a", "b"]}

    def test_cursor_data_string_id(self):
        """Test cursor with string ID."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id="user_123",
            timestamp="2026-03-07T12:00:00Z"
        )
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.id == "user_123"


class TestCursorPaginator:
    """Test cursor paginator functionality."""

    @pytest.fixture
    def paginator(self):
        """Create a paginator instance."""
        return CursorPaginator(
            secret_key="test_secret",
            default_page_size=20,
            max_page_size=100,
            cursor_expires_in=3600
        )

    def test_validate_page_size(self, paginator):
        """Test page size validation."""
        assert paginator.validate_page_size(None) == 20  # default
        assert paginator.validate_page_size(10) == 10
        assert paginator.validate_page_size(50) == 50
        assert paginator.validate_page_size(150) == 100  # max
        assert paginator.validate_page_size(0) == 20  # min
        assert paginator.validate_page_size(-5) == 20  # negative

    def test_decode_cursor_valid(self, paginator):
        """Test decoding valid cursor."""
        cursor_data = CursorData(id=100)
        cursor = paginator.encode_cursor(cursor_data)
        
        decoded = paginator.decode_cursor(cursor)
        assert decoded.id == 100

    def test_decode_cursor_none(self, paginator):
        """Test decoding None cursor returns None."""
        assert paginator.decode_cursor(None) is None

    def test_decode_cursor_invalid(self, paginator):
        """Test decoding invalid cursor raises error."""
        with pytest.raises(InvalidCursorError):
            paginator.decode_cursor("invalid")

    @pytest.mark.asyncio
    async def test_paginate_without_cursor(self, paginator):
        """Test pagination without cursor."""
        items = [{"id": i, "name": f"item_{i}"} for i in range(1, 26)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        result = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=10
        )
        
        assert len(result.items) == 10
        assert result.items[0]["id"] == 1
        assert result.items[-1]["id"] == 10
        assert result.has_more is True
        assert result.next_cursor is not None

    @pytest.mark.asyncio
    async def test_paginate_with_cursor(self, paginator):
        """Test pagination with cursor."""
        items = [{"id": i, "name": f"item_{i}"} for i in range(1, 26)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        # First page
        result1 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=10
        )
        
        # Second page using cursor
        result2 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            cursor=result1.next_cursor,
            page_size=10
        )
        
        assert len(result2.items) == 10
        assert result2.items[0]["id"] == 11
        assert result2.items[-1]["id"] == 20

    @pytest.mark.asyncio
    async def test_paginate_last_page(self, paginator):
        """Test pagination on last page."""
        items = [{"id": i} for i in range(1, 16)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        result = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=20  # More than items
        )
        
        assert len(result.items) == 15
        assert result.has_more is False
        assert result.next_cursor is None

    @pytest.mark.asyncio
    async def test_paginate_empty_list(self, paginator):
        """Test pagination with empty list."""
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        result = await paginator.paginate(
            items=[],
            get_cursor_data=get_cursor_data,
            page_size=10
        )
        
        assert len(result.items) == 0
        assert result.has_more is False
        assert result.next_cursor is None


class TestCreateCursorFromItem:
    """Test cursor creation from items."""

    def test_from_dict(self):
        """Test creating cursor from dictionary."""
        item = {
            "id": 123,
            "created_at": "2026-03-07T12:00:00Z",
            "name": "test"
        }
        
        cursor_data = create_cursor_from_item(item)
        
        assert cursor_data.id == 123
        assert cursor_data.timestamp == "2026-03-07T12:00:00Z"
        assert cursor_data.sort_value is None

    def test_from_object(self):
        """Test creating cursor from object."""
        class Item:
            def __init__(self):
                self.id = 456
                self.created_at = "2026-03-07T12:00:00Z"
                self.sort_field = "value"
        
        item = Item()
        cursor_data = create_cursor_from_item(
            item,
            timestamp_field="created_at",
            sort_field="sort_field"
        )
        
        assert cursor_data.id == 456
        assert cursor_data.timestamp == "2026-03-07T12:00:00Z"
        assert cursor_data.sort_value == "value"

    def test_from_object_with_datetime(self):
        """Test creating cursor from object with datetime field."""
        from datetime import datetime, timezone
        
        class Item:
            def __init__(self):
                self.id = 789
                self.created_at = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        
        item = Item()
        cursor_data = create_cursor_from_item(item)
        
        assert cursor_data.id == 789
        assert "2026-03-07" in cursor_data.timestamp

    def test_custom_fields(self):
        """Test creating cursor with custom field names."""
        item = {
            "pk": 999,
            "ts": "2026-03-07T12:00:00Z",
            "sort": "alpha"
        }
        
        cursor_data = create_cursor_from_item(
            item,
            id_field="pk",
            timestamp_field="ts",
            sort_field="sort"
        )
        
        assert cursor_data.id == 999
        assert cursor_data.timestamp == "2026-03-07T12:00:00Z"
        assert cursor_data.sort_value == "alpha"


class TestOffsetCursorAdapter:
    """Test offset to cursor adapter."""

    def test_offset_to_cursor(self):
        """Test converting offset to cursor."""
        cursor = OffsetCursorAdapter.offset_to_cursor(100)
        assert isinstance(cursor, str)
        
        # Decode and verify
        decoded = CursorEncoder.decode(cursor, "offset_compat")
        assert decoded.id == 100
        assert decoded.sort_value == "offset"

    def test_cursor_to_offset(self):
        """Test converting cursor back to offset."""
        cursor = OffsetCursorAdapter.offset_to_cursor(50)
        offset = OffsetCursorAdapter.cursor_to_offset(cursor)
        
        assert offset == 50

    def test_cursor_to_offset_none(self):
        """Test converting None cursor returns 0."""
        offset = OffsetCursorAdapter.cursor_to_offset(None)
        assert offset == 0

    def test_cursor_to_offset_invalid(self):
        """Test converting invalid cursor returns 0."""
        offset = OffsetCursorAdapter.cursor_to_offset("invalid")
        assert offset == 0


class TestCursorData:
    """Test CursorData dataclass."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        data = CursorData(
            id=123,
            timestamp="2026-03-07T12:00:00Z",
            sort_value="test"
        )
        
        d = data.to_dict()
        assert d["id"] == 123
        assert d["timestamp"] == "2026-03-07T12:00:00Z"
        assert d["sort_value"] == "test"
        assert "filters" not in d  # None values excluded

    def test_from_dict(self):
        """Test creating from dictionary."""
        d = {
            "id": 456,
            "timestamp": "2026-03-07T12:00:00Z",
            "sort_value": "value",
            "filters": {"key": "value"}
        }
        
        data = CursorData.from_dict(d)
        assert data.id == 456
        assert data.timestamp == "2026-03-07T12:00:00Z"
        assert data.sort_value == "value"
        assert data.filters == {"key": "value"}


class TestPaginationResult:
    """Test PaginationResult dataclass."""

    def test_basic_creation(self):
        """Test creating pagination result."""
        items = [1, 2, 3]
        result = PaginationResult(
            items=items,
            next_cursor="cursor123",
            has_more=True,
            total=100
        )
        
        assert result.items == items
        assert result.next_cursor == "cursor123"
        assert result.has_more is True
        assert result.total == 100

    def test_without_total(self):
        """Test creating pagination result without total."""
        result = PaginationResult(
            items=[],
            next_cursor=None,
            has_more=False
        )
        
        assert result.total is None


class TestEdgeCases:
    """Test edge cases."""

    def test_unicode_in_cursor(self):
        """Test cursor with unicode characters."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id=1,
            sort_value="Hello 世界 🌍"
        )
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.sort_value == "Hello 世界 🌍"

    def test_large_cursor_data(self):
        """Test cursor with large data."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id=1,
            filters={"key": "x" * 1000}  # Large filter value
        )
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.filters["key"] == "x" * 1000

    def test_special_characters_in_secret(self):
        """Test cursor with special characters in secret key."""
        secret_key = "test!@#$%^&*()_+-=[]{}|;':\",./<>?"
        cursor_data = CursorData(id=123)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.id == 123

    @pytest.mark.asyncio
    async def test_concurrent_pagination(self):
        """Test pagination under simulated concurrent access."""
        paginator = CursorPaginator(secret_key="test")
        
        items = [{"id": i} for i in range(1, 101)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        # Get first page
        result1 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=20
        )
        
        # Simulate concurrent modification
        # (Remove some items that would be on next page)
        modified_items = items[:50]  # Half the items
        
        # Get second page with modified list
        # This simulates what happens under concurrent writes
        result2 = await paginator.paginate(
            items=modified_items,
            get_cursor_data=get_cursor_data,
            cursor=result1.next_cursor,
            page_size=20
        )
        
        # Cursor-based pagination should handle this gracefully
        assert result2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
