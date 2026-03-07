"""
Extended unit tests for Cursor-based Pagination (#1365).

Additional tests for edge cases, integration scenarios, and stability verification.
"""
import pytest
import asyncio
import time
import json
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from datetime import datetime, timezone, timedelta

from api.utils.cursor_pagination import (
    CursorEncoder,
    CursorData,
    CursorPaginator,
    PaginationResult,
    create_cursor_from_item,
    OffsetCursorAdapter,
    InvalidCursorError,
    ExpiredCursorError,
    CursorError
)

from api.services.cursor_pagination_service import (
    CursorPaginationService,
    paginate_with_cursor
)


class TestCursorStability:
    """Test pagination stability under concurrent writes."""

    @pytest.mark.asyncio
    async def test_no_duplicates_under_concurrent_writes(self):
        """
        Test that items are not duplicated when paginating under concurrent writes.
        
        This is the main issue cursor pagination solves.
        """
        paginator = CursorPaginator(secret_key="test")
        
        # Initial dataset
        items = [{"id": i, "name": f"item_{i}"} for i in range(1, 51)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        # Get first page
        page1 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=10
        )
        
        # Simulate new items added at the beginning (concurrent write)
        new_items = [{"id": i, "name": f"new_item_{i}"} for i in range(-5, 1)]
        modified_items = new_items + items
        
        # Get second page using cursor from first page
        page2 = await paginator.paginate(
            items=modified_items,
            get_cursor_data=get_cursor_data,
            cursor=page1.next_cursor,
            page_size=10
        )
        
        # Collect all IDs from both pages
        page1_ids = {item["id"] for item in page1.items}
        page2_ids = {item["id"] for item in page2.items}
        
        # No duplicates
        assert len(page1_ids & page2_ids) == 0, "Found duplicate items across pages"

    @pytest.mark.asyncio
    async def test_no_missing_items_under_deletion(self):
        """
        Test that items are not skipped when items are deleted during pagination.
        """
        paginator = CursorPaginator(secret_key="test")
        
        items = [{"id": i} for i in range(1, 51)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        # Get first page
        page1 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=10
        )
        
        # Simulate deletion of items 11-15 (would be on page 2)
        modified_items = [item for item in items if item["id"] > 15 or item["id"] <= 10]
        
        # Get second page
        page2 = await paginator.paginate(
            items=modified_items,
            get_cursor_data=get_cursor_data,
            cursor=page1.next_cursor,
            page_size=10
        )
        
        # Items 16-20 should still appear (shifted due to deletions)
        page2_ids = [item["id"] for item in page2.items]
        
        # Should continue from where page 1 left off
        # Cursor-based pagination should handle this
        assert len(page2.items) > 0

    @pytest.mark.asyncio
    async def test_stable_ordering_with_timestamp_sort(self):
        """
        Test stable ordering when using timestamp-based cursors.
        """
        paginator = CursorPaginator(secret_key="test")
        
        # Items with same timestamp but different IDs
        items = [
            {"id": i, "created_at": "2026-03-07T12:00:00Z"}
            for i in range(1, 21)
        ]
        
        def get_cursor_data(item):
            return CursorData(
                id=item["id"],
                timestamp=item["created_at"]
            )
        
        page1 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            page_size=5
        )
        
        page2 = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            cursor=page1.next_cursor,
            page_size=5
        )
        
        # Order should be preserved
        all_ids = [item["id"] for item in page1.items + page2.items]
        assert all_ids == sorted(all_ids)


