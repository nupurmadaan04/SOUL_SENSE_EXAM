"""
Tests for the feature flags module.

Tests cover:
- FeatureFlag dataclass validation
- FeatureFlagManager defaults and lookups
- Environment variable overrides
- Config file integration
- Decorators (@feature_gated, @require_feature)
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from app.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    EXPERIMENTAL_FLAGS,
    feature_gated,
    require_feature,
)


class TestFeatureFlag:
    """Test FeatureFlag dataclass."""
    
    def test_basic_flag_creation(self):
        """Test creating a basic feature flag."""
        flag = FeatureFlag(
            name="test_feature",
            default=False,
            description="A test feature"
        )
        assert flag.name == "test_feature"
        assert flag.default is False
        assert flag.description == "A test feature"
        assert flag.experimental is True  # Default
        assert flag.category == "general"  # Default
    
    def test_flag_name_normalized_to_lowercase(self):
        """Test that flag names are normalized to lowercase."""
        flag = FeatureFlag(name="TEST_FEATURE")
        assert flag.name == "test_feature"
    
    def test_invalid_flag_name_raises_error(self):
        """Test that invalid flag names raise ValueError."""
        with pytest.raises(ValueError, match="Invalid flag name"):
            FeatureFlag(name="test-feature")  # Hyphens not allowed
    
    def test_flag_with_all_attributes(self):
        """Test creating a flag with all attributes."""
        flag = FeatureFlag(
            name="full_feature",
            default=True,
            description="Full feature",
            experimental=False,
            category="ui"
        )
        assert flag.name == "full_feature"
        assert flag.default is True
        assert flag.experimental is False
        assert flag.category == "ui"


class TestFeatureFlagManager:
    """Test FeatureFlagManager class."""
    
    @pytest.fixture
    def clean_env(self, monkeypatch):
        """Remove any SOULSENSE_FF_ environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("SOULSENSE_FF_"):
                monkeypatch.delenv(key, raising=False)
    
    @pytest.fixture
    def manager(self, clean_env):
        """Create a fresh FeatureFlagManager with empty config."""
        return FeatureFlagManager(config_data={})
    
    def test_default_flags_registered(self, manager):
        """Test that default experimental flags are registered."""
        flags = manager.get_all_flags()
        assert "ai_journal_suggestions" in flags
        assert "advanced_analytics" in flags
        assert "beta_ui_components" in flags
    
    def test_is_enabled_returns_default_when_not_configured(self, manager):
        """Test that is_enabled returns default value."""
        # All experimental flags default to False
        assert manager.is_enabled("ai_journal_suggestions") is False
        assert manager.is_enabled("advanced_analytics") is False
    
    def test_is_disabled_convenience_method(self, manager):
        """Test is_disabled convenience method."""
        assert manager.is_disabled("ai_journal_suggestions") is True
    
    def test_unknown_flag_returns_false(self, manager):
        """Test that unknown flags return False."""
        assert manager.is_enabled("nonexistent_flag") is False
    
    def test_config_file_values_applied(self, clean_env):
        """Test that config file values are applied."""
        config_data = {
            "experimental": {
                "ai_journal_suggestions": True,
                "advanced_analytics": True
            }
        }
        manager = FeatureFlagManager(config_data=config_data)
        
        assert manager.is_enabled("ai_journal_suggestions") is True
        assert manager.is_enabled("advanced_analytics") is True
        assert manager.is_enabled("beta_ui_components") is False  # Still default
    
    def test_env_var_overrides_config(self, monkeypatch):
        """Test that environment variables override config file."""
        config_data = {
            "experimental": {
                "ai_journal_suggestions": False
            }
        }
        
        # Set env var to True
        monkeypatch.setenv("SOULSENSE_FF_AI_JOURNAL_SUGGESTIONS", "true")
        
        manager = FeatureFlagManager(config_data=config_data)
        
        # Env var should win
        assert manager.is_enabled("ai_journal_suggestions") is True
    
    def test_env_var_case_insensitive_values(self, monkeypatch):
        """Test various truthy env var values."""
        test_cases = [
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
        ]
        
        for value, expected in test_cases:
            monkeypatch.setenv("SOULSENSE_FF_AI_JOURNAL_SUGGESTIONS", value)
            manager = FeatureFlagManager(config_data={})
            assert manager.is_enabled("ai_journal_suggestions") is expected, \
                f"Failed for value: {value}"
    
    def test_get_flag_returns_flag_object(self, manager):
        """Test get_flag returns FeatureFlag object."""
        flag = manager.get_flag("ai_journal_suggestions")
        assert flag is not None
        assert isinstance(flag, FeatureFlag)
        assert flag.name == "ai_journal_suggestions"
    
    def test_get_flag_returns_none_for_unknown(self, manager):
        """Test get_flag returns None for unknown flags."""
        assert manager.get_flag("unknown_flag") is None
    
    def test_get_enabled_flags(self, clean_env):
        """Test get_enabled_flags returns only enabled flags."""
        config_data = {
            "experimental": {
                "ai_journal_suggestions": True,
            }
        }
        manager = FeatureFlagManager(config_data=config_data)
        
        enabled = manager.get_enabled_flags()
        assert "ai_journal_suggestions" in enabled
        assert "advanced_analytics" not in enabled
    
    def test_get_flags_by_category(self, manager):
        """Test get_flags_by_category filters correctly."""
        ai_flags = manager.get_flags_by_category("ai")
        assert "ai_journal_suggestions" in ai_flags
        assert "ml_emotion_detection" in ai_flags
        assert "beta_ui_components" not in ai_flags
    
    def test_register_flag(self, manager):
        """Test registering a new flag at runtime."""
        new_flag = FeatureFlag(
            name="custom_feature",
            default=True,
            description="Custom feature"
        )
        manager.register_flag(new_flag)
        
        assert manager.is_enabled("custom_feature") is True
        assert manager.get_flag("custom_feature") == new_flag
    
    def test_set_and_clear_override(self, manager):
        """Test runtime override functionality."""
        # Default is False
        assert manager.is_enabled("ai_journal_suggestions") is False
        
        # Set override
        manager.set_override("ai_journal_suggestions", True)
        assert manager.is_enabled("ai_journal_suggestions") is True
        
        # Clear override
        manager.clear_override("ai_journal_suggestions")
        assert manager.is_enabled("ai_journal_suggestions") is False
    
    def test_clear_all_overrides(self, manager):
        """Test clearing all runtime overrides."""
        manager.set_override("ai_journal_suggestions", True)
        manager.set_override("advanced_analytics", True)
        
        manager.clear_all_overrides()
        
        assert manager.is_enabled("ai_journal_suggestions") is False
        assert manager.is_enabled("advanced_analytics") is False
    
    def test_get_flag_status(self, clean_env):
        """Test get_flag_status returns detailed info."""
        config_data = {
            "experimental": {
                "ai_journal_suggestions": True
            }
        }
        manager = FeatureFlagManager(config_data=config_data)
        
        status = manager.get_flag_status()
        
        assert "ai_journal_suggestions" in status
        ai_status = status["ai_journal_suggestions"]
        assert ai_status["enabled"] is True
        assert ai_status["source"] == "config"
        assert ai_status["default"] is False
        assert "description" in ai_status


