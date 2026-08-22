"""
Model versioning compatibility layer for SoulSense ML components.
Provides backward compatibility and versioning support for ML models.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class ModelVersion:
    """Represents a model version with metadata."""

    def __init__(self, version: str, model_path: str, metadata: Dict[str, Any]):
        self.version = version
        self.model_path = model_path
        self.metadata = metadata
        self.created_at = metadata.get('created_at', '')
        self.accuracy = metadata.get('accuracy', 0.0)

    def __str__(self):
        return f"ModelVersion(v{self.version}, accuracy={self.accuracy:.3f})"

class ModelVersionManager:
    """Manages model versions and provides versioning functionality."""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.version_file = self.models_dir / "versions.json"
        self._load_versions()

    def _load_versions(self):
        """Load version information from disk."""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r') as f:
                    self.versions = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.versions = {}
        else:
            self.versions = {}

    def _save_versions(self):
        """Save version information to disk."""
        try:
            with open(self.version_file, 'w') as f:
                json.dump(self.versions, f, indent=2)
        except IOError:
            pass  # Silently fail if can't save

    def register_model(self, name: str, version: str, model_path: str, metadata: Dict[str, Any]):
        """Register a new model version."""
        if name not in self.versions:
            self.versions[name] = {}

        self.versions[name][version] = {
            'model_path': model_path,
            'metadata': metadata,
            'created_at': metadata.get('created_at', '')
        }
        self._save_versions()

    def get_latest_version(self, name: str) -> Optional[ModelVersion]:
        """Get the latest version of a model."""
        if name not in self.versions or not self.versions[name]:
            return None

        # Find version with highest accuracy or latest creation date
        versions = self.versions[name]
        best_version = None
        best_score = -1

        for ver, info in versions.items():
            accuracy = info['metadata'].get('accuracy', 0.0)
            if accuracy > best_score:
                best_score = accuracy
                best_version = ver

        if best_version:
            return ModelVersion(best_version, versions[best_version]['model_path'], versions[best_version]['metadata'])

        return None

    def get_model_path(self, name: str, version: Optional[str] = None) -> Optional[str]:
        """Get the path to a specific model version."""
        if name not in self.versions:
            return None

        if version is None:
            latest = self.get_latest_version(name)
            return latest.model_path if latest else None

        if version in self.versions[name]:
            return self.versions[name][version]['model_path']

        return None

# Global instance for easy access
version_manager = ModelVersionManager()

# Compatibility functions for existing code
def get_model_version(name: str, version: Optional[str] = None) -> Optional[ModelVersion]:
    """Get a model version (compatibility function)."""
    if version:
        if name in version_manager.versions and version in version_manager.versions[name]:
            info = version_manager.versions[name][version]
            return ModelVersion(version, info['model_path'], info['metadata'])
        return None
    else:
        return version_manager.get_latest_version(name)

def register_model_version(name: str, version: str, path: str, metadata: Dict[str, Any]):
    """Register a model version (compatibility function)."""
    version_manager.register_model(name, version, path, metadata)

def get_model_path(name: str, version: Optional[str] = None) -> Optional[str]:
    """Get model path (compatibility function)."""
    return version_manager.get_model_path(name, version)
