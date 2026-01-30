import pytest
from unittest.mock import patch, MagicMock
from app.ui.journal import JournalFeature
from app.models import JournalEntry
from app.services.journal_service import JournalService
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer


class TestJournalSentimentAnalysis:
    """Test suite for journal sentiment analysis functionality"""

    @pytest.fixture
    def journal_feature(self):
        """Create a JournalFeature instance for testing"""
        mock_app = MagicMock()
        mock_app.colors = {
            "bg": "#f0f0f0",
            "surface": "white",
            "text_primary": "black",
            "text_secondary": "#666",
            "primary": "#8B5CF6",
            "secondary": "#EC4899"
        }
        mock_app.username = "test_user"

        # Mock the parent root
        mock_root = MagicMock()

        feature = JournalFeature(mock_root, app=mock_app)
        return feature

    def test_sentiment_analyzer_initialization(self, journal_feature):
        """Test that VADER sentiment analyzer is properly initialized"""
        assert hasattr(journal_feature, 'sia')
        assert isinstance(journal_feature.sia, SentimentIntensityAnalyzer)

    def test_analyze_sentiment_positive_text(self, journal_feature):
        """Test sentiment analysis with positive text"""
        positive_text = "I feel amazing today! Everything is going great and I'm so happy!"
        score = journal_feature.analyze_sentiment(positive_text)

        assert score > 20  # Should be positive
        assert score <= 100  # Should be within bounds

    def test_analyze_sentiment_negative_text(self, journal_feature):
        """Test sentiment analysis with negative text"""
        negative_text = "I'm feeling terrible today. Everything is going wrong and I'm so sad."
        score = journal_feature.analyze_sentiment(negative_text)

        assert score < -20  # Should be negative
        assert score >= -100  # Should be within bounds

    def test_analyze_sentiment_neutral_text(self, journal_feature):
        """Test sentiment analysis with neutral text"""
        neutral_text = "Today was an ordinary day. I did my usual routine and nothing special happened."
        score = journal_feature.analyze_sentiment(neutral_text)

        assert -20 <= score <= 20  # Should be neutral

    def test_analyze_sentiment_empty_text(self, journal_feature):
        """Test sentiment analysis with empty text"""
        score = journal_feature.analyze_sentiment("")
        assert score == 0.0

    def test_analyze_sentiment_whitespace_only(self, journal_feature):
        """Test sentiment analysis with whitespace-only text"""
        score = journal_feature.analyze_sentiment("   \n\t   ")
        assert score == 0.0

    def test_extract_emotional_patterns_positive(self, journal_feature):
        """Test emotional pattern extraction for positive content"""
        positive_text = "I feel happy and grateful today. I'm so excited about my achievements!"
        patterns = journal_feature.extract_emotional_patterns(positive_text)

        assert "general expression" in patterns.lower()

    def test_extract_emotional_patterns_stress(self, journal_feature):
        """Test emotional pattern extraction for stress-related content"""
        stress_text = "I'm feeling stressed and overwhelmed with all the pressure at work."
        patterns = journal_feature.extract_emotional_patterns(stress_text)

        assert "stress" in patterns.lower()

    def test_extract_emotional_patterns_growth(self, journal_feature):
        """Test emotional pattern extraction for growth-oriented content"""
        growth_text = "I'm learning new skills and growing every day. This is helping me improve myself."
        patterns = journal_feature.extract_emotional_patterns(growth_text)

        assert "growth" in patterns.lower()

    def test_extract_emotional_patterns_social(self, journal_feature):
        """Test emotional pattern extraction for social content"""
        social_text = "I had a great conversation with my friend today. Family time was wonderful."
        patterns = journal_feature.extract_emotional_patterns(social_text)

        assert "social" in patterns.lower()

    def test_extract_emotional_patterns_reflection(self, journal_feature):
        """Test emotional pattern extraction for self-reflection"""
        reflection_text = "I realize that I need to be more patient. I'm thinking about how to improve."
        patterns = journal_feature.extract_emotional_patterns(reflection_text)

        assert "reflect" in patterns.lower()

    def test_mood_from_score_positive(self, journal_feature):
        """Test mood classification from sentiment score"""
        mood = journal_feature._app_mood_from_score(50)
        assert mood == "Positive"

    def test_mood_from_score_negative(self, journal_feature):
        """Test mood classification from sentiment score"""
        mood = journal_feature._app_mood_from_score(-50)
        assert mood == "Negative"

    def test_mood_from_score_neutral(self, journal_feature):
        """Test mood classification from sentiment score"""
        mood = journal_feature._app_mood_from_score(0)
        assert mood == "Neutral"

    @patch('app.services.journal_service.JournalService.create_entry')
    def test_save_and_analyze_integration(self, mock_create_entry, journal_feature):
        """Test the complete save and analyze workflow"""
        # Mock the text area and other UI elements
        journal_feature.text_area = MagicMock()
        journal_feature.text_area.get.return_value = "I feel great today! Everything is wonderful."

        journal_feature.sleep_hours_var = MagicMock()
        journal_feature.sleep_hours_var.get.return_value = 8.0

        journal_feature.sleep_quality_var = MagicMock()
        journal_feature.sleep_quality_var.get.return_value = 8

        journal_feature.energy_level_var = MagicMock()
        journal_feature.energy_level_var.get.return_value = 9

        journal_feature.stress_level_var = MagicMock()
        journal_feature.stress_level_var.get.return_value = 3

        journal_feature.work_hours_var = MagicMock()
        journal_feature.work_hours_var.get.return_value = 8.0

        journal_feature.screen_time_var = MagicMock()
        journal_feature.screen_time_var.get.return_value = 120

        journal_feature.tags_entry = MagicMock()
        journal_feature.tags_entry.get.return_value = "gratitude, happiness"

        journal_feature.schedule_text = MagicMock()
        journal_feature.schedule_text.get.return_value = "Work, exercise, reading"

        journal_feature.triggers_text = MagicMock()
        journal_feature.triggers_text.get.return_value = "None today"

        # Mock the parent root for loading overlay
        journal_feature.parent_root = MagicMock()

        # Call the method
        journal_feature.save_and_analyze()

        # Verify that create_entry was called with correct parameters
        mock_create_entry.assert_called_once()
        call_args = mock_create_entry.call_args

        # Check that sentiment score is calculated (should be positive)
        assert call_args[1]['sentiment_score'] > 20  # Should be positive for "great" and "wonderful"

        # Check other parameters
        assert call_args[1]['sleep_hours'] == 8.0
        assert call_args[1]['sleep_quality'] == 8
        assert call_args[1]['energy_level'] == 9
        assert call_args[1]['stress_level'] == 3
        assert call_args[1]['work_hours'] == 8.0
        assert call_args[1]['screen_time_mins'] == 120


