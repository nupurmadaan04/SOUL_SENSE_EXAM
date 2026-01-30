"""
Tests for AI-Powered EQ Insights functionality.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ml.insights_generator import EQInsightsGenerator


class TestEQInsightsGenerator:
    """Test cases for EQ Insights Generator."""

    @patch('app.ml.insights_generator.get_session')
    def test_generate_insights_basic(self, mock_get_session):
        """Test basic insights generation."""
        # Mock session and database objects
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock user data
        mock_strengths = Mock()
        mock_strengths.top_strengths = '["Empathy", "Self-awareness"]'
        mock_strengths.areas_for_improvement = '["Public speaking"]'
        mock_strengths.learning_style = "Visual"
        mock_strengths.comm_style = "Direct communication"

        mock_patterns = Mock()
        mock_patterns.common_emotions = '["anxiety", "calmness"]'
        mock_patterns.emotional_triggers = "Work deadlines"
        mock_patterns.coping_strategies = "Deep breathing"
        mock_patterns.preferred_support = "Problem-solving"

        # Mock historical scores
        mock_scores = [
            Mock(total_score=15, timestamp="2024-01-01T10:00:00"),
            Mock(total_score=18, timestamp="2024-01-15T10:00:00"),
            Mock(total_score=20, timestamp="2024-01-30T10:00:00")
        ]

        # Configure mocks
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_strengths, mock_patterns
        ]
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_scores
        mock_session.query.return_value.filter.return_value.all.return_value = mock_scores

        # Test insights generation
        generator = EQInsightsGenerator()
        insights = generator.generate_insights(
            user_id=1,
            current_score=20,
            age=25,
            sentiment_score=0.5
        )

        # Verify insights structure
        assert isinstance(insights, dict)
        assert 'recommendations' in insights
        assert 'next_steps' in insights
        assert 'user_cluster' in insights
        assert 'confidence_score' in insights
        assert 'strengths_analysis' in insights
        assert 'pattern_analysis' in insights

        # Verify recommendations are generated
        assert isinstance(insights['recommendations'], list)
        assert len(insights['recommendations']) > 0

        # Verify next steps are generated
        assert isinstance(insights['next_steps'], list)
        assert len(insights['next_steps']) > 0

    @patch('app.ml.insights_generator.get_session')
    def test_analyze_strengths(self, mock_get_session):
        """Test strengths analysis."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        generator = EQInsightsGenerator()

        # Mock user strengths
        mock_strengths = Mock()
        mock_strengths.top_strengths = '["Empathy", "Self-awareness"]'
        mock_strengths.areas_for_improvement = '["Public speaking"]'
        mock_strengths.learning_style = "Visual"
        mock_strengths.comm_style = "Direct communication"

        analysis = generator._analyze_strengths(mock_strengths)

        assert 'top_strengths' in analysis
        assert 'areas_for_improvement' in analysis
        assert 'learning_style' in analysis
        assert 'communication_style' in analysis
        assert analysis['learning_style'] == "Visual"
        assert analysis['communication_style'] == "Direct communication"
        assert "Empathy" in analysis['top_strengths']
        assert "Public speaking" in analysis['areas_for_improvement']

    @patch('app.ml.insights_generator.get_session')
    def test_analyze_patterns(self, mock_get_session):
        """Test emotional patterns analysis."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        generator = EQInsightsGenerator()

        # Mock user patterns
        mock_patterns = Mock()
        mock_patterns.common_emotions = '["anxiety", "calmness"]'
        mock_patterns.emotional_triggers = "Work deadlines"
        mock_patterns.coping_strategies = "Deep breathing"
        mock_patterns.preferred_support = "Problem-solving"

        analysis = generator._analyze_patterns(mock_patterns)

        assert 'common_emotions' in analysis
        assert 'triggers' in analysis
        assert 'coping_strategies' in analysis
        assert 'preferred_support' in analysis
        assert "anxiety" in analysis['common_emotions']
        assert analysis['triggers'] == "Work deadlines"
        assert analysis['coping_strategies'] == "Deep breathing"
        assert analysis['preferred_support'] == "Problem-solving"

    def test_generate_recommendations_score_based(self):
        """Test score-based recommendations."""
        generator = EQInsightsGenerator()

        # Test low score recommendations
        low_score_insights = {
            'user_cluster': 'Beginner',
            'strengths_analysis': {'top_strengths': []},
            'pattern_analysis': {'common_emotions': []}
        }

        recommendations = generator._generate_recommendations(
            current_score=12,
            insights=low_score_insights,
            historical_scores=[]
        )

        assert any("basic emotional awareness" in rec.lower() for rec in recommendations)
        assert any("mindfulness" in rec.lower() for rec in recommendations)

        # Test high score recommendations
        high_score_insights = {
            'user_cluster': 'Advanced',
            'strengths_analysis': {'top_strengths': []},
            'pattern_analysis': {'common_emotions': []}
        }

        recommendations = generator._generate_recommendations(
            current_score=22,
            insights=high_score_insights,
            historical_scores=[]
        )

        assert any("leadership" in rec.lower() or "mentor" in rec.lower() for rec in recommendations)

    def test_generate_next_steps(self):
        """Test next steps generation."""
        generator = EQInsightsGenerator()

        # Test with high improvement potential (> 5 triggers advanced)
        insights_high = {'improvement_potential': 6.0}
        next_steps = generator._generate_next_steps(insights_high)

        assert any("advanced" in step.lower() for step in next_steps)

        # Test with moderate improvement potential
        insights_medium = {'improvement_potential': 3.0}
        next_steps = generator._generate_next_steps(insights_medium)

        assert any("current strengths" in step.lower() for step in next_steps)

        # Test with low improvement potential
        insights_low = {'improvement_potential': -2.0}
        next_steps = generator._generate_next_steps(insights_low)

        assert any("foundational" in step.lower() or "building" in step.lower() for step in next_steps)

    def test_fallback_insights(self):
        """Test fallback insights when ML model is not available."""
        generator = EQInsightsGenerator()

        fallback = generator._get_fallback_insights(18)

        assert 'recommendations' in fallback
        assert 'next_steps' in fallback
        assert 'confidence_score' in fallback
        assert fallback['confidence_score'] == 0.5
        assert len(fallback['recommendations']) > 0
        assert len(fallback['next_steps']) > 0

    @patch('app.ml.insights_generator.joblib.load')
    @patch('app.ml.insights_generator.os.path.exists')
    def test_model_loading(self, mock_exists, mock_load):
        """Test model loading functionality."""
        mock_exists.return_value = True
        mock_load.return_value = {
            'model': Mock(),
            'scaler': Mock(),
            'cluster_model': Mock(),
            'feature_columns': ['age', 'total_score'],
            'trained_at': "2024-01-01T00:00:00"
        }

        generator = EQInsightsGenerator()

        # Should attempt to load model
        mock_load.assert_called_once()
        assert generator.is_trained is True

    def test_collect_feedback(self):
        """Test feedback collection."""
        generator = EQInsightsGenerator()

        # Should not raise exception
        generator.collect_feedback(
            user_id=1,
            insights={'test': 'data'},
            feedback_rating=4,
            feedback_text="Very helpful insights!"
        )


if __name__ == '__main__':
    pytest.main([__file__])
