"""
Feature Flags Module for SoulSense

This module provides a feature flag system for enabling/disabling experimental
features via configuration. Flags can be set via:
1. config.json (experimental section)
2. Environment variables (SOULSENSE_FF_* prefix)

Environment variables take precedence over config file settings.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, TypeVar
from functools import wraps

# Type variable for generic decorator
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class FeatureFlag:
    """
    Represents a single feature flag with metadata.
    
    Attributes:
        name: Unique identifier for the flag (lowercase, underscored)
        default: Default state when not configured (False for experimental)
        description: Human-readable description of what the flag controls
        experimental: Whether this is an experimental/beta feature
        category: Optional grouping category for UI display
    """
    name: str
    default: bool = False
    description: str = ""
    experimental: bool = True
    category: str = "general"
    
    def __post_init__(self) -> None:
        """Validate flag name format."""
        if not self.name.replace('_', '').isalnum():
            raise ValueError(f"Invalid flag name: {self.name}. Use lowercase alphanumeric with underscores.")
        self.name = self.name.lower()


# Pre-defined experimental feature flags
EXPERIMENTAL_FLAGS: Dict[str, FeatureFlag] = {
    "ai_journal_suggestions": FeatureFlag(
        name="ai_journal_suggestions",
        default=False,
        description="Enable AI-powered suggestions in the journal feature",
        experimental=True,
        category="ai"
    ),
    "advanced_analytics": FeatureFlag(
        name="advanced_analytics",
        default=False,
        description="Enable advanced analytics dashboard with predictive insights",
        experimental=True,
        category="analytics"
    ),
    "beta_ui_components": FeatureFlag(
        name="beta_ui_components",
        default=False,
        description="Enable beta UI components and experimental layouts",
        experimental=True,
        category="ui"
    ),
    "ml_emotion_detection": FeatureFlag(
        name="ml_emotion_detection",
        default=False,
        description="Enable ML-based emotion detection from text entries",
        experimental=True,
        category="ai"
    ),
    "data_export_v2": FeatureFlag(
        name="data_export_v2",
        default=False,
        description="Enable new data export formats (PDF, enhanced CSV)",
        experimental=True,
        category="data"
    ),
}


class FeatureFlagManager:
    """
    Centralized manager for feature flags.
    
    Supports configuration from:
    - Default values defined in EXPERIMENTAL_FLAGS
    - config.json experimental section
    - Environment variables (SOULSENSE_FF_* prefix, highest priority)
    
    Usage:
        from app.feature_flags import feature_flags
        
        if feature_flags.is_enabled("ai_journal_suggestions"):
            # AI suggestion code
            pass
    """
    
    _ENV_PREFIX = "SOULSENSE_FF_"
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the feature flag manager.
        
        Args:
            config_data: Optional config dict with 'experimental' key.
                         If None, will attempt to load from config.json.
        """
        self._flags: Dict[str, FeatureFlag] = EXPERIMENTAL_FLAGS.copy()
        self._overrides: Dict[str, bool] = {}
        self._config_values: Dict[str, bool] = {}
        self.logger = logging.getLogger(__name__)
        
        # Load config file values
        if config_data is not None:
            self._load_from_config(config_data)
        else:
            self._load_config_file()
        
        # Load environment variable overrides
        self._load_env_overrides()
    
    def _load_config_file(self) -> None:
        """Load experimental flags from config.json if available."""
        try:
            from app.config import BASE_DIR, CONFIG_PATH
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    config_data = json.load(f)
                    self._load_from_config(config_data)
        except Exception as e:
            self.logger.warning(f"Could not load feature flags from config: {e}")
    
    def _load_from_config(self, config_data: Dict[str, Any]) -> None:
        """Extract experimental flags from config dict."""
        experimental = config_data.get("experimental", {})
        for flag_name, enabled in experimental.items():
            if isinstance(enabled, bool):
                self._config_values[flag_name.lower()] = enabled
    
    def _load_env_overrides(self) -> None:
        """Load feature flag overrides from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(self._ENV_PREFIX):
                flag_name = key[len(self._ENV_PREFIX):].lower()
                self._overrides[flag_name] = value.lower() in ('true', '1', 'yes', 'on')
    
    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Priority (highest to lowest):
        1. Environment variable (SOULSENSE_FF_*)
        2. config.json experimental section
        3. Default value from flag definition
        
        Args:
            flag_name: Name of the flag to check
            
        Returns:
            True if the flag is enabled, False otherwise
        """
        flag_name = flag_name.lower()
        
        # Check environment override first (highest priority)
        if flag_name in self._overrides:
            return self._overrides[flag_name]
        
        # Check config file value
        if flag_name in self._config_values:
            return self._config_values[flag_name]
        
        # Check if flag exists and return default
        if flag_name in self._flags:
            return self._flags[flag_name].default
        
        # Unknown flag - log and return False
        self.logger.debug(f"Unknown feature flag requested: {flag_name}")
        return False
    
    def is_disabled(self, flag_name: str) -> bool:
        """Check if a feature flag is disabled (convenience method)."""
        return not self.is_enabled(flag_name)
    
    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get the FeatureFlag object for a given flag name."""
        return self._flags.get(flag_name.lower())
    
    def get_all_flags(self) -> Dict[str, FeatureFlag]:
        """Get all registered feature flags."""
        return self._flags.copy()
    
    def get_enabled_flags(self) -> Dict[str, FeatureFlag]:
        """Get all currently enabled feature flags."""
        return {
            name: flag for name, flag in self._flags.items()
            if self.is_enabled(name)
        }
    
    def get_flags_by_category(self, category: str) -> Dict[str, FeatureFlag]:
        """Get all feature flags in a specific category."""
        return {
            name: flag for name, flag in self._flags.items()
            if flag.category == category
        }
    
    def register_flag(self, flag: FeatureFlag) -> None:
        """
        Register a new feature flag at runtime.
        
        Args:
            flag: FeatureFlag instance to register
        """
        self._flags[flag.name] = flag
        self.logger.info(f"Registered feature flag: {flag.name}")
    
    def set_override(self, flag_name: str, enabled: bool) -> None:
        """
        Set a runtime override for a feature flag.
        
        This is useful for testing or admin interfaces.
        
        Args:
            flag_name: Name of the flag to override
            enabled: New state for the flag
        """
        self._overrides[flag_name.lower()] = enabled
    
    def clear_override(self, flag_name: str) -> None:
        """Clear a runtime override for a feature flag."""
        self._overrides.pop(flag_name.lower(), None)
    
    def clear_all_overrides(self) -> None:
        """Clear all runtime overrides."""
        self._overrides.clear()
    
    def get_flag_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed status of all feature flags.
        
        Returns a dict with flag info including current state and source.
        """
        status = {}
        for name, flag in self._flags.items():
            source = "default"
            if name in self._overrides:
                source = "environment" if name.upper() in os.environ else "runtime"
            elif name in self._config_values:
                source = "config"
            
            status[name] = {
                "enabled": self.is_enabled(name),
                "source": source,
                "default": flag.default,
                "description": flag.description,
                "experimental": flag.experimental,
                "category": flag.category,
            }
        return status


