import pytest
from unittest.mock import MagicMock, patch
import datetime
# Import app modules directly as standard patching handles mocks
from app.ui.journal import JournalFeature
from app.services.journal_service import JournalService

class TestJournalSentimentAnalysis:
    """Test suite for journal sentiment analysis functionality"""

    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.colors = {
            "bg": "#f0f0f0", "surface": "white", "text_primary": "black",
            "text_secondary": "#666", "primary": "#8B5CF6", "secondary": "#EC4899"
        }
        app.username = "test_user"
        return app

    # Patch at the source where they are used
    @patch('app.ui.journal.tk')
    @patch('app.ui.journal.ttk')
    @patch('app.ui.journal.messagebox')
    @patch('app.ui.journal.scrolledtext')
    def test_initialization(self, mock_st, mock_mb, mock_ttk, mock_tk, mock_app):
        mock_root = MagicMock()
        
        # Mock widgets
        mock_tk.Frame.return_value = MagicMock()
        mock_tk.Label.return_value = MagicMock()
        mock_tk.DoubleVar.return_value = MagicMock()
        mock_tk.IntVar.return_value = MagicMock()
        
        # Initialize
        with patch.object(JournalFeature, '_initialize_sentiment_analyzer', MagicMock()):
            feature = JournalFeature(mock_root, app=mock_app)
            assert feature is not None

    @patch('app.ui.journal.tk')
    @patch('app.ui.journal.ttk')
    def test_analyze_sentiment_logic(self, mock_ttk, mock_tk, mock_app):
        # We can test verify logic without full UI initialization if we partially mock
        mock_root = MagicMock()
        
        with patch.object(JournalFeature, '_initialize_sentiment_analyzer', MagicMock()):
            feature = JournalFeature(mock_root, app=mock_app)
            
        feature.sia = MagicMock()
        
        # Test positive
        feature.sia.polarity_scores.return_value = {'compound': 0.8}
        assert feature.analyze_sentiment("Happy") == 80.0
        
        # Test negative
        feature.sia.polarity_scores.return_value = {'compound': -0.8}
        assert feature.analyze_sentiment("Sad") == -80.0

    @patch('app.ui.journal.tk')
    @patch('app.ui.journal.ttk')
    @patch('app.ui.journal.JournalService') # Patch service in UI
    @patch('app.ui.components.loading_overlay.show_loading')
    @patch('app.ui.components.loading_overlay.hide_loading')
    def test_save_and_analyze_integration(self, mock_hide, mock_show, mock_service, mock_ttk, mock_tk, mock_app):
        mock_root = MagicMock()
        
        with patch.object(JournalFeature, '_initialize_sentiment_analyzer', MagicMock()):
            feature = JournalFeature(mock_root, app=mock_app)
            
        # Setup UI references
        feature.text_area = MagicMock()
        feature.text_area.get.return_value = "My journal entry"
        
        for v in ['sleep_hours_var', 'sleep_quality_var', 'energy_level_var', 
                  'stress_level_var', 'work_hours_var', 'screen_time_var']:
            setattr(feature, v, MagicMock())
            getattr(feature, v).get.return_value = 5
            
        feature.tags_entry = MagicMock()
        feature.schedule_text = MagicMock()
        feature.triggers_text = MagicMock()
        feature.parent_root = MagicMock()
        
        # Mock logic
        feature.analyze_sentiment = MagicMock(return_value=80.0)
        feature.generate_health_insights = MagicMock(return_value="Insight")
        feature.show_analysis_results = MagicMock()
        
        feature.save_and_analyze()
        
        assert mock_service.create_entry.called

class TestJournalServiceDatabase:
    """Test service with DB context mocked"""
    
    @patch('app.services.journal_service.safe_db_context')
    @patch('app.services.journal_service.JournalEntry') # Mock model to avoid schema need
    def test_create_entry_success(self, MockEntry, mock_safe_db_context):
        # Setup session mock
        mock_session = MagicMock()
        mock_safe_db_context.return_value.__enter__.return_value = mock_session
        
        # Call service
        result = JournalService.create_entry("user", "content", 50, "patterns")
        
        assert result is not None
        assert mock_session.add.called
        assert MockEntry.called

    @patch('app.services.journal_service.safe_db_context')
    @patch('app.services.journal_service.JournalEntry')
    @patch('app.services.journal_service.desc')
    def test_get_entries(self, mock_desc, MockEntry, mock_safe_db_context):
        mock_session = MagicMock()
        mock_safe_db_context.return_value.__enter__.return_value = mock_session
        
        # Mock query chain
        mock_query = mock_session.query.return_value
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = ["e1", "e2"]
        
        result = JournalService.get_entries("user")
        
        assert len(result) == 2
