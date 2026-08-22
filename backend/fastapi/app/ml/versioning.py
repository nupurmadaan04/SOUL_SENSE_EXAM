"""
Model Versioning System for SoulSense ML
Provides version control for trained ML models and experiments.

Features:
- Semantic versioning for models
- Model registry with metadata tracking
- Experiment logging and comparison
- Model rollback capabilities
- A/B testing support
"""

import os
import json
import pickle
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
import uuid
import logging
from app.config import MODELS_DIR, DATA_DIR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for a versioned model."""
    model_id: str
    version: str
    name: str
    description: str
    created_at: str
    model_type: str
    framework: str
    metrics: Dict[str, float]
    parameters: Dict[str, Any]
    feature_names: List[str]
    class_names: List[str]
    tags: List[str] = field(default_factory=list)
    parent_version: Optional[str] = None
    is_production: bool = False
    file_hash: str = ""
    file_size_bytes: int = 0
    training_data_info: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class ExperimentRecord:
    """Record for an experiment."""
    experiment_id: str
    name: str
    description: str
    timestamp: str
    model_version: str
    dataset_info: Dict[str, Any]
    hyperparameters: Dict[str, Any]
    metrics: Dict[str, float]
    artifacts: List[str]
    status: str  # 'running', 'completed', 'failed'
    duration_seconds: float = 0.0
    notes: str = ""
    tags: List[str] = field(default_factory=list)


class SemanticVersion:
    """Handles semantic versioning (major.minor.patch)."""
    
    def __init__(self, version_str: str = "1.0.0"):
        """Initialize semantic version from string.

        Args:
            version_str (str, optional): Version string in format major.minor.patch. Defaults to "1.0.0".
        """
        parts = version_str.split(".")
        self.major = int(parts[0]) if len(parts) > 0 else 1
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def bump_major(self) -> "SemanticVersion":
        """Increment major version (breaking changes)."""
        return SemanticVersion(f"{self.major + 1}.0.0")
    
    def bump_minor(self) -> "SemanticVersion":
        """Increment minor version (new features)."""
        return SemanticVersion(f"{self.major}.{self.minor + 1}.0")
    
    def bump_patch(self) -> "SemanticVersion":
        """Increment patch version (bug fixes)."""
        return SemanticVersion(f"{self.major}.{self.minor}.{self.patch + 1}")
    
    def __lt__(self, other: "SemanticVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return False
        return str(self) == str(other)


class ModelRegistry:
    """
    Central registry for managing versioned ML models.
    
    Features:
    - Store and retrieve model versions
    - Track metadata and lineage
    - Support for production model promotion
    - Model comparison and rollback
    """
    
    def __init__(self, registry_path: str = None):
        """Initialize the model registry.

        Args:
            registry_path (str, optional): Path to registry directory. If None, uses default.
        """
        self.registry_path = Path(registry_path or os.path.join(MODELS_DIR, "registry"))
        self.models_path = self.registry_path / "models"
        self.metadata_file = self.registry_path / "registry.json"
        
        # Create directories
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize registry
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry from disk."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "models": {},
            "production_model": None,
            "staging_model": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _save_registry(self):
        """Save registry to disk."""
        self.registry["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, default=str)
    
    def _compute_file_hash(self, filepath: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _get_next_version(self, model_name: str, bump_type: str = "patch") -> str:
        """Get the next version for a model."""
        if model_name not in self.registry["models"]:
            return "1.0.0"
        
        versions = self.registry["models"][model_name]["versions"]
        if not versions:
            return "1.0.0"
        
        # Get latest version
        latest = max(versions.keys(), key=lambda v: SemanticVersion(v))
        current = SemanticVersion(latest)
        
        if bump_type == "major":
            return str(current.bump_major())
        elif bump_type == "minor":
            return str(current.bump_minor())
        else:
            return str(current.bump_patch())
    
    def register_model(
        self,
        model: Any,
        name: str,
        description: str = "",
        model_type: str = "classifier",
        framework: str = "sklearn",
        metrics: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        feature_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        bump_type: str = "patch",
        scaler: Any = None,
        additional_artifacts: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> ModelMetadata:
        """Register a new model version.

        Args:
            model (Any): The trained model object.
            name (str): Model name (e.g., 'soulsense_predictor').
            description (str, optional): Description of the model. Defaults to "".
            model_type (str, optional): Type of model. Defaults to "classifier".
            framework (str, optional): ML framework used. Defaults to "sklearn".
            metrics (Optional[Dict[str, float]], optional): Performance metrics. Defaults to None.
            parameters (Optional[Dict[str, Any]], optional): Model hyperparameters. Defaults to None.
            feature_names (Optional[List[str]], optional): List of feature names. Defaults to None.
            class_names (Optional[List[str]], optional): List of class names. Defaults to None.
            tags (Optional[List[str]], optional): List of tags. Defaults to None.
            bump_type (str, optional): Version bump type. Defaults to "patch".
            scaler (Any, optional): Optional scaler object. Defaults to None.
            additional_artifacts (Optional[Dict[str, Any]], optional): Additional objects to save. Defaults to None.
            notes (str, optional): Additional notes. Defaults to "".

        Returns:
            ModelMetadata: Metadata for the registered model.
        """
        # Initialize model entry if needed
        if name not in self.registry["models"]:
            self.registry["models"][name] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "versions": {}
            }
        
        # Generate version
        version = self._get_next_version(name, bump_type)
        model_id = f"{name}_v{version}_{uuid.uuid4().hex[:8]}"
        
        # Create model directory
        model_dir = self.models_path / name / version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model artifacts
        model_data = {
            "model": model,
            "scaler": scaler,
            "feature_names": feature_names or [],
            "class_names": class_names or [],
            **(additional_artifacts or {})
        }
        
        model_file = model_dir / "model.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Compute file hash and size
        file_hash = self._compute_file_hash(model_file)
        file_size = model_file.stat().st_size
        
        # Get parent version
        versions = list(self.registry["models"][name]["versions"].keys())
        parent_version = max(versions, key=lambda v: SemanticVersion(v)) if versions else None
        
        # Create metadata
        metadata = ModelMetadata(
            model_id=model_id,
            version=version,
            name=name,
            description=description,
            created_at=datetime.now(timezone.utc).isoformat(),
            model_type=model_type,
            framework=framework,
            metrics=metrics or {},
            parameters=parameters or {},
            feature_names=feature_names or [],
            class_names=class_names or [],
            tags=tags or [],
            parent_version=parent_version,
            file_hash=file_hash,
            file_size_bytes=file_size,
            notes=notes
        )
        
        # Save metadata
        metadata_file = model_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(metadata), f, indent=2)
        
        # Update registry
        self.registry["models"][name]["versions"][version] = asdict(metadata)
        self._save_registry()
        
        logger.info(f"✅ Registered model: {name} v{version} (ID: {model_id})")
        return metadata
    
    def get_model(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Tuple[Any, ModelMetadata]:
        """Load a model by name and version.

        Args:
            name (str): Model name.
            version (Optional[str], optional): Version string. Defaults to latest.

        Returns:
            Tuple[Any, ModelMetadata]: Tuple of (model_data, metadata).
        """
        if name not in self.registry["models"]:
            raise ValueError(f"Model '{name}' not found in registry")
        
        versions = self.registry["models"][name]["versions"]
        if not versions:
            raise ValueError(f"No versions found for model '{name}'")
        
        # Get version
        if version is None:
            version = max(versions.keys(), key=lambda v: SemanticVersion(v))
        
        if version not in versions:
            raise ValueError(f"Version '{version}' not found for model '{name}'")
        
        # Load model
        model_dir = self.models_path / name / version
        model_file = model_dir / "model.pkl"
        
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
        
        # Load metadata
        metadata_dict = versions[version]
        metadata = ModelMetadata(**metadata_dict)
        
        logger.info(f"✅ Loaded model: {name} v{version}")
        return model_data, metadata

    # Backwards-compatible alias for older callers
    def load_model(self, name: str, version: Optional[str] = None) -> Tuple[Any, ModelMetadata]:
        """Alias for get_model to preserve backward compatibility.

        Args:
            name (str): Model name.
            version (Optional[str], optional): Version string. Defaults to latest.

        Returns:
            Tuple[Any, ModelMetadata]: Tuple of (model_data, metadata).
        """
        return self.get_model(name, version)
    
    def get_production_model(self, name: str) -> Optional[Tuple[Any, ModelMetadata]]:
        """Get the production model for a given name.

        Args:
            name (str): Model name.

        Returns:
            Optional[Tuple[Any, ModelMetadata]]: Production model data and metadata, or None.
        """
        if name not in self.registry["models"]:
            return None
        
        versions = self.registry["models"][name]["versions"]
        for version, metadata in versions.items():
            if metadata.get("is_production", False):
                return self.get_model(name, version)
        
        return None

    def has_active_run(self) -> bool:
        """Return True if there is an active experiment run.

        Returns:
            bool: True if there is an active experiment, False otherwise.
        """
        return bool(self._current_experiment)
    
    def promote_to_production(self, name: str, version: str) -> bool:
        """Promote a model version to production.

        Args:
            name (str): Model name.
            version (str): Version to promote.

        Returns:
            bool: True if promotion successful.
        """
        if name not in self.registry["models"]:
            raise ValueError(f"Model '{name}' not found")
        
        versions = self.registry["models"][name]["versions"]
        if version not in versions:
            raise ValueError(f"Version '{version}' not found")
        
        # Demote current production model
        for v, meta in versions.items():
            meta["is_production"] = False
        
        # Promote new version
        versions[version]["is_production"] = True
        self.registry["production_model"] = f"{name}:{version}"
        self._save_registry()
        
        logger.info(f"🚀 Promoted {name} v{version} to production")
        return True
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models.

        Returns:
            List[Dict[str, Any]]: List of model information dictionaries.
        """
        models_list = []
        for name, info in self.registry["models"].items():
            latest_version = max(info["versions"].keys(), key=lambda v: SemanticVersion(v)) if info["versions"] else None
            models_list.append({
                "name": name,
                "latest_version": latest_version,
                "version_count": len(info["versions"]),
                "created_at": info["created_at"]
            })
        return models_list
    
    def list_versions(self, name: str) -> List[Dict[str, Any]]:
        """List all versions of a model.

        Args:
            name (str): Model name.

        Returns:
            List[Dict[str, Any]]: List of version information dictionaries.
        """
        if name not in self.registry["models"]:
            return []
        
        versions = []
        for version, metadata in self.registry["models"][name]["versions"].items():
            versions.append({
                "version": version,
                "created_at": metadata["created_at"],
                "is_production": metadata.get("is_production", False),
                "metrics": metadata.get("metrics", {})
            })
        
        # Sort by version
        versions.sort(key=lambda x: SemanticVersion(x["version"]), reverse=True)
        return versions
    
    def compare_versions(
        self,
        name: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """Compare two versions of a model.

        Args:
            name (str): Model name.
            version1 (str): First version to compare.
            version2 (str): Second version to compare.

        Returns:
            Dict[str, Any]: Comparison results including metrics and parameters.
        """
        if name not in self.registry["models"]:
            raise ValueError(f"Model '{name}' not found")
        
        versions = self.registry["models"][name]["versions"]
        
        if version1 not in versions or version2 not in versions:
            raise ValueError("One or both versions not found")
        
        meta1 = versions[version1]
        meta2 = versions[version2]
        
        # Compare metrics
        metrics_comparison = {}
        all_metrics = set(meta1.get("metrics", {}).keys()) | set(meta2.get("metrics", {}).keys())
        
        for metric in all_metrics:
            val1 = meta1.get("metrics", {}).get(metric)
            val2 = meta2.get("metrics", {}).get(metric)
            
            if val1 is not None and val2 is not None:
                diff = val2 - val1
                metrics_comparison[metric] = {
                    "v1": val1,
                    "v2": val2,
                    "diff": diff,
                    "improved": diff > 0
                }
        
        return {
            "version1": version1,
            "version2": version2,
            "metrics_comparison": metrics_comparison,
            "parameters_diff": {
                "v1": meta1.get("parameters", {}),
                "v2": meta2.get("parameters", {})
            }
        }
    
    def rollback(self, name: str, target_version: str) -> bool:
        """Rollback to a previous version by promoting it to production.

        Args:
            name (str): Model name.
            target_version (str): Version to rollback to.

        Returns:
            bool: True if rollback successful.
        """
        return self.promote_to_production(name, target_version)
    
    def delete_version(self, name: str, version: str, force: bool = False) -> bool:
        """Delete a specific version.

        Args:
            name (str): Model name.
            version (str): Version to delete.
            force (bool, optional): Force deletion even if production. Defaults to False.

        Returns:
            bool: True if deletion successful.
        """
        if name not in self.registry["models"]:
            raise ValueError(f"Model '{name}' not found")
        
        versions = self.registry["models"][name]["versions"]
        if version not in versions:
            raise ValueError(f"Version '{version}' not found")
        
        metadata = versions[version]
        if metadata.get("is_production", False) and not force:
            raise ValueError("Cannot delete production model. Use force=True or promote another version first.")
        
        # Remove model files
        model_dir = self.models_path / name / version
        if model_dir.exists():
            shutil.rmtree(model_dir)
        
        # Update registry
        del versions[version]
        self._save_registry()
        
        logger.info(f"🗑️ Deleted model: {name} v{version}")
        return True


class ExperimentTracker:
    """
    Track ML experiments with metrics, parameters, and artifacts.
    
    Features:
    - Log experiments with full metadata
    - Compare experiments
    - Track experiment lineage
    - Generate reports
    """
    
    def __init__(self, experiments_path: str = None):
        self.experiments_path = Path(experiments_path or os.path.join(DATA_DIR, "experiments"))
        self.experiments_path.mkdir(parents=True, exist_ok=True)
        self.experiments_file = self.experiments_path / "experiments.json"
        self.experiments = self._load_experiments()
    
    def _load_experiments(self) -> Dict[str, Any]:
        """Load experiments from disk."""
        if self.experiments_file.exists():
            with open(self.experiments_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "experiments": {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _save_experiments(self):
        """Save experiments to disk."""
        with open(self.experiments_file, 'w', encoding='utf-8') as f:
            json.dump(self.experiments, f, indent=2, default=str)
    
    def start_experiment(
        self,
        name: str,
        description: str = "",
        hyperparameters: Optional[Dict[str, Any]] = None,
        dataset_info: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Start a new experiment.
        
        Returns:
            Experiment ID
        """
        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        
        experiment = ExperimentRecord(
            experiment_id=experiment_id,
            name=name,
            description=description,
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_version="",
            dataset_info=dataset_info or {},
            hyperparameters=hyperparameters or {},
            metrics={},
            artifacts=[],
            status="running",
            tags=tags or []
        )
        
        # Create experiment directory
        exp_dir = self.experiments_path / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save experiment
        self.experiments["experiments"][experiment_id] = asdict(experiment)
        self._save_experiments()
        
        logger.info(f"🧪 Started experiment: {name} (ID: {experiment_id})")
        return experiment_id
    
    def log_metrics(
        self,
        experiment_id: str,
        metrics: Dict[str, float]
    ):
        """Log metrics for an experiment."""
        if experiment_id not in self.experiments["experiments"]:
            raise ValueError(f"Experiment '{experiment_id}' not found")
        
        self.experiments["experiments"][experiment_id]["metrics"].update(metrics)
        self._save_experiments()
        
        logger.info(f"📊 Logged metrics for experiment {experiment_id}: {metrics}")
    
    def log_artifact(
        self,
        experiment_id: str,
        artifact_name: str,
        artifact_data: Any
    ):
        """Save an artifact for an experiment."""
        if experiment_id not in self.experiments["experiments"]:
            raise ValueError(f"Experiment '{experiment_id}' not found")
        
        exp_dir = self.experiments_path / experiment_id
        artifact_path = exp_dir / artifact_name
        
        # Save artifact based on type
        if isinstance(artifact_data, (dict, list)):
            with open(f"{artifact_path}.json", 'w', encoding='utf-8') as f:
                json.dump(artifact_data, f, indent=2)
            artifact_file = f"{artifact_name}.json"
        elif isinstance(artifact_data, str):
            with open(f"{artifact_path}.txt", 'w', encoding='utf-8') as f:
                f.write(artifact_data)
            artifact_file = f"{artifact_name}.txt"
        else:
            with open(f"{artifact_path}.pkl", 'wb') as f:
                pickle.dump(artifact_data, f)
            artifact_file = f"{artifact_name}.pkl"
        
        self.experiments["experiments"][experiment_id]["artifacts"].append(artifact_file)
        self._save_experiments()
        
        logger.info(f"📦 Saved artifact: {artifact_file}")
    
    def complete_experiment(
        self,
        experiment_id: str,
        model_version: str = "",
        duration_seconds: float = 0.0,
        notes: str = ""
    ):
        """Mark an experiment as completed."""
        if experiment_id not in self.experiments["experiments"]:
            raise ValueError(f"Experiment '{experiment_id}' not found")
        
        exp = self.experiments["experiments"][experiment_id]
        exp["status"] = "completed"
        exp["model_version"] = model_version
        exp["duration_seconds"] = duration_seconds
        exp["notes"] = notes
        
        self._save_experiments()
        logger.info(f"✅ Completed experiment: {experiment_id}")
    
    def fail_experiment(
        self,
        experiment_id: str,
        error_message: str = ""
    ):
        """Mark an experiment as failed."""
        if experiment_id not in self.experiments["experiments"]:
            raise ValueError(f"Experiment '{experiment_id}' not found")
        
        exp = self.experiments["experiments"][experiment_id]
        exp["status"] = "failed"
        exp["notes"] = f"Failed: {error_message}"
        
        self._save_experiments()
        logger.info(f"❌ Failed experiment: {experiment_id}")
    
    def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        """Get an experiment by ID."""
        if experiment_id not in self.experiments["experiments"]:
            return None
        
        exp_dict = self.experiments["experiments"][experiment_id]
        return ExperimentRecord(**exp_dict)
    
    def list_experiments(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filtering."""
        experiments_list = []
        
        for exp_id, exp in self.experiments["experiments"].items():
            # Filter by status
            if status and exp["status"] != status:
                continue
            
            # Filter by tags
            if tags and not any(tag in exp.get("tags", []) for tag in tags):
                continue
            
            experiments_list.append({
                "experiment_id": exp_id,
                "name": exp["name"],
                "status": exp["status"],
                "timestamp": exp["timestamp"],
                "metrics": exp.get("metrics", {}),
                "tags": exp.get("tags", [])
            })
        
        # Sort by timestamp (newest first)
        experiments_list.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return experiments_list[:limit]
    
    def compare_experiments(
        self,
        experiment_ids: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple experiments."""
        comparison = {
            "experiments": [],
            "metrics_comparison": {}
        }
        
        all_metrics = set()
        
        for exp_id in experiment_ids:
            exp = self.experiments["experiments"].get(exp_id)
            if exp:
                comparison["experiments"].append({
                    "id": exp_id,
                    "name": exp["name"],
                    "hyperparameters": exp.get("hyperparameters", {}),
                    "metrics": exp.get("metrics", {})
                })
                all_metrics.update(exp.get("metrics", {}).keys())
        
        # Build metrics comparison table
        for metric in all_metrics:
            comparison["metrics_comparison"][metric] = {
                exp["id"]: exp["metrics"].get(metric)
                for exp in comparison["experiments"]
            }
        
        return comparison
    
    def get_best_experiment(
        self,
        metric: str,
        maximize: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get the best experiment based on a metric."""
        best_exp = None
        best_value = float('-inf') if maximize else float('inf')
        
        for exp_id, exp in self.experiments["experiments"].items():
            if exp["status"] != "completed":
                continue
            
            value = exp.get("metrics", {}).get(metric)
            if value is None:
                continue
            
            if (maximize and value > best_value) or (not maximize and value < best_value):
                best_value = value
                best_exp = {
                    "experiment_id": exp_id,
                    **exp
                }
        
        return best_exp
    
    def generate_report(self, experiment_id: str) -> str:
        """Generate a detailed report for an experiment."""
        exp = self.experiments["experiments"].get(experiment_id)
        if not exp:
            return f"Experiment {experiment_id} not found"
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                    EXPERIMENT REPORT                          ║
╠══════════════════════════════════════════════════════════════╣
║ ID: {exp['experiment_id']:<54} ║
║ Name: {exp['name']:<52} ║
║ Status: {exp['status']:<50} ║
║ Timestamp: {exp['timestamp']:<47} ║
╠══════════════════════════════════════════════════════════════╣
║                    HYPERPARAMETERS                            ║
╠══════════════════════════════════════════════════════════════╣
"""
        for key, value in exp.get('hyperparameters', {}).items():
            report += f"║ {key}: {str(value):<52} ║\n"
        
        report += """╠══════════════════════════════════════════════════════════════╣
║                       METRICS                                 ║
╠══════════════════════════════════════════════════════════════╣
"""
        for key, value in exp.get('metrics', {}).items():
            if isinstance(value, float):
                report += f"║ {key}: {value:<52.4f} ║\n"
            else:
                report += f"║ {key}: {str(value):<52} ║\n"
        
        report += """╠══════════════════════════════════════════════════════════════╣
║                      ARTIFACTS                                ║
╠══════════════════════════════════════════════════════════════╣
"""
        for artifact in exp.get('artifacts', []):
            report += f"║ • {artifact:<56} ║\n"
        
        report += """╚══════════════════════════════════════════════════════════════╝
"""
        
        if exp.get('notes'):
            report += f"\nNotes: {exp['notes']}\n"
        
        return report


class ModelVersioningManager:
    """
    High-level manager combining model registry and experiment tracking.
    
    Provides a unified interface for:
    - Running versioned experiments
    - Registering models from experiments
    - Managing the ML lifecycle
    """
    
    def __init__(
        self,
        registry_path: str = None,
        experiments_path: str = None
    ):
        """Initialize the model versioning manager.

        Args:
            registry_path (str, optional): Path to model registry. Defaults to None.
            experiments_path (str, optional): Path to experiments. Defaults to None.
        """
        self.registry = ModelRegistry(registry_path)
        self.tracker = ExperimentTracker(experiments_path)
        self._current_experiment: Optional[str] = None
        self._experiment_start_time: Optional[datetime] = None
    
    def start_run(
        self,
        name: str,
        description: str = "",
        hyperparameters: Optional[Dict[str, Any]] = None,
        dataset_info: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Start a new training run (experiment).

        Args:
            name (str): Experiment name.
            description (str, optional): Experiment description. Defaults to "".
            hyperparameters (Optional[Dict[str, Any]], optional): Model hyperparameters. Defaults to None.
            dataset_info (Optional[Dict[str, Any]], optional): Dataset information. Defaults to None.
            tags (Optional[List[str]], optional): Experiment tags. Defaults to None.

        Returns:
            str: Experiment ID.
        """
        self._current_experiment = self.tracker.start_experiment(
            name=name,
            description=description,
            hyperparameters=hyperparameters,
            dataset_info=dataset_info,
            tags=tags
        )
        self._experiment_start_time = datetime.now(timezone.utc)
        return self._current_experiment
    
    def log_metrics(self, metrics: Dict[str, float]):
        """Log metrics for the current run.

        Args:
            metrics (Dict[str, float]): Metrics to log.

        Raises:
            ValueError: If no active experiment.
        """
        if not self._current_experiment:
            raise ValueError("No active experiment. Call start_run() first.")
        self.tracker.log_metrics(self._current_experiment, metrics)
    
    def log_artifact(self, name: str, data: Any):
        """Log an artifact for the current run.

        Args:
            name (str): Artifact name.
            data (Any): Artifact data.

        Raises:
            ValueError: If no active experiment.
        """
        if not self._current_experiment:
            raise ValueError("No active experiment. Call start_run() first.")
        self.tracker.log_artifact(self._current_experiment, name, data)
    
    def end_run(
        self,
        model: Any = None,
        model_name: str = "",
        scaler: Any = None,
        feature_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        bump_type: str = "patch",
        notes: str = ""
    ) -> Optional[ModelMetadata]:
        """End the current run and optionally register the model.

        Args:
            model (Any, optional): Model to register. Defaults to None.
            model_name (str, optional): Name for the registered model. Defaults to "".
            scaler (Any, optional): Scaler to save with model. Defaults to None.
            feature_names (Optional[List[str]], optional): Feature names. Defaults to None.
            class_names (Optional[List[str]], optional): Class names. Defaults to None.
            bump_type (str, optional): Version bump type. Defaults to "patch".
            notes (str, optional): Additional notes. Defaults to "".

        Returns:
            Optional[ModelMetadata]: Model metadata if model was registered, None otherwise.

        Raises:
            ValueError: If no active experiment.
        """
        if not self._current_experiment:
            raise ValueError("No active experiment.")
        
        duration = 0.0
        if self._experiment_start_time:
            duration = (datetime.now(timezone.utc) - self._experiment_start_time).total_seconds()
        
        model_version = ""
        metadata = None
        
        # Register model if provided
        if model is not None and model_name:
            exp = self.tracker.get_experiment(self._current_experiment)
            
            metadata = self.registry.register_model(
                model=model,
                name=model_name,
                description=exp.description if exp else "",
                metrics=exp.metrics if exp else {},
                parameters=exp.hyperparameters if exp else {},
                feature_names=feature_names,
                class_names=class_names,
                scaler=scaler,
                bump_type=bump_type,
                notes=notes
            )
            model_version = metadata.version
        
        # Complete experiment
        self.tracker.complete_experiment(
            self._current_experiment,
            model_version=model_version,
            duration_seconds=duration,
            notes=notes
        )
        
        # Reset state
        self._current_experiment = None
        self._experiment_start_time = None
        
        return metadata
    
    def fail_run(self, error_message: str = ""):
        """Mark the current run as failed.

        Args:
            error_message (str, optional): Error message. Defaults to "".
        """
        if not self._current_experiment:
            return
        
        self.tracker.fail_experiment(self._current_experiment, error_message)
        self._current_experiment = None
        self._experiment_start_time = None
    
    def get_production_model(self, name: str) -> Optional[Tuple[Any, ModelMetadata]]:
        """Get the production model.

        Args:
            name (str): Model name.

        Returns:
            Optional[Tuple[Any, ModelMetadata]]: Production model data and metadata.
        """
        return self.registry.get_production_model(name)
    
    def promote_model(self, name: str, version: str):
        """Promote a model to production.

        Args:
            name (str): Model name.
            version (str): Version to promote.
        """
        return self.registry.promote_to_production(name, version)
    
    def generate_summary(self) -> str:
        """Generate a summary of all models and experiments.

        Returns:
            str: Formatted summary string.
        """
        summary = """
╔══════════════════════════════════════════════════════════════╗
║              MODEL VERSIONING SYSTEM SUMMARY                  ║
╚══════════════════════════════════════════════════════════════╝

📦 REGISTERED MODELS
────────────────────
"""
        models = self.registry.list_models()
        if models:
            for model in models:
                summary += f"  • {model['name']} (v{model['latest_version']}) - {model['version_count']} versions\n"
        else:
            summary += "  No models registered yet.\n"
        
        summary += """
🧪 RECENT EXPERIMENTS
─────────────────────
"""
        experiments = self.tracker.list_experiments(limit=10)
        if experiments:
            for exp in experiments:
                status_icon = {"completed": "✅", "running": "🔄", "failed": "❌"}.get(exp['status'], "❓")
                summary += f"  {status_icon} {exp['name']} ({exp['experiment_id'][:12]}...)\n"
                if exp.get('metrics'):
                    metrics_str = ", ".join(f"{k}: {v:.4f}" for k, v in list(exp['metrics'].items())[:3])
                    summary += f"     └─ {metrics_str}\n"
        else:
            summary += "  No experiments recorded yet.\n"
        
        return summary


# Convenience function for quick versioning
def create_versioning_manager(
    registry_path: str = "models/registry",
    experiments_path: str = "experiments"
) -> ModelVersioningManager:
    """Create a ModelVersioningManager instance.

    Args:
        registry_path (str, optional): Path to model registry. Defaults to "models/registry".
        experiments_path (str, optional): Path to experiments. Defaults to "experiments".

    Returns:
        ModelVersioningManager: Initialized manager instance.
    """
    return ModelVersioningManager(registry_path, experiments_path)


# Example usage and test
if __name__ == "__main__":
    print("🧪 Testing Model Versioning System...")
    
    # Create manager
    manager = create_versioning_manager()
    
    # Start experiment
    exp_id = manager.start_run(
        name="test_experiment",
        description="Testing the versioning system",
        hyperparameters={
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.01
        },
        dataset_info={
            "samples": 1000,
            "features": 8
        },
        tags=["test", "demo"]
    )
    
    # Log metrics
    manager.log_metrics({
        "accuracy": 0.85,
        "f1_score": 0.82,
        "precision": 0.84,
        "recall": 0.80
    })
    
    # Log artifact
    manager.log_artifact("config", {
        "model_type": "RandomForest",
        "random_state": 42
    })
    
    # End run (without registering a model for this test)
    manager.end_run(notes="Test run completed successfully")
    
    # Print summary
    print(manager.generate_summary())
    
    print("\n✅ Model versioning system test completed!")
