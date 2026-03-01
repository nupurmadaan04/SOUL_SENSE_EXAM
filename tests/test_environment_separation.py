"""Tests for environment data separation and hygiene.

This test suite ensures that analytics data from different environments
(development, staging, production) is strictly separated.

Issue: #979 - Environment & Data Hygiene Issues
"""
import pytest
import os
from datetime import datetime, UTC
from unittest.mock import Mock, patch, AsyncMock

# Import after path setup
import sys
sys.path.insert(0, '/Users/takku/Desktop/Elite hack/SOUL_SENSE_EXAM')

from backend.fastapi.api.utils.environment_context import (
    Environment,
    EnvironmentContext,
    get_current_environment,
    set_environment_context,
    is_production,
    is_staging,
    is_development,
    validate_environment_strictness,
    get_environment_prefix,
    _environment_context
)


class TestEnvironmentContext:
    """Tests for environment context management."""
    
    def test_environment_enum_values(self):
        """Test that Environment enum has correct values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"
    
    def test_get_current_environment_default(self):
        """Test that default environment is development."""
        # Clear any context
        _environment_context.set(None)
        
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            env = get_current_environment()
            assert env == "development"
    
    def test_get_current_environment_from_env_var(self):
        """Test reading environment from APP_ENV."""
        _environment_context.set(None)
        
        with patch.dict(os.environ, {"APP_ENV": "staging"}, clear=True):
            env = get_current_environment()
            assert env == "staging"
    
    def test_get_current_environment_from_soulsense_env(self):
        """Test reading environment from SOULSENSE_ENV."""
        _environment_context.set(None)
        
        with patch.dict(os.environ, {"SOULSENSE_ENV": "production"}, clear=True):
            env = get_current_environment()
            assert env == "production"
    
    def test_get_current_environment_priority(self):
        """Test that context variable takes priority over env vars."""
        set_environment_context("production")
        
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            env = get_current_environment()
            assert env == "production"
    
    def test_environment_context_manager(self):
        """Test EnvironmentContext context manager."""
        _environment_context.set(None)
        
        with EnvironmentContext("staging"):
            assert get_current_environment() == "staging"
        
        # After exiting context, should revert
        _environment_context.set(None)
        assert get_current_environment() == "development"
    
    def test_environment_context_manager_invalid(self):
        """Test that invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="Invalid environment"):
            with EnvironmentContext("invalid"):
                pass
    
    def test_set_environment_context(self):
        """Test setting environment context."""
        set_environment_context("staging")
        assert get_current_environment() == "staging"
        
        set_environment_context("production")
        assert get_current_environment() == "production"
    
    def test_set_environment_context_invalid(self):
        """Test that setting invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="Invalid environment"):
            set_environment_context("invalid_env")
    
    def test_is_production(self):
        """Test is_production check."""
        set_environment_context("production")
        assert is_production() is True
        assert is_staging() is False
        assert is_development() is False
    
    def test_is_staging(self):
        """Test is_staging check."""
        set_environment_context("staging")
        assert is_production() is False
        assert is_staging() is True
        assert is_development() is False
    
    def test_is_development(self):
        """Test is_development check."""
        set_environment_context("development")
        assert is_production() is False
        assert is_staging() is False
        assert is_development() is True
    
    def test_get_environment_prefix(self):
        """Test environment prefix generation."""
        set_environment_context("production")
        assert get_environment_prefix() == "prod"
        
        set_environment_context("staging")
        assert get_environment_prefix() == "staging"
        
        set_environment_context("development")
        assert get_environment_prefix() == "dev"
        
        set_environment_context("testing")
        assert get_environment_prefix() == "test"


class TestEnvironmentValidation:
    """Tests for environment validation."""
    
    def test_validate_environment_strictness_valid(self):
        """Test validation passes for valid configuration."""
        set_environment_context("development")
        
        with patch.dict(os.environ, {
            "DATABASE_URL": "sqlite:///./data/soulsense.db",
            "APP_ENV": "development"
        }, clear=True):
            result = validate_environment_strictness()
            
            assert result["is_valid"] is True
            assert result["environment"] == "development"
            assert result["separation_enabled"] is True
    
    def test_validate_environment_strictness_production_db_in_dev(self):
        """Test validation fails when using production database in dev."""
        set_environment_context("development")
        
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@prod-db.example.com/soulsense_production",
            "APP_ENV": "development"
        }, clear=True):
            result = validate_environment_strictness()
            
            assert result["is_valid"] is False
            assert len(result["errors"]) > 0
            assert "production database" in result["errors"][0].lower()
    
    def test_validate_environment_strictness_staging_warnings(self):
        """Test validation warnings for staging configuration."""
        set_environment_context("staging")
        
        with patch.dict(os.environ, {
            "DATABASE_URL": "sqlite:///./data/staging.db",
            "APP_ENV": "staging",
            "REDIS_DB": "0"
        }, clear=True):
            result = validate_environment_strictness()
            
            # Should have warning about Redis DB
            assert any("redis" in w.lower() for w in result["warnings"])


class TestAnalyticsServiceEnvironmentFiltering:
    """Tests for analytics service environment filtering."""
    
    def test_analytics_event_model_has_environment(self):
        """Test that AnalyticsEvent model has environment attribute."""
        from backend.fastapi.api.models import AnalyticsEvent
        
        set_environment_context("staging")
        
        # Create an event directly to verify environment is set
        event = AnalyticsEvent(
            anonymous_id='test-id',
            event_name='test_event',
            environment='staging'
        )
        
        assert event.environment == "staging"
    
    def test_analytics_service_file_includes_environment(self):
        """Test that analytics service file contains environment filtering."""
        import os
        
        service_path = "/Users/takku/Desktop/Elite hack/SOUL_SENSE_EXAM/backend/fastapi/api/services/analytics_service.py"
        with open(service_path, 'r') as f:
            content = f.read()
        
        # Check that the file includes environment parameter
        assert 'environment: Optional[str] = None' in content
        assert 'get_current_environment()' in content
        assert 'from ..utils.environment_context import get_current_environment' in content


class TestEnvironmentMiddleware:
    """Tests for environment middleware."""
    
    def test_middleware_file_exists(self):
        """Test that middleware file exists and has correct content."""
        import os
        
        middleware_path = "/Users/takku/Desktop/Elite hack/SOUL_SENSE_EXAM/backend/fastapi/api/middleware/environment_middleware.py"
        assert os.path.exists(middleware_path)
        
        with open(middleware_path, 'r') as f:
            content = f.read()
        
        # Verify key components exist
        assert 'EnvironmentMiddleware' in content
        assert 'EnvironmentValidationMiddleware' in content
        assert 'set_environment_context' in content
        assert 'get_current_environment' in content
        assert 'X-Environment' in content
    
    def test_middleware_file_structure(self):
        """Test that middleware file has proper structure."""
        middleware_path = "/Users/takku/Desktop/Elite hack/SOUL_SENSE_EXAM/backend/fastapi/api/middleware/environment_middleware.py"
        
        with open(middleware_path, 'r') as f:
            content = f.read()
        
        # Check for required imports
        assert 'from fastapi import Request, Response' in content
        assert 'from starlette.middleware.base import BaseHTTPMiddleware' in content
        
        # Check for class definitions
        assert 'class EnvironmentMiddleware(BaseHTTPMiddleware):' in content
        assert 'class EnvironmentValidationMiddleware(BaseHTTPMiddleware):' in content
        
        # Check for dispatch method
        assert 'async def dispatch(self, request: Request, call_next):' in content


class TestEnvironmentDataIsolation:
    """Integration tests for environment data isolation."""
    
    def test_analytics_event_model_has_environment_column(self):
        """Test that AnalyticsEvent model has environment column."""
        from backend.fastapi.api.models import AnalyticsEvent
        
        # Check that the model has the environment attribute
        assert hasattr(AnalyticsEvent, 'environment')
        
        # Create an instance with explicit environment
        event = AnalyticsEvent(
            event_name="test",
            environment="staging"
        )
        assert event.environment == "staging"
    
    def test_score_model_has_environment_column(self):
        """Test that Score model has environment column."""
        from backend.fastapi.api.models import Score
        
        # Check that the model has the environment attribute
        assert hasattr(Score, 'environment')
    
    def test_journal_entry_model_has_environment_column(self):
        """Test that JournalEntry model has environment column."""
        from backend.fastapi.api.models import JournalEntry
        
        # Check that the model has the environment attribute
        assert hasattr(JournalEntry, 'environment')


class TestMigration:
    """Tests for database migration."""
    
    def test_migration_file_exists(self):
        """Test that migration file was created."""
        import os
        migration_path = "/Users/takku/Desktop/Elite hack/SOUL_SENSE_EXAM/migrations/versions/f0e1d2c3b4a5_add_environment_separation_columns.py"
        assert os.path.exists(migration_path)
    
    def test_migration_has_correct_revision(self):
        """Test that migration has correct revision ID."""
        migration_path = "/Users/takku/Desktop/Elite hack/SOUL_SENSE_EXAM/migrations/versions/f0e1d2c3b4a5_add_environment_separation_columns.py"
        
        with open(migration_path, 'r') as f:
            content = f.read()
            assert "revision: str = 'f0e1d2c3b4a5'" in content
            assert "environment" in content
            assert "analytics_events" in content
            assert "scores" in content
            assert "journal_entries" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
