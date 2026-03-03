"""
Payload validation utilities for DoS protection.

This module provides functions to validate request payloads against
size limits, nesting depth, and other DoS attack vectors.

Issue #1068: Add Payload Size Limits and DoS Protection
"""

import json
import io
import gzip
import zipfile
from typing import Any, Dict, Tuple, Optional, Union
from starlette.datastructures import Headers
from starlette.types import Message


class PayloadValidationError(Exception):
    """Base exception for payload validation errors."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class PayloadTooLargeError(PayloadValidationError):
    """Payload exceeds maximum size limit."""
    def __init__(self, size_bytes: int, max_size_bytes: int):
        super().__init__(
            code="PAYLOAD_TOO_LARGE",
            message=f"Request body too large: {size_bytes} bytes (max: {max_size_bytes} bytes)",
            details={
                "size_bytes": size_bytes,
                "max_size_bytes": max_size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "max_size_mb": round(max_size_bytes / (1024 * 1024), 2)
            }
        )


class PayloadDepthExceededError(PayloadValidationError):
    """JSON nesting depth exceeds limit."""
    def __init__(self, depth: int, max_depth: int):
        super().__init__(
            code="PAYLOAD_DEPTH_EXCEEDED",
            message=f"JSON nesting depth exceeded: {depth} (max: {max_depth})",
            details={"depth": depth, "max_depth": max_depth}
        )


class PayloadStructureError(PayloadValidationError):
    """Payload structure violates limits (too many keys, array elements, etc.)."""
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="PAYLOAD_STRUCTURE_VIOLATION",
            message=f"Payload structure violation: {reason}",
            details=details
        )


class CompressionBombError(PayloadValidationError):
    """Compression bomb detected."""
    def __init__(self, ratio: float, threshold: float):
        super().__init__(
            code="COMPRESSION_BOMB",
            message=f"Compression bomb detected: ratio {ratio:.1f}:1 (threshold: {threshold}:1)",
            details={"compression_ratio": ratio, "threshold": threshold}
        )


def calculate_json_depth(obj: Any, current_depth: int = 0) -> int:
    """
    Calculate the maximum nesting depth of a JSON object.
    
    Args:
        obj: The JSON object (dict, list, or primitive)
        current_depth: Current depth in the recursion
        
    Returns:
        Maximum nesting depth
    """
    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(
            calculate_json_depth(v, current_depth + 1)
            for v in obj.values()
        )
    elif isinstance(obj, list):
        if not obj:
            return current_depth
        return max(
            calculate_json_depth(item, current_depth + 1)
            for item in obj
        )
    else:
        return current_depth


def count_json_elements(obj: Any) -> Tuple[int, int]:
    """
    Count the number of array elements and object keys in a JSON object.
    
    Args:
        obj: The JSON object
        
    Returns:
        Tuple of (total_array_elements, total_object_keys)
    """
    array_count = 0
    object_keys = 0
    
    if isinstance(obj, dict):
        object_keys += len(obj)
        for v in obj.values():
            arr, keys = count_json_elements(v)
            array_count += arr
            object_keys += keys
    elif isinstance(obj, list):
        array_count += len(obj)
        for item in obj:
            arr, keys = count_json_elements(item)
            array_count += arr
            object_keys += keys
    
    return array_count, object_keys


def validate_json_structure(
    obj: Any,
    max_depth: int = 20,
    max_array_size: int = 10000,
    max_object_keys: int = 1000,
    _current_depth: int = 0
) -> None:
    """
    Validate JSON structure against DoS limits.
    
    Args:
        obj: The JSON object to validate
        max_depth: Maximum allowed nesting depth
        max_array_size: Maximum allowed elements in any single array
        max_object_keys: Maximum allowed keys in any single object
        _current_depth: Current depth (internal use)
        
    Raises:
        PayloadDepthExceededError: If nesting depth exceeds limit
        PayloadStructureError: If structure violates limits
    """
    if _current_depth > max_depth:
        raise PayloadDepthExceededError(_current_depth, max_depth)
    
    if isinstance(obj, dict):
        if len(obj) > max_object_keys:
            raise PayloadStructureError(
                f"Object has too many keys: {len(obj)} (max: {max_object_keys})",
                {"keys": len(obj), "max_keys": max_object_keys}
            )
        for v in obj.values():
            validate_json_structure(v, max_depth, max_array_size, max_object_keys, _current_depth + 1)
    
    elif isinstance(obj, list):
        if len(obj) > max_array_size:
            raise PayloadStructureError(
                f"Array has too many elements: {len(obj)} (max: {max_array_size})",
                {"elements": len(obj), "max_elements": max_array_size}
            )
        for item in obj:
            validate_json_structure(item, max_depth, max_array_size, max_object_keys, _current_depth + 1)


def validate_json_payload(
    body: Union[str, bytes],
    max_depth: int = 20,
    max_array_size: int = 10000,
    max_object_keys: int = 1000
) -> Any:
    """
    Validate a JSON payload for DoS protection.
    
    Args:
        body: The raw JSON body (string or bytes)
        max_depth: Maximum allowed nesting depth
        max_array_size: Maximum allowed array elements
        max_object_keys: Maximum allowed object keys
        
    Returns:
        Parsed JSON object if valid
        
    Raises:
        PayloadValidationError: If validation fails
        json.JSONDecodeError: If JSON is malformed
    """
    # Parse JSON
    try:
        if isinstance(body, bytes):
            data = json.loads(body.decode('utf-8'))
        else:
            data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise PayloadValidationError(
            code="MALFORMED_JSON",
            message=f"Invalid JSON: {str(e)}",
            details={"error": str(e)}
        )
    
    # Validate structure
    validate_json_structure(data, max_depth, max_array_size, max_object_keys)
    
    return data


def check_compression_bomb(
    data: bytes,
    threshold_ratio: float = 10.0,
    max_uncompressed_size: int = 100 * 1024 * 1024
) -> None:
    """
    Check if gzip compressed data might be a compression bomb.
    
    Args:
        data: The compressed data
        threshold_ratio: Compression ratio threshold (compressed:uncompressed)
        max_uncompressed_size: Maximum allowed uncompressed size
        
    Raises:
        CompressionBombError: If compression bomb is detected
    """
    if not data:
        return
    
    # Check for gzip magic bytes
    if not data.startswith(b'\x1f\x8b'):
        return
    
    try:
        # Try to decompress and check size
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            # Read in chunks to avoid loading huge data
            total_size = 0
            chunk_size = 1024 * 1024  # 1MB chunks
            
            while True:
                chunk = gz.read(chunk_size)
                if not chunk:
                    break
                total_size += len(chunk)
                
                # Check uncompressed size limit
                if total_size > max_uncompressed_size:
                    raise CompressionBombError(
                        ratio=float('inf'),
                        threshold=threshold_ratio
                    )
        
        # Calculate compression ratio
        compressed_size = len(data)
        if compressed_size > 0:
            ratio = total_size / compressed_size
            if ratio > threshold_ratio:
                raise CompressionBombError(ratio=ratio, threshold=threshold_ratio)
                
    except (gzip.BadGzipFile, OSError):
        # Not a valid gzip file, ignore
        pass
    except CompressionBombError:
        raise
    except Exception:
        # Other errors, ignore
        pass


def check_zip_bomb(
    data: bytes,
    threshold_ratio: float = 10.0,
    max_total_size: int = 100 * 1024 * 1024,
    max_files: int = 1000
) -> None:
    """
    Check if zip data might be a compression bomb.
    
    Args:
        data: The zip file data
        threshold_ratio: Compression ratio threshold
        max_total_size: Maximum total uncompressed size
        max_files: Maximum number of files in archive
        
    Raises:
        CompressionBombError: If compression bomb is detected
    """
    if not data:
        return
    
    # Check for zip magic bytes
    if not data.startswith(b'PK'):
        return
    
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Check number of files
            if len(zf.namelist()) > max_files:
                raise PayloadStructureError(
                    f"Zip archive contains too many files: {len(zf.namelist())} (max: {max_files})",
                    {"files": len(zf.namelist()), "max_files": max_files}
                )
            
            # Check total uncompressed size
            total_compressed = 0
            total_uncompressed = 0
            
            for info in zf.infolist():
                total_compressed += info.compress_size
                total_uncompressed += info.file_size
                
                # Check individual file size
                if info.file_size > max_total_size:
                    raise CompressionBombError(
                        ratio=float('inf'),
                        threshold=threshold_ratio
                    )
            
            # Check compression ratio
            if total_compressed > 0:
                ratio = total_uncompressed / total_compressed
                if ratio > threshold_ratio:
                    raise CompressionBombError(ratio=ratio, threshold=threshold_ratio)
                    
    except (zipfile.BadZipFile, OSError):
        # Not a valid zip file, ignore
        pass
    except (CompressionBombError, PayloadStructureError):
        raise
    except Exception:
        # Other errors, ignore
        pass


def get_content_length(headers: Headers) -> Optional[int]:
    """
    Get content length from headers.
    
    Args:
        headers: The request headers
        
    Returns:
        Content length as integer, or None if not present/invalid
    """
    content_length = headers.get("content-length")
    if content_length:
        try:
            return int(content_length)
        except (ValueError, TypeError):
            pass
    return None


def should_validate_content_type(content_type: Optional[str]) -> bool:
    """
    Determine if a content type should be validated for DoS protection.
    
    Args:
        content_type: The Content-Type header value
        
    Returns:
        True if should validate, False otherwise
    """
    if not content_type:
        return False
    
    content_type = content_type.lower()
    
    # Validate JSON content types
    if any(ct in content_type for ct in ['application/json', 'text/json']):
        return True
    
    # Validate form data (url-encoded and multipart)
    if any(ct in content_type for ct in ['application/x-www-form-urlencoded', 'multipart/form-data']):
        return True
    
    # Validate XML content types (potential XXE and bomb attacks)
    if any(ct in content_type for ct in ['application/xml', 'text/xml']):
        return True
    
    return False


def validate_content_length(
    content_length: Optional[int],
    max_size_bytes: int
) -> None:
    """
    Validate content length header against maximum size.
    
    Args:
        content_length: The content length value (may be None)
        max_size_bytes: Maximum allowed size
        
    Raises:
        PayloadTooLargeError: If content length exceeds limit
    """
    if content_length is not None and content_length > max_size_bytes:
        raise PayloadTooLargeError(content_length, max_size_bytes)