class TestJournalServiceDatabase:
    """Test suite for journal database operations"""

    @patch('app.services.journal_service.safe_db_context')
    def test_create_entry_success(self, mock_context):
        """Test successful journal entry creation"""
        mock_session = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_session
        mock_context.return_value.__exit__.return_value = None

        # Mock the entry creation
        mock_entry = MagicMock()
        mock_session.add.return_value = None

        # Call the service method
        result = JournalService.create_entry(
            username="test_user",
            content="Test content",
            sentiment_score=50.0,
            emotional_patterns="Test patterns",
            sleep_hours=8.0,
            energy_level=7
        )

        # Verify database operations
        mock_session.add.assert_called_once()
        assert result is not None

    @patch('app.services.journal_service.safe_db_context')
    def test_get_entries_success(self, mock_context):
        """Test successful journal entries retrieval"""
        mock_session = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_session
        mock_context.return_value.__exit__.return_value = None

        # Mock query results
        mock_entries = [MagicMock(), MagicMock()]
        mock_query = MagicMock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = mock_entries
        mock_session.query.return_value = mock_query

        # Call the service method
        result = JournalService.get_entries("test_user")

        # Verify results
        assert len(result) == 2
        mock_session.query.assert_called_once_with(JournalEntry)

    @patch('app.services.journal_service.safe_db_context')
    def test_get_recent_entries_success(self, mock_context):
        """Test successful recent entries retrieval"""
        mock_session = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_session
        mock_context.return_value.__exit__.return_value = None

        # Mock query results
        mock_entries = [MagicMock(), MagicMock()]
        mock_query = MagicMock()
        mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_entries
        mock_session.query.return_value = mock_query

        # Call the service method
        result = JournalService.get_recent_entries("test_user", days=7)

        # Verify results
        assert len(result) == 2

    @patch('app.services.journal_service.safe_db_context')
    def test_create_entry_database_error(self, mock_context):
        """Test database error handling during entry creation"""
        from app.exceptions import DatabaseError

        mock_context.return_value.__enter__.side_effect = Exception("Database connection failed")

        # Verify exception is raised
        with pytest.raises(DatabaseError):
            JournalService.create_entry(
                username="test_user",
                content="Test content",
                sentiment_score=50.0,
                emotional_patterns="Test patterns"
            )

    @patch('app.services.journal_service.safe_db_context')
    def test_get_entries_database_error(self, mock_context):
        """Test database error handling during entries retrieval"""
        from app.exceptions import DatabaseError

        mock_context.return_value.__enter__.side_effect = Exception("Database connection failed")

        # Verify exception is raised
        with pytest.raises(DatabaseError):
            JournalService.get_entries("test_user")


class TestJournalModel:
    """Test suite for JournalEntry model"""

    def test_journal_entry_creation(self):
        """Test JournalEntry model instantiation"""
        entry = JournalEntry(
            username="test_user",
            content="Test journal content",
            sentiment_score=75.5,
            emotional_patterns="Positive, Grateful",
            sleep_hours=7.5,
            energy_level=8,
            stress_level=3,
            work_hours=8.0,
            screen_time_mins=90,
            tags="gratitude, work"
        )

        assert entry.username == "test_user"
        assert entry.content == "Test journal content"
        assert entry.sentiment_score == 75.5
        assert entry.emotional_patterns == "Positive, Grateful"
        assert entry.sleep_hours == 7.5
        assert entry.energy_level == 8
        assert entry.stress_level == 3
        assert entry.work_hours == 8.0
        assert entry.screen_time_mins == 90
        assert entry.tags == "gratitude, work"

    def test_journal_entry_default_values(self):
        """Test JournalEntry default values"""
        entry = JournalEntry(
            username="test_user",
            content="Test content",
            sentiment_score=0.0,
            emotional_patterns=""
        )

        assert entry.is_deleted == False
        assert entry.privacy_level == "private"
        assert entry.word_count == 0

    def test_journal_entry_relationships(self):
        """Test JournalEntry relationships"""
        # This would require a full database setup, so we'll just verify the relationship exists
        entry = JournalEntry(
            username="test_user",
            content="Test content",
            sentiment_score=0.0,
            emotional_patterns=""
        )

        # Check that the relationship attribute exists
        assert hasattr(entry, 'user')
        assert entry.user_id is None  # Not set in this test
