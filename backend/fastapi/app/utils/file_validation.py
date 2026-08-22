import os
import re
import platform
from typing import List, Optional, Union
from app.exceptions import ValidationError

# Windows Reserved Names
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def sanitize_filename(filename: str, fallback: str = "unnamed_file") -> str:
    """
    Sanitize a filename to ensure it's safe for the filesystem.
    
    Args:
        filename: The user-provided filename.
        fallback: A default name to use if sanitization results in an empty string.
        
    Returns:
        A safe filename string.
    """
    if not filename:
        return fallback

    # 1. Remove dangerous characters (shell metachars, slashes, null bytes)
    # Keep alphanumeric, dots, hyphens, underscores, and spaces
    clean_name = re.sub(r'[^a-zA-Z0-9.\-_ ]', '', filename)
    clean_name = clean_name.strip()
    
    # 2. Check for reserved names (Windows)
    root, _ = os.path.splitext(clean_name)
    if root.upper() in RESERVED_NAMES:
        clean_name = f"_{clean_name}"
        
    # 3. Handle empty result
    if not clean_name:
        return fallback
        
    return clean_name

def validate_file_path(
    path: str, 
    allowed_extensions: Optional[List[str]] = None, 
    must_exist: bool = False, 
    base_dir: Optional[str] = None
) -> str:
    """
    Validate a file path for security and correctness.
    
    Args:
        path: The file path to validate.
        allowed_extensions: List of allowed extensions (e.g., ['.json', '.csv']). Case insensitive.
        must_exist: If True, the file must already exist.
        base_dir: If provided, the resolved path MUST be within this directory (prevents traversal).
        
    Returns:
        The text-normalized absolute path.
        
    Raises:
        ValidationError: If any validation check fails.
    """
    if not path:
        raise ValidationError("File path cannot be empty.")

    # 1. Path Length Check (Approximate Windows MAX_PATH safety)
    if len(path) > 255:
        raise ValidationError("File path is too long (max 255 characters).")

    try:
        # 2. Resolve Path (handle symlinks and relative paths)
        # os.path.realpath resolves symlinks, abspath does not always on all platforms
        absolute_path = os.path.realpath(os.path.abspath(path))
    except Exception as e:
         raise ValidationError(f"Invalid file path structure: {e}")

    # 3. Base Directory Confinement (Path Traversal Prevention)
    if base_dir:
        resolved_base = os.path.realpath(os.path.abspath(base_dir))
        # Use commonpath to check if absolute_path is subpath of resolved_base
        # This is safer than startswith for path comparison
        try:
            common = os.path.commonpath([resolved_base, absolute_path])
            if common != resolved_base:
                raise ValidationError("Access denied: Path is outside the allowed directory.")
        except ValueError:
             # Can happen on Windows if paths are on different drives
             raise ValidationError("Access denied: Path is on a different drive.")

    # 4. Extension Validation
    if allowed_extensions:
        _, ext = os.path.splitext(absolute_path)
        # Normalize extensions to lowercase for comparison
        valid_exts = [e.lower() if e.startswith('.') else f".{e.lower()}" for e in allowed_extensions]
        if ext.lower() not in valid_exts:
            raise ValidationError(f"Invalid file extension '{ext}'. Allowed: {', '.join(valid_exts)}")

    # 5. Existence Check (if required)
    if must_exist and not os.path.exists(absolute_path):
        raise ValidationError(f"File not found: {path}")
        
    # 6. Check for directory-ness (we usually expect a file)
    if os.path.isdir(absolute_path):
         raise ValidationError(f"Path is a directory, expected a file: {path}")

    return absolute_path
