"""Efficient file I/O operations"""
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class FileIOManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._file_cache = {}
        self._cache_lock = threading.Lock()
    
    @lru_cache(maxsize=32)
    def read_json_cached(self, filepath: str):
        """Cached JSON file reading"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return {}
    
    def write_json_async(self, filepath: str, data: dict):
        """Async JSON writing"""
        def write_task():
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.debug(f"Wrote {filepath}")
            except Exception as e:
                logger.error(f"Failed to write {filepath}: {e}")
        
        return self.executor.submit(write_task)
    
    def read_file_chunked(self, filepath: str, chunk_size: int = 8192):
        """Memory-efficient file reading"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
    
    def batch_write_files(self, file_data: dict):
        """Batch write multiple files"""
        futures = []
        for filepath, data in file_data.items():
            if isinstance(data, dict):
                future = self.write_json_async(filepath, data)
            else:
                future = self.executor.submit(self._write_text, filepath, data)
            futures.append(future)
        return futures
    
    def _write_text(self, filepath: str, content: str):
        """Write text file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write {filepath}: {e}")
    
    def clear_cache(self):
        """Clear file cache"""
        self.read_json_cached.cache_clear()
        with self._cache_lock:
            self._file_cache.clear()
    
    def shutdown(self):
        """Shutdown executor"""
        self.executor.shutdown(wait=True)

# Global file manager
file_manager = FileIOManager()

def read_config_fast(filepath: str):
    """Fast config reading with caching"""
    return file_manager.read_json_cached(filepath)

def save_data_async(filepath: str, data: dict):
    """Async data saving"""
    return file_manager.write_json_async(filepath, data)