def feature_gated(flag_name: str, fallback: Any = None) -> Callable[[F], F]:
    """
    Decorator to gate a function behind a feature flag.
    
    If the flag is disabled, the function returns the fallback value
    without executing.
    
    Args:
        flag_name: Name of the feature flag to check
        fallback: Value to return if the flag is disabled (default: None)
    
    Usage:
        @feature_gated("ai_journal_suggestions")
        def get_ai_suggestions(text: str) -> List[str]:
            # This only runs if the flag is enabled
            return ai_model.suggest(text)
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if feature_flags.is_enabled(flag_name):
                return func(*args, **kwargs)
            return fallback
        return wrapper  # type: ignore
    return decorator


def require_feature(flag_name: str) -> Callable[[F], F]:
    """
    Decorator that raises an error if a feature flag is disabled.
    
    Use this for features that should fail loudly rather than silently.
    
    Args:
        flag_name: Name of the feature flag to check
    
    Raises:
        RuntimeError: If the feature flag is disabled
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not feature_flags.is_enabled(flag_name):
                raise RuntimeError(
                    f"Feature '{flag_name}' is not enabled. "
                    f"Enable it via SOULSENSE_FF_{flag_name.upper()}=true or in config.json"
                )
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


# Global feature flag manager instance
feature_flags = FeatureFlagManager()