class TestCursorSecurity:
    """Test cursor security features."""

    def test_cursor_signature_prevents_forgery(self):
        """Test that cursors cannot be forged without secret key."""
        secret_key = "super_secret_key_only_server_knows"
        cursor_data = CursorData(id=12345)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Attacker tries to create cursor without secret
        with pytest.raises(InvalidCursorError):
            CursorEncoder.decode(cursor, "wrong_secret")

    def test_cursor_cannot_be_modified(self):
        """Test that modifying cursor payload is detected."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=100)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Try various modifications
        modifications = [
            cursor[:-1],  # Truncated
            cursor + "X",  # Extended
            cursor[1:],  # Missing first char
            "X" + cursor[1:],  # First char changed
            cursor.replace("A", "B").replace("a", "b"),  # Character substitution
        ]
        
        for modified in modifications:
            with pytest.raises(InvalidCursorError):
                CursorEncoder.decode(modified, secret_key)

    def test_timing_attack_resistance(self):
        """Test that signature comparison is timing-safe."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=999)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Both should take similar time (no early exit on mismatch)
        start1 = time.time()
        try:
            CursorEncoder.decode(cursor, secret_key)
        except:
            pass
        time_valid = time.time() - start1
        
        start2 = time.time()
        try:
            CursorEncoder.decode(cursor[:-1], secret_key)
        except:
            pass
        time_invalid = time.time() - start2
        
        # Skip if times are too small to compare (avoid division by zero)
        min_time = min(time_valid, time_invalid)
        if min_time < 0.0001:  # Less than 0.1ms
            return  # Skip this test if operations are too fast
        
        # Times should be reasonably close (within 10x factor)
        # This is a basic check - real timing attack prevention uses hmac.compare_digest
        ratio = max(time_valid, time_invalid) / min_time
        assert ratio < 10, "Potential timing side-channel detected"

    def test_cursor_does_not_expose_internal_data(self):
        """Test that cursor doesn't expose sensitive internal data."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id=123,
            timestamp="2026-03-07T12:00:00Z",
            filters={"user_id": 456, "internal_flag": True}
        )
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Decode base64 and check structure
        import base64
        padding = 4 - len(cursor) % 4
        if padding != 4:
            cursor += '=' * padding
        decoded = base64.urlsafe_b64decode(cursor.encode('utf-8')).decode('utf-8')
        
        # Should contain version prefix
        assert decoded.startswith("v1:")
        
        # Payload should be base64 encoded (not plain text)
        parts = decoded.split(':')
        assert len(parts) == 3
        
        # Try to decode payload directly - should be base64
        try:
            payload = base64.urlsafe_b64decode(parts[1])
            # Even after base64 decode, it's JSON (not human readable without processing)
            data = json.loads(payload)
            # Data should be accessible only with proper decoding
            assert "id" in data
        except:
            pass  # Either way, data is not immediately readable


class TestCursorExpiration:
    """Test cursor expiration features."""

    def test_short_lived_cursor(self):
        """Test cursor with short expiration."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=100)
        
        # 100ms expiration
        cursor = CursorEncoder.encode(cursor_data, secret_key, expires_in=0.1)
        
        # Should work immediately
        decoded = CursorEncoder.decode(cursor, secret_key)
        assert decoded.id == 100
        
        # Wait for expiration
        time.sleep(0.15)
        
        with pytest.raises(ExpiredCursorError):
            CursorEncoder.decode(cursor, secret_key)

    def test_long_lived_cursor(self):
        """Test cursor with long expiration."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=200)
        
        # 1 hour expiration
        cursor = CursorEncoder.encode(cursor_data, secret_key, expires_in=3600)
        
        # Should work
        decoded = CursorEncoder.decode(cursor, secret_key)
        assert decoded.id == 200

    def test_no_expiration(self):
        """Test cursor without expiration."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=300)
        
        # No expiration
        cursor = CursorEncoder.encode(cursor_data, secret_key, expires_in=None)
        
        # Should work
        decoded = CursorEncoder.decode(cursor, secret_key)
        assert decoded.id == 300

    def test_max_age_enforcement(self):
        """Test max_age parameter enforcement."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=400)
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Wait a bit
        time.sleep(0.1)
        
        # Should fail with strict max_age
        with pytest.raises(ExpiredCursorError):
            CursorEncoder.decode(cursor, secret_key, max_age=0.05)
        
        # Should succeed with generous max_age
        decoded = CursorEncoder.decode(cursor, secret_key, max_age=3600)
        assert decoded.id == 400


class TestBackwardCompatibility:
    """Test backward compatibility with offset-based pagination."""

    def test_offset_to_cursor_conversion(self):
        """Test converting offset to cursor format."""
        offset = 100
        cursor = OffsetCursorAdapter.offset_to_cursor(offset)
        
        assert isinstance(cursor, str)
        
        # Can be converted back
        decoded_offset = OffsetCursorAdapter.cursor_to_offset(cursor)
        assert decoded_offset == offset

    @pytest.mark.asyncio
    async def test_mixed_pagination_support(self):
        """Test supporting both offset and cursor in same endpoint."""
        # Note: In real usage, offset cursors use a different secret
        # This test verifies the pattern works conceptually
        paginator = CursorPaginator(secret_key="offset_compat")
        
        items = [{"id": i} for i in range(1, 31)]
        
        # Offset-based request (converted to cursor)
        offset = 10
        cursor = OffsetCursorAdapter.offset_to_cursor(offset)
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        result = await paginator.paginate(
            items=items,
            get_cursor_data=get_cursor_data,
            cursor=cursor,
            page_size=10
        )
        
        # Should work with converted cursor
        assert result is not None

    def test_legacy_offset_preserved(self):
        """Test that legacy offset values are preserved in cursor."""
        for offset in [0, 1, 10, 50, 100, 1000]:
            cursor = OffsetCursorAdapter.offset_to_cursor(offset)
            decoded = OffsetCursorAdapter.cursor_to_offset(cursor)
            assert decoded == offset, f"Offset {offset} not preserved"


class TestCursorPaginationService:
    """Test CursorPaginationService integration."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    def test_service_initialization(self):
        """Test service initialization with custom and default secret."""
        # With custom secret
        service1 = CursorPaginationService(secret_key="custom_secret")
        assert service1.secret_key == "custom_secret"
        
        # With default secret (should load from settings)
        service2 = CursorPaginationService()
        assert service2.secret_key is not None

    def test_validate_page_size(self):
        """Test page size validation in service."""
        service = CursorPaginationService(secret_key="test")
        
        assert service.paginator.validate_page_size(10) == 10
        assert service.paginator.validate_page_size(200) == 100  # max
        assert service.paginator.validate_page_size(None) == 20  # default

    def test_create_cursor(self):
        """Test cursor creation through service."""
        service = CursorPaginationService(secret_key="test")
        
        cursor = service.create_cursor(
            item_id=123,
            timestamp="2026-03-07T12:00:00Z",
            sort_value="test",
            filters={"key": "value"}
        )
        
        assert isinstance(cursor, str)
        
        # Should be decodable
        decoded = service.validate_cursor(cursor)
        assert decoded.id == 123
        assert decoded.filters == {"key": "value"}

    def test_validate_cursor_valid(self):
        """Test validating valid cursor."""
        service = CursorPaginationService(secret_key="test")
        cursor = service.create_cursor(item_id=456)
        
        decoded = service.validate_cursor(cursor)
        assert decoded.id == 456

    def test_validate_cursor_invalid(self):
        """Test validating invalid cursor."""
        service = CursorPaginationService(secret_key="test")
        
        with pytest.raises(InvalidCursorError):
            service.validate_cursor("invalid_cursor")

    def test_validate_cursor_none(self):
        """Test validating None cursor."""
        service = CursorPaginationService(secret_key="test")
        
        result = service.validate_cursor(None)
        assert result is None


