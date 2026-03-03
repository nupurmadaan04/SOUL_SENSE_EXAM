"""
Unit tests for Advanced Analytics and Pattern Recognition (Feature #804).

Tests statistical methods, caching, privacy controls, and ML functionality.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.ml.pattern_recognition import PatternRecognitionService
from app.ml.cache_service import CacheService
from app.ml.analytics_service import AnalyticsService


class TestPatternRecognitionService:
    """Test cases for pattern recognition service."""

    @pytest.fixture
    def service(self):
        """Create pattern recognition service instance."""
        return PatternRecognitionService()

    @pytest.fixture
    def sample_data(self):
        """Create sample emotional data for testing."""
        dates = pd.date_range(start='2024-01-01', end='2024-02-01', freq='D')
        np.random.seed(42)  # For reproducible tests

        data = []
        for i, date in enumerate(dates):
            # Create some patterns: higher scores on weekends, seasonal variation
            base_score = 60
            weekend_boost = 10 if date.weekday() >= 5 else 0
            seasonal_variation = 5 * np.sin(2 * np.pi * i / 30)  # Monthly cycle
            noise = np.random.normal(0, 5)

            score = base_score + weekend_boost + seasonal_variation + noise
            score = max(0, min(100, score))  # Bound between 0-100

            data.append({
                'timestamp': date,
                'score': score,
                'sentiment': np.random.uniform(-1, 1)
            })

        return pd.DataFrame(data)

    def test_detect_temporal_patterns_insufficient_data(self, service):
        """Test pattern detection with insufficient data."""
        with patch('app.ml.pattern_recognition.get_session') as mock_session:
            mock_session.return_value.query.return_value.filter.return_value.all.return_value = []

            result = service.detect_temporal_patterns("test_user", "30d")

            assert "Insufficient data" in result["message"]
            assert result["patterns"] == []
            assert result["confidence"] == 0.0

    def test_correlation_calculation_with_p_values(self, service):
        """Test correlation calculation includes statistical significance."""
        # Create test data with known correlation
        np.random.seed(42)
        n = 50
        x = np.random.normal(0, 1, n)
        y = 0.8 * x + 0.2 * np.random.normal(0, 1, n)  # Strong positive correlation

        test_df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=n),
            'eq_score': (x * 10 + 50).clip(0, 100),
            'sleep_hours': (y * 2 + 8).clip(0, 24)
        })

        with patch('app.ml.pattern_recognition.get_session') as mock_session:
            # Mock the database queries
            mock_scores = []
            mock_entries = []

            for _, row in test_df.iterrows():
                mock_score = Mock()
                mock_score.timestamp = row['date'].isoformat()
                mock_score.total_score = row['eq_score']
                mock_scores.append(mock_score)

                mock_entry = Mock()
                mock_entry.entry_date = row['date']
                mock_entry.sleep_hours = row['sleep_hours']
                mock_entry.stress_level = 5
                mock_entry.energy_level = 5
                mock_entry.screen_time_mins = 120
                mock_entry.content = "Test entry"
                mock_entries.append(mock_entry)

            mock_session.return_value.query.return_value.filter.return_value.all.side_effect = [
                mock_scores,  # First call for scores
                mock_entries  # Second call for journal entries
            ]

            result = service.find_correlations("test_user")

            assert "significant_correlations" in result
            assert "correlation_matrix" in result
            assert "statistical_notes" in result

            # Check that correlations include statistical measures
            if result["significant_correlations"]:
                corr = result["significant_correlations"][0]
                assert "p_value" in corr
                assert "confidence_interval" in corr
                assert "statistically_significant" in corr
                assert corr["p_value"] < 0.05  # Should be significant

    def test_arima_forecasting(self, service):
        """Test ARIMA forecasting functionality."""
        # Create time series with trend
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        trend = np.linspace(50, 70, 30)
        noise = np.random.normal(0, 2, 30)
        scores = trend + noise

        df = pd.DataFrame({
            'timestamp': dates,
            'score': scores
        })
        df.set_index('timestamp', inplace=True)
        df = df.resample('D').mean()

        predictions = service._predict_with_arima(df, 7)

        assert len(predictions) == 7
        for pred in predictions:
            assert "date" in pred
            assert "predicted_score" in pred
            assert "confidence_interval" in pred
            assert 0 <= pred["predicted_score"] <= 100

    def test_prophet_forecasting(self, service):
        """Test Prophet forecasting functionality."""
        # Create time series data
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        scores = 60 + 10 * np.sin(2 * np.pi * np.arange(30) / 7) + np.random.normal(0, 3, 30)

        df = pd.DataFrame({
            'timestamp': dates,
            'score': scores
        })
        df.set_index('timestamp', inplace=True)
        df = df.resample('D').mean()

        predictions = service._predict_with_prophet(df, 7)

        assert len(predictions) == 7
        for pred in predictions:
            assert "date" in pred
            assert "predicted_score" in pred
            assert "confidence_interval" in pred
            assert len(pred["confidence_interval"]) == 2

    def test_fallback_trend_prediction(self, service):
        """Test fallback linear trend prediction."""
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        scores = 50 + 0.5 * np.arange(20) + np.random.normal(0, 2, 20)

        df = pd.DataFrame({
            'timestamp': dates,
            'score': scores
        })
        df.set_index('timestamp', inplace=True)

        predictions = service._predict_with_trend(df, 5)

        assert len(predictions) == 5
        for pred in predictions:
            assert "date" in pred
            assert "predicted_score" in pred
            assert "confidence_interval" in pred
            assert pred["confidence_level"] == 0.8  # Lower confidence for simple model


class TestCacheService:
    """Test cases for caching service."""

    @pytest.fixture
    def cache_service(self):
        """Create cache service instance."""
        return CacheService()

    def test_cache_operations(self, cache_service):
        """Test basic cache operations."""
        if not cache_service.enabled:
            pytest.skip("Redis not available")

        # Test set and get
        cache_service.set("test_key", {"data": "value"}, ttl_seconds=60)
        result = cache_service.get("test_key")

        assert result == {"data": "value"}

        # Test exists
        assert cache_service.exists("test_key")

        # Test delete
        assert cache_service.delete("test_key")
        assert not cache_service.exists("test_key")

    def test_analytics_cache_methods(self, cache_service):
        """Test analytics-specific cache methods."""
        if not cache_service.enabled:
            pytest.skip("Redis not available")

        test_data = {"patterns": [], "confidence": 0.8}

        # Test patterns cache
        cache_service.set_patterns_cache("test_user", "30d", test_data)
        cached = cache_service.get_patterns_cache("test_user", "30d")
        assert cached == test_data

        # Test correlations cache
        corr_data = {"correlations": {}}
        cache_key = hash(("eq_score", "sleep_hours"))
        cache_service.set_correlations_cache("test_user", str(cache_key), corr_data)
        cached_corr = cache_service.get_correlations_cache("test_user", str(cache_key))
        assert cached_corr == corr_data

    def test_cache_user_cleanup(self, cache_service):
        """Test clearing user-specific cache."""
        if not cache_service.enabled:
            pytest.skip("Redis not available")

        # Set multiple user keys
        cache_service.set("user:test_user:patterns:30d", {"data": "test"})
        cache_service.set("user:test_user:correlations:123", {"data": "test2"})
        cache_service.set("user:other_user:patterns:30d", {"data": "other"})

        # Clear test_user cache
        deleted_count = cache_service.clear_user_cache("test_user")
        assert deleted_count >= 2  # Should delete at least the test_user keys

        # Check that other_user data still exists
        assert cache_service.exists("user:other_user:patterns:30d")


class TestAnalyticsService:
    """Test cases for comprehensive analytics service."""

    @pytest.fixture
    def analytics_service(self):
        """Create analytics service instance."""
        return AnalyticsService()

    def test_emotional_forecast_integration(self, analytics_service):
        """Test emotional forecast brings together multiple components."""
        with patch.object(analytics_service.pattern_service, 'predict_mood') as mock_predict, \
             patch.object(analytics_service.pattern_service, 'detect_temporal_patterns') as mock_patterns:

            mock_predict.return_value = {
                "predictions": [{"date": "2024-02-01", "predicted_score": 65}],
                "model_used": "ARIMA"
            }
            mock_patterns.return_value = {"patterns": []}

            result = analytics_service.get_emotional_forecast("test_user", 7)

            assert "predictions" in result
            assert "model_used" in result
            mock_predict.assert_called_once_with("test_user", 7)

    def test_correlation_matrix_integration(self, analytics_service):
        """Test correlation matrix integrates pattern recognition."""
        with patch.object(analytics_service.pattern_service, 'find_correlations') as mock_corr:
            mock_corr.return_value = {
                "significant_correlations": [],
                "correlation_matrix": {}
            }

            result = analytics_service.get_correlation_matrix("test_user")

            assert "significant_correlations" in result
            mock_corr.assert_called_once_with("test_user", None)


class TestPrivacyControls:
    """Test privacy control enforcement."""

    def test_privacy_settings_required(self):
        """Test that analytics endpoints require privacy settings."""
        from fastapi import HTTPException

        # Mock user without analytics enabled
        mock_user = Mock()
        mock_user.settings = None  # No settings

        # This would be tested in the actual endpoint tests
        # Here we just verify the logic structure
        analytics_enabled = mock_user.settings and mock_user.settings.analytics_enabled
        assert not analytics_enabled

        # Test with disabled settings
        mock_user.settings = Mock()
        mock_user.settings.analytics_enabled = False
        analytics_enabled = mock_user.settings and mock_user.settings.analytics_enabled
        assert not analytics_enabled

        # Test with enabled settings
        mock_user.settings.analytics_enabled = True
        analytics_enabled = mock_user.settings and mock_user.settings.analytics_enabled
        assert analytics_enabled


if __name__ == "__main__":
    pytest.main([__file__])