class TestDecorators:
    """Test feature flag decorators."""
    
    @pytest.fixture
    def mock_manager(self, monkeypatch):
        """Create a mock feature flags manager."""
        mock = MagicMock(spec=FeatureFlagManager)
        monkeypatch.setattr("app.feature_flags.feature_flags", mock)
        return mock
    
    def test_feature_gated_enabled(self, mock_manager):
        """Test @feature_gated runs function when flag is enabled."""
        mock_manager.is_enabled.return_value = True
        
        @feature_gated("test_flag")
        def my_function():
            return "executed"
        
        result = my_function()
        assert result == "executed"
        mock_manager.is_enabled.assert_called_with("test_flag")
    
    def test_feature_gated_disabled_returns_fallback(self, mock_manager):
        """Test @feature_gated returns fallback when flag is disabled."""
        mock_manager.is_enabled.return_value = False
        
        @feature_gated("test_flag", fallback="default_value")
        def my_function():
            return "executed"
        
        result = my_function()
        assert result == "default_value"
    
    def test_feature_gated_disabled_returns_none_by_default(self, mock_manager):
        """Test @feature_gated returns None by default when disabled."""
        mock_manager.is_enabled.return_value = False
        
        @feature_gated("test_flag")
        def my_function():
            return "executed"
        
        result = my_function()
        assert result is None
    
    def test_require_feature_enabled(self, mock_manager):
        """Test @require_feature runs function when flag is enabled."""
        mock_manager.is_enabled.return_value = True
        
        @require_feature("test_flag")
        def my_function():
            return "executed"
        
        result = my_function()
        assert result == "executed"
    
    def test_require_feature_disabled_raises(self, mock_manager):
        """Test @require_feature raises RuntimeError when flag is disabled."""
        mock_manager.is_enabled.return_value = False
        
        @require_feature("test_flag")
        def my_function():
            return "executed"
        
        with pytest.raises(RuntimeError, match="Feature 'test_flag' is not enabled"):
            my_function()
    
    def test_decorators_preserve_function_metadata(self, mock_manager):
        """Test that decorators preserve function name and docstring."""
        mock_manager.is_enabled.return_value = True
        
        @feature_gated("test_flag")
        def my_documented_function():
            """This is the docstring."""
            return "executed"
        
        assert my_documented_function.__name__ == "my_documented_function"
        assert "docstring" in my_documented_function.__doc__


class TestExperimentalFlags:
    """Test pre-defined experimental flags."""
    
    def test_all_flags_have_descriptions(self):
        """Test that all experimental flags have descriptions."""
        for name, flag in EXPERIMENTAL_FLAGS.items():
            assert flag.description, f"Flag {name} missing description"
    
    def test_all_flags_are_experimental_by_default(self):
        """Test that all flags are marked as experimental."""
        for name, flag in EXPERIMENTAL_FLAGS.items():
            assert flag.experimental is True, f"Flag {name} should be experimental"
    
    def test_all_flags_default_to_false(self):
        """Test that all experimental flags default to False (safe)."""
        for name, flag in EXPERIMENTAL_FLAGS.items():
            assert flag.default is False, f"Flag {name} should default to False"
    
    def test_expected_flags_exist(self):
        """Test that expected experimental flags are defined."""
        expected = [
            "ai_journal_suggestions",
            "advanced_analytics",
            "beta_ui_components",
            "ml_emotion_detection",
            "data_export_v2",
        ]
        for flag_name in expected:
            assert flag_name in EXPERIMENTAL_FLAGS, f"Missing flag: {flag_name}"