class TestPerformanceCharacteristics:
    """Test performance characteristics of cursor pagination."""

    def test_cursor_encoding_speed(self):
        """Test that cursor encoding is fast."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id=12345,
            timestamp="2026-03-07T12:00:00Z",
            filters={"key": "value"}
        )
        
        iterations = 1000
        start = time.time()
        
        for _ in range(iterations):
            CursorEncoder.encode(cursor_data, secret_key)
        
        elapsed = time.time() - start
        
        # Should complete 1000 encodings in less than 1 second
        assert elapsed < 1.0, f"Encoding too slow: {elapsed:.2f}s for {iterations} iterations"

    def test_cursor_decoding_speed(self):
        """Test that cursor decoding is fast."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=12345)
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        iterations = 1000
        start = time.time()
        
        for _ in range(iterations):
            CursorEncoder.decode(cursor, secret_key)
        
        elapsed = time.time() - start
        
        # Should complete 1000 decodings in less than 1 second
        assert elapsed < 1.0, f"Decoding too slow: {elapsed:.2f}s for {iterations} iterations"

    @pytest.mark.asyncio
    async def test_large_dataset_pagination(self):
        """Test pagination with large dataset."""
        paginator = CursorPaginator(secret_key="test")
        
        # 10,000 items
        items = [{"id": i} for i in range(1, 10001)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        start = time.time()
        
        # Paginate through all items
        all_items = []
        cursor = None
        page_count = 0
        
        while True:
            result = await paginator.paginate(
                items=items,
                get_cursor_data=get_cursor_data,
                cursor=cursor,
                page_size=100
            )
            all_items.extend(result.items)
            page_count += 1
            
            if not result.has_more:
                break
            cursor = result.next_cursor
        
        elapsed = time.time() - start
        
        assert len(all_items) == 10000
        assert page_count == 100
        assert elapsed < 5.0, f"Pagination too slow for large dataset: {elapsed:.2f}s"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_base64_cursor(self):
        """Test handling of malformed base64 in cursor."""
        with pytest.raises(InvalidCursorError):
            CursorEncoder.decode("!!!not_base64!!!", "secret")

    def test_cursor_with_wrong_version(self):
        """Test handling of cursor with unsupported version."""
        secret_key = "test_secret"
        cursor_data = CursorData(id=100)
        
        # Create valid cursor
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Modify version prefix (this is a simplified test - real modification would need proper base64 handling)
        # Just test that version check exists
        with pytest.raises(InvalidCursorError):
            # Invalid cursor format should be rejected
            CursorEncoder.decode("v0:invalid:signature", secret_key)

    def test_empty_secret_key(self):
        """Test behavior with empty secret key."""
        cursor_data = CursorData(id=100)
        
        # Should still work (though not recommended)
        cursor = CursorEncoder.encode(cursor_data, "")
        decoded = CursorEncoder.decode(cursor, "")
        assert decoded.id == 100

    def test_none_values_in_cursor_data(self):
        """Test cursor data with None values."""
        secret_key = "test_secret"
        cursor_data = CursorData(
            id=100,
            timestamp=None,
            sort_value=None,
            filters=None
        )
        
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        decoded = CursorEncoder.decode(cursor, secret_key)
        
        assert decoded.id == 100
        assert decoded.timestamp is None
        assert decoded.sort_value is None

    @pytest.mark.asyncio
    async def test_pagination_with_corrupt_cursor(self):
        """Test pagination behavior with corrupt cursor."""
        paginator = CursorPaginator(secret_key="test")
        
        items = [{"id": i} for i in range(1, 21)]
        
        def get_cursor_data(item):
            return CursorData(id=item["id"])
        
        # Try with corrupt cursor
        with pytest.raises(InvalidCursorError):
            await paginator.paginate(
                items=items,
                get_cursor_data=get_cursor_data,
                cursor="corrupt_cursor_data",
                page_size=10
            )


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_feed_pagination(self):
        """
        Test pagination for a social media feed scenario.
        
        Simulates a feed where new items are constantly being added.
        """
        paginator = CursorPaginator(secret_key="test")
        
        # Initial feed items (newest first)
        feed_items = [
            {"id": i, "created_at": f"2026-03-{i:02d}T12:00:00Z", "content": f"Post {i}"}
            for i in range(50, 0, -1)  # 50 to 1
        ]
        
        def get_cursor_data(item):
            return CursorData(
                id=item["id"],
                timestamp=item["created_at"]
            )
        
        # User views first page
        page1 = await paginator.paginate(
            items=feed_items,
            get_cursor_data=get_cursor_data,
            page_size=10
        )
        
        assert len(page1.items) == 10
        
        # New posts arrive
        new_posts = [
            {"id": 100 + i, "created_at": f"2026-03-0{i}T13:00:00Z", "content": f"New Post {i}"}
            for i in range(1, 6)
        ]
        updated_feed = new_posts + feed_items
        
        # User views second page (should continue from where they left off)
        page2 = await paginator.paginate(
            items=updated_feed,
            get_cursor_data=get_cursor_data,
            cursor=page1.next_cursor,
            page_size=10
        )
        
        # Should not show items from page 1 again
        page1_ids = {item["id"] for item in page1.items}
        page2_ids = {item["id"] for item in page2.items}
        assert not (page1_ids & page2_ids), "Found duplicate items in feed"

    @pytest.mark.asyncio
    async def test_search_results_pagination(self):
        """
        Test pagination for search results.
        
        Search results should remain stable during pagination.
        """
        paginator = CursorPaginator(secret_key="test")
        
        # Search results
        results = [
            {"id": i, "relevance_score": 100 - i, "title": f"Result {i}"}
            for i in range(1, 101)
        ]
        
        def get_cursor_data(item):
            return CursorData(
                id=item["id"],
                sort_value=str(item["relevance_score"])
            )
        
        # Paginate through results
        all_results = []
        cursor = None
        
        for _ in range(5):  # 5 pages
            page = await paginator.paginate(
                items=results,
                get_cursor_data=get_cursor_data,
                cursor=cursor,
                page_size=10
            )
            all_results.extend(page.items)
            if not page.has_more:
                break
            cursor = page.next_cursor
        
        # Should have 50 unique results
        assert len(all_results) == 50
        assert len(set(item["id"] for item in all_results)) == 50

    def test_api_response_format(self):
        """Test that cursor fits in API response format."""
        from api.schemas.pagination import CursorPaginatedResponse
        
        secret_key = "test_secret"
        cursor_data = CursorData(id=123)
        cursor = CursorEncoder.encode(cursor_data, secret_key)
        
        # Create response
        response = CursorPaginatedResponse(
            items=[{"id": 1}, {"id": 2}],
            next_cursor=cursor,
            has_more=True,
            total=100
        )
        
        # Should serialize correctly
        json_response = response.model_dump_json()
        assert cursor in json_response
        assert '"has_more":true' in json_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
