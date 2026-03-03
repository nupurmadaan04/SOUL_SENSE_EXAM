"""
Unit tests for Payload Size Limits and DoS Protection (Issue #1068).

Tests cover:
- Payload size validation
- JSON depth validation
- Array/object size validation
- Compression bomb detection
- Multipart validation
- Middleware integration
"""

import json
import gzip
import io
import zipfile
import pytest
from typing import Dict, Any

from api.utils.payload_validator import (
    calculate_json_depth,
    count_json_elements,
    validate_json_structure,
    validate_json_payload,
    check_compression_bomb,
    check_zip_bomb,
    get_content_length,
    should_validate_content_type,
    validate_content_length,
    PayloadValidationError,
    PayloadTooLargeError,
    PayloadDepthExceededError,
    PayloadStructureError,
    CompressionBombError,
)
from api.constants.errors import ErrorCode
from api.exceptions import (
    PayloadTooLargeException,
    PayloadDepthExceededException,
    PayloadMalformedException,
    CompressionBombException,
    MultipartTooManyPartsException,
)


class TestCalculateJsonDepth:
    """Tests for calculate_json_depth function."""
    
    def test_primitive_returns_zero(self):
        """Primitive values have depth 0."""
        assert calculate_json_depth("string") == 0
        assert calculate_json_depth(123) == 0
        assert calculate_json_depth(True) == 0
        assert calculate_json_depth(None) == 0
    
    def test_empty_object_returns_zero(self):
        """Empty object has depth 0."""
        assert calculate_json_depth({}) == 0
    
    def test_empty_array_returns_zero(self):
        """Empty array has depth 0."""
        assert calculate_json_depth([]) == 0
    
    def test_flat_object_depth_one(self):
        """Flat object has depth 1."""
        data = {"key": "value", "num": 123}
        assert calculate_json_depth(data) == 1
    
    def test_nested_object_depth(self):
        """Nested object depth is calculated correctly."""
        data = {"level1": {"level2": {"level3": "value"}}}
        assert calculate_json_depth(data) == 3
    
    def test_nested_array_depth(self):
        """Nested array depth is calculated correctly."""
        data = [[["deep"]]]
        assert calculate_json_depth(data) == 3
    
    def test_mixed_nesting(self):
        """Mixed object/array nesting is calculated correctly."""
        data = {"arr": [{"nested": "value"}]}
        assert calculate_json_depth(data) == 3
    
    def test_deeply_nested(self):
        """Very deep nesting is calculated correctly."""
        data = {}
        current = data
        for i in range(50):
            current["level"] = {}
            current = current["level"]
        assert calculate_json_depth(data) == 50


class TestCountJsonElements:
    """Tests for count_json_elements function."""
    
    def test_primitive_counts_zero(self):
        """Primitives have no array elements or object keys."""
        assert count_json_elements("string") == (0, 0)
        assert count_json_elements(123) == (0, 0)
    
    def test_empty_object(self):
        """Empty object has no keys."""
        assert count_json_elements({}) == (0, 0)
    
    def test_simple_object(self):
        """Simple object counts keys."""
        data = {"a": 1, "b": 2, "c": 3}
        assert count_json_elements(data) == (0, 3)
    
    def test_simple_array(self):
        """Simple array counts elements."""
        data = [1, 2, 3, 4, 5]
        assert count_json_elements(data) == (5, 0)
    
    def test_nested_counts_cumulative(self):
        """Nested structures count cumulatively."""
        data = {
            "arr1": [1, 2, 3],
            "obj1": {"a": 1, "b": 2},
            "arr2": [4, 5]
        }
        # arr1: 3, arr2: 2 = 5 array elements
        # root: 3, obj1: 2 = 5 object keys
        assert count_json_elements(data) == (5, 5)


class TestValidateJsonStructure:
    """Tests for validate_json_structure function."""
    
    def test_valid_structure_passes(self):
        """Valid JSON structure passes validation."""
        data = {"key": "value", "arr": [1, 2, 3]}
        validate_json_structure(data, max_depth=20, max_array_size=100, max_object_keys=100)
    
    def test_exceeds_depth_raises(self):
        """Exceeding max depth raises PayloadDepthExceededError."""
        data = {"level1": {"level2": {"level3": "deep"}}}
        with pytest.raises(PayloadDepthExceededError) as exc_info:
            validate_json_structure(data, max_depth=2)
        assert exc_info.value.details["depth"] == 3
        assert exc_info.value.details["max_depth"] == 2
    
    def test_exceeds_array_size_raises(self):
        """Exceeding max array size raises PayloadStructureError."""
        data = {"arr": list(range(101))}
        with pytest.raises(PayloadStructureError) as exc_info:
            validate_json_structure(data, max_array_size=100)
        assert "too many elements" in exc_info.value.message.lower()
    
    def test_exceeds_object_keys_raises(self):
        """Exceeding max object keys raises PayloadStructureError."""
        data = {f"key{i}": i for i in range(101)}
        with pytest.raises(PayloadStructureError) as exc_info:
            validate_json_structure(data, max_object_keys=100)
        assert "too many keys" in exc_info.value.message.lower()
    
    def test_exactly_at_limits_passes(self):
        """Exactly at limits passes validation."""
        data = {
            f"key{i}": list(range(100)) for i in range(100)
        }
        validate_json_structure(data, max_depth=3, max_array_size=100, max_object_keys=100)


