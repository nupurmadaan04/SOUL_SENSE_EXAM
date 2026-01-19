import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

# Import ML classes
from app.ml.risk_predictor import RiskPredictor
from app.ml.clustering import EmotionalProfileClusterer


class TestLazyLoading:
    """Test suite for lazy loading of ML models."""

    def test_risk_predictor_lazy_loading(self):
        """Test that RiskPredictor loads model only when needed."""
        # Initialize predictor
        predictor = RiskPredictor()

        # Model should not be loaded initially
        assert predictor.model is None
        assert predictor._model_loaded is False

        # Call predict - this should trigger lazy loading attempt
        # Since no model files exist, it will use fallback, but the lazy loading logic is still exercised
        result = predictor.predict(25, 0.5, 25)

        # Verify fallback was used (contains "Rule")
        assert "Rule" in result
        # Model should still be None since loading failed
        assert predictor.model is None
        # But _model_loaded should be True to indicate loading was attempted
        assert predictor._model_loaded is True

    def test_clustering_lazy_loading(self):
        """Test that EmotionalProfileClusterer loads model only when needed."""
        # Initialize clusterer
        clusterer = EmotionalProfileClusterer()

        # Model should not be loaded initially
        assert clusterer.is_fitted is False
        assert clusterer.kmeans is None

        # Call predict - this should trigger lazy loading attempt
        # Since no model file exists, it will return None, but the lazy loading logic is exercised
        result = clusterer.predict("test_user")

        # Should return None when no model is available
        assert result is None
        # is_fitted should still be False since loading failed
        assert clusterer.is_fitted is False

    def test_no_startup_loading(self):
        """Test that importing ML classes doesn't load models."""
        # This test ensures that simply importing the classes doesn't trigger model loading
        # We mock the loading functions to ensure they're not called during import

        with patch('joblib.load') as mock_joblib_load, \
             patch('pickle.load') as mock_pickle_load:

            # Import the classes
            from app.ml.risk_predictor import RiskPredictor
            from app.ml.clustering import EmotionalProfileClusterer

            # Create instances
            predictor = RiskPredictor()
            clusterer = EmotionalProfileClusterer()

            # Verify no loading occurred during initialization
            assert not mock_joblib_load.called
            assert not mock_pickle_load.called

            # Models should not be loaded
            assert predictor.model is None
            assert predictor._model_loaded is False
            assert clusterer.is_fitted is False

    def test_fallback_behavior(self):
        """Test that fallback logic works when models can't be loaded."""
        # Test RiskPredictor fallback
        predictor = RiskPredictor(models_dir="/nonexistent")

        # Should use fallback without loading model
        result = predictor.predict(25, 0.5, 25)
        assert "Rule" in result  # Should contain "Rule" from fallback
        assert predictor.model is None

        # Test Clustering fallback
        clusterer = EmotionalProfileClusterer()
        clusterer.model_path = "/nonexistent"

        result = clusterer.predict("test_user")
        assert result is None  # Should return None when can't load

    def test_multiple_calls_efficiency(self):
        """Test that multiple calls don't repeatedly attempt loading when no models exist."""
        predictor = RiskPredictor()

        # First call - should attempt loading
        result1 = predictor.predict(25, 0.5, 25)
        assert predictor._model_loaded is True

        # Second call - should not attempt loading again (already tried)
        result2 = predictor.predict(30, 0.7, 30)

        # Both should use fallback
        assert "Rule" in result1
        assert "Rule" in result2
        assert predictor.model is None  # Still None since no models available


if __name__ == "__main__":
    pytest.main([__file__])
