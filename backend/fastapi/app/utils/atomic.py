
import os
import contextlib
import tempfile
import shutil
import logging
import time
import random
from typing import Generator, Any

logger = logging.getLogger(__name__)

# Constants for retry logic
MAX_RETRIES = 5
BASE_DELAY = 0.1  # seconds

@contextlib.contextmanager
def atomic_write(filepath: str, mode: str = "w", encoding: str = "utf-8", **kwargs: Any) -> Generator[Any, None, None]:
    """
    Context manager for atomic file writes.
    
    Writes to a temporary file in the same directory, then atomically renames it
    to the target filepath. ensures data durability with fsync.
    
    Args:
        filepath: Target file path
        mode: File mode (default 'w')
        encoding: File encoding (default 'utf-8')
        **kwargs: Additional arguments passed to open()
        
    Yields:
        File object for writing
    """
    # Create temp file in same directory to ensure atomic move (no cross-device link error)
    dirname = os.path.dirname(os.path.abspath(filepath))
    basename = os.path.basename(filepath)
    
    # Ensure directory exists
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
        
    # Create temp file
    # We use delete=False because we want to close it before renaming
    # suffix .tmp makes it easy to identify
    prefix = f".{basename}_"
    fd, temp_path = tempfile.mkstemp(dir=dirname, prefix=prefix, suffix=".tmp", text="b" not in mode)
    
    f = None
    try:
        # Open the file handle returned by mkstemp
        f = os.fdopen(fd, mode, encoding=encoding if "b" not in mode else None, **kwargs)
        
        # Yield file to caller
        yield f
        
        # Flush internal buffers to OS
        f.flush()
        
        # Force OS to flush to disk
        os.fsync(f.fileno())
        
        # Close file before moving
        f.close()
        f = None # prevent closing again in finally
        
        # Copy permissions from target if it exists
        if os.path.exists(filepath):
            try:
                shutil.copymode(filepath, temp_path)
            except OSError as e:
                logger.warning(f"Could not copy permissions for {filepath}: {e}")
        
        # Atomic rename with retry for Windows locking issues
        _rename_with_retry(temp_path, filepath)
            
    except Exception as e:
        # If an error occurred, try to close
        if f:
            try:
                f.close()
            except Exception:
                pass
        
        # Delete temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as cleanup_error:
                logger.warning(f"Failed to clean up temp file {temp_path}: {cleanup_error}")
                
        raise e

def _rename_with_retry(src: str, dst: str) -> None:
    """
    Rename src to dst with retries to handle Windows transient file locks.
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            # os.replace is atomic on POSIX and Windows (Python 3.3+)
            os.replace(src, dst)
            return
        except OSError as e:
            last_error = e
            # Check for common Windows lock error codes
            # 13: Permission denied, 32: Sharing violation
            # On POSIX, we might get checking too, but retry is generally safe
            logger.debug(f"Rename failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            # Linear backoff with jitter
            delay = BASE_DELAY * (attempt + 1) + (random.random() * 0.1)
            time.sleep(delay)
            
    # If we get here, all retries failed
    raise OSError(f"Failed to replace {dst} with atomic write after {MAX_RETRIES} attempts. Last error: {last_error}") from last_error