class TestValidateJsonPayload:
    """Tests for validate_json_payload function."""
    
    def test_valid_json_string(self):
        """Valid JSON string passes validation."""
        body = '{"key": "value", "num": 123}'
        result = validate_json_payload(body)
        assert result == {"key": "value", "num": 123}
    
    def test_valid_json_bytes(self):
        """Valid JSON bytes passes validation."""
        body = b'{"key": "value", "num": 123}'
        result = validate_json_payload(body)
        assert result == {"key": "value", "num": 123}
    
    def test_malformed_json_raises(self):
        """Malformed JSON raises PayloadValidationError."""
        body = '{"key": invalid}'
        with pytest.raises(PayloadValidationError) as exc_info:
            validate_json_payload(body)
        assert exc_info.value.code == "MALFORMED_JSON"
    
    def test_deeply_nested_json_raises(self):
        """Deeply nested JSON raises PayloadDepthExceededError."""
        data = {}
        current = data
        for i in range(25):
            current["level"] = {}
            current = current["level"]
        body = json.dumps(data)
        
        with pytest.raises(PayloadDepthExceededError) as exc_info:
            validate_json_payload(body, max_depth=20)
        assert exc_info.value.details["depth"] > 20
    
    def test_large_array_json_raises(self):
        """Large array in JSON raises PayloadStructureError."""
        data = {"items": list(range(15000))}
        body = json.dumps(data)
        
        with pytest.raises(PayloadStructureError) as exc_info:
            validate_json_payload(body, max_array_size=10000)
        assert "too many elements" in exc_info.value.message.lower()


class TestCheckCompressionBomb:
    """Tests for check_compression_bomb function."""
    
    def test_empty_data_passes(self):
        """Empty data passes check."""
        check_compression_bomb(b"")
    
    def test_non_gzip_passes(self):
        """Non-gzip data passes check."""
        check_compression_bomb(b"not gzip data")
    
    def test_valid_gzip_passes(self):
        """Valid gzip with normal ratio passes."""
        data = b"Hello, World! " * 100
        compressed = gzip.compress(data)
        check_compression_bomb(compressed, threshold_ratio=100.0)
    
    def test_compression_bomb_detected(self):
        """Compression bomb is detected."""
        # Create data that compresses very well (high ratio)
        data = b"A" * 100000  # Highly compressible
        compressed = gzip.compress(data)
        
        # Check with low threshold
        with pytest.raises(CompressionBombError) as exc_info:
            check_compression_bomb(compressed, threshold_ratio=5.0)
        assert exc_info.value.details["compression_ratio"] > 5.0
    
    def test_invalid_gzip_passes(self):
        """Invalid gzip data passes (not an error)."""
        check_compression_bomb(b'\x1f\x8binvalid gzip')


class TestCheckZipBomb:
    """Tests for check_zip_bomb function."""
    
    def test_empty_data_passes(self):
        """Empty data passes check."""
        check_zip_bomb(b"")
    
    def test_non_zip_passes(self):
        """Non-zip data passes check."""
        check_zip_bomb(b"not zip data")
    
    def test_valid_zip_passes(self):
        """Valid zip with normal content passes."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.txt", "Hello, World!")
        
        check_zip_bomb(buffer.getvalue(), threshold_ratio=100.0)
    
    def test_too_many_files_raises(self):
        """Zip with too many files raises PayloadStructureError."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            for i in range(150):
                zf.writestr(f"file{i}.txt", "content")
        
        with pytest.raises(PayloadStructureError) as exc_info:
            check_zip_bomb(buffer.getvalue(), max_files=100)
        assert "too many files" in exc_info.value.message.lower()
    
    def test_invalid_zip_passes(self):
        """Invalid zip data passes (not an error)."""
        check_zip_bomb(b'PKinvalid zip')


class TestGetContentLength:
    """Tests for get_content_length function."""
    
    def test_no_header_returns_none(self):
        """No content-length header returns None."""
        from starlette.datastructures import Headers
        headers = Headers()
        assert get_content_length(headers) is None
    
    def test_valid_header_returns_int(self):
        """Valid content-length header returns integer."""
        from starlette.datastructures import Headers
        headers = Headers({"content-length": "1024"})
        assert get_content_length(headers) == 1024
    
    def test_invalid_header_returns_none(self):
        """Invalid content-length header returns None."""
        from starlette.datastructures import Headers
        headers = Headers({"content-length": "invalid"})
        assert get_content_length(headers) is None


