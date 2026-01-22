import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ui.journal import JournalFeature
from app.models import JournalEntry

class TestSmartInsights(unittest.TestCase):
    def setUp(self):
        self.mock_root = MagicMock()
        self.feature = JournalFeature(self.mock_root)
        self.feature.username = "test_user"

    @patch('app.services.journal_service.JournalService.get_recent_entries')
    def test_digital_overload_insight(self, mock_get_entries):
        # Setup mock entries
        entries = []
        for i in range(3):
            entry = JournalEntry(
                username="test_user",
                entry_date=datetime.now() - timedelta(days=i),
                content="test content",
                sentiment_score=0.5,
                emotional_patterns="{}",
                # High Screen (>240), High Stress (>6)
                screen_time_mins=300, 
                stress_level=8,
                sleep_hours=7,
                energy_level=6,
                work_hours=8
            )
            entries.append(entry)
        
        mock_get_entries.return_value = entries
        
        # Run logic
        insight = self.feature.generate_health_insights()
        
        # Verify
        print(f"Insight Generated: {insight}")
        self.assertIn("Digital Overload", insight)
        self.assertIn("Reducing screen time", insight)
        
    @patch('app.services.journal_service.JournalService.get_recent_entries')
    def test_burnout_insight(self, mock_get_entries):
         # Setup mock entries
        entries = []
        for i in range(3):
            entry = JournalEntry(
                username="test_user",
                entry_date=datetime.now() - timedelta(days=i),
                content="test content",
                # High Work (>9), Low Energy (<5)
                screen_time_mins=120, 
                stress_level=5,
                sleep_hours=7,
                energy_level=3,
                work_hours=12
            )
            entries.append(entry)
        
        mock_get_entries.return_value = entries
        
        # Run logic
        insight = self.feature.generate_health_insights()
        
        # Verify
        print(f"Insight Generated: {insight}")
        self.assertIn("Early Burnout", insight)

if __name__ == '__main__':
    unittest.main()