class TestShouldValidateContentType:
    """Tests for should_validate_content_type function."""
    
    def test_none_returns_false(self):
        """None content type returns False."""
        assert should_validate_content_type(None) is False
    
    def test_json_returns_true(self):
        """JSON content types return True."""
        assert should_validate_content_type("application/json") is True
        assert should_validate_content_type("application/json; charset=utf-8") is True
        assert should_validate_content_type("text/json") is True
    
    def test_form_returns_true(self):
        """Form content types return True."""
        assert should_validate_content_type("application/x-www-form-urlencoded") is True
        assert should_validate_content_type("multipart/form-data") is True
    
    def test_xml_returns_true(self):
        """XML content types return True."""
        assert should_validate_content_type("application/xml") is True
        assert should_validate_content_type("text/xml") is True
    
    def test_other_returns_false(self):
        """Other content types return False."""
        assert should_validate_content_type("text/plain") is False
        assert should_validate_content_type("application/octet-stream") is False
        assert should_validate_content_type("image/png") is False


class TestValidateContentLength:
    """Tests for validate_content_length function."""
    
    def test_none_passes(self):
        """None content length passes."""
        validate_content_length(None, 10000)
    
    def test_within_limit_passes(self):
        """Content length within limit passes."""
        validate_content_length(1000, 10000)
    
    def test_at_limit_passes(self):
        """Content length at limit passes."""
        validate_content_length(10000, 10000)
    
    def test_exceeds_limit_raises(self):
        """Content length exceeding limit raises PayloadTooLargeError."""
        with pytest.raises(PayloadTooLargeError) as exc_info:
            validate_content_length(20000, 10000)
        assert exc_info.value.details["size_bytes"] == 20000
        assert exc_info.value.details["max_size_bytes"] == 10000


class TestPayloadExceptions:
    """Tests for payload exception classes."""
    
    def test_payload_too_large_exception(self):
        """PayloadTooLargeException has correct properties."""
        exc = PayloadTooLargeException(15000000, 10000000)
        assert exc.status_code == 413
        assert exc.detail["code"] == ErrorCode.PAYLOAD_TOO_LARGE.value
        assert "size_bytes" in exc.detail["details"]
        assert "size_mb" in exc.detail["details"]
    
    def test_payload_depth_exceeded_exception(self):
        """PayloadDepthExceededException has correct properties."""
        exc = PayloadDepthExceededException(50, 20)
        assert exc.status_code == 413
        assert exc.detail["code"] == ErrorCode.PAYLOAD_DEPTH_EXCEEDED.value
        assert exc.detail["details"]["depth"] == 50
        assert exc.detail["details"]["max_depth"] == 20
    
    def test_payload_malformed_exception(self):
        """PayloadMalformedException has correct properties."""
        exc = PayloadMalformedException("Invalid encoding")
        assert exc.status_code == 413
        assert exc.detail["code"] == ErrorCode.PAYLOAD_MALFORMED.value
        assert "Invalid encoding" in exc.detail["message"]
    
    def test_compression_bomb_exception(self):
        """CompressionBombException has correct properties."""
        exc = CompressionBombException(50.0, 10.0)
        assert exc.status_code == 413
        assert exc.detail["code"] == ErrorCode.PAYLOAD_COMPRESSION_BOMB.value
        assert exc.detail["details"]["compression_ratio"] == 50.0
        assert exc.detail["details"]["threshold"] == 10.0
    
    def test_multipart_too_many_parts_exception(self):
        """MultipartTooManyPartsException has correct properties."""
        exc = MultipartTooManyPartsException(200, 100)
        assert exc.status_code == 413
        assert exc.detail["code"] == ErrorCode.MULTIPART_TOO_MANY_PARTS.value
        assert exc.detail["details"]["parts"] == 200
        assert exc.detail["details"]["max_parts"] == 100


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_very_large_depth(self):
        """JSON with very large depth is caught."""
        # Note: Python's json module has a recursion limit (~1000)
        # We test with a depth that json can handle but our validator rejects
        data = {}
        current = data
        for i in range(150):  # Keep under Python's recursion limit
            current["level"] = {}
            current = current["level"]
        current["value"] = "deep"
        
        body = json.dumps(data)
        with pytest.raises(PayloadDepthExceededError):
            validate_json_payload(body, max_depth=100)
    
    def test_circular_reference_not_possible(self):
        """Circular references cannot exist in JSON (would fail parsing)."""
        # This test documents that JSON doesn't support circular references
        # If someone tried to send one, it would fail at JSON parsing
        pass
    
    def test_unicode_in_json(self):
        """Unicode characters in JSON are handled correctly."""
        data = {"message": "Hello 世界 🌍", "emoji": "🎉" * 100}
        body = json.dumps(data, ensure_ascii=False)
        result = validate_json_payload(body)
        assert result["message"] == "Hello 世界 🌍"
    
    def test_binary_data_in_json(self):
        """Binary data cannot be directly in JSON."""
        # JSON doesn't support binary data, it would need to be base64 encoded
        import base64
        binary_data = b"\x00\x01\x02\x03"
        encoded = base64.b64encode(binary_data).decode()
        data = {"binary": encoded}
        body = json.dumps(data)
        result = validate_json_payload(body)
        assert result["binary"] == encoded
