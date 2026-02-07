"""
Unit Tests for Smart Journal Prompts Service (Issue #586)

Tests the SmartPromptService that provides AI-personalized journal prompts
based on user's emotional context, EQ scores, and journal sentiment trends.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Import the service and prompt database
from backend.fastapi.api.services.smart_prompt_service import (
    SmartPromptService,
    SMART_PROMPTS
)


class TestSmartPromptsDatabase:
    """Test prompt database structure and content."""
    
    def test_prompt_database_has_required_categories(self):
        """Verify all expected categories exist."""
        required_categories = [
            "anxiety", "stress", "sadness", "low_energy", 
            "gratitude", "positivity", "reflection", "relationships", 
            "creativity", "general"
        ]
        for category in required_categories:
            assert category in SMART_PROMPTS, f"Missing category: {category}"
    
    def test_each_category_has_minimum_prompts(self):
        """Each category should have at least 5 prompts."""
        for category, prompts in SMART_PROMPTS.items():
            assert len(prompts) >= 5, f"Category {category} has only {len(prompts)} prompts"
    
    def test_prompt_structure_is_valid(self):
        """Each prompt should have required fields."""
        for category, prompts in SMART_PROMPTS.items():
            for prompt in prompts:
                assert "id" in prompt, f"Missing 'id' in {category}"
                assert "prompt" in prompt, f"Missing 'prompt' in {category}"
                assert isinstance(prompt["prompt"], str), f"Prompt text should be string in {category}"
                assert len(prompt["prompt"]) > 10, f"Prompt too short in {category}"


class TestSmartPromptService:
    """Test the SmartPromptService logic."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mock DB."""
        return SmartPromptService(mock_db)
    
    def test_get_time_category_morning(self, service):
        """Test time category detection for morning hours."""
        with patch('backend.fastapi.api.services.smart_prompt_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 9, 0, 0)  # 9 AM
            category = service._get_time_category()
            assert category == "morning"
    
    def test_get_time_category_evening(self, service):
        """Test time category detection for evening hours."""
        with patch('backend.fastapi.api.services.smart_prompt_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 19, 0, 0)  # 7 PM
            category = service._get_time_category()
            assert category == "evening"
    
    def test_get_smart_prompts_returns_correct_count(self, service, mock_db):
        """Verify correct number of prompts returned."""
        # Mock empty user context (new user)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = service.get_smart_prompts(user_id=1, count=3)
        
        assert "prompts" in result
        assert len(result["prompts"]) == 3
    
    def test_get_smart_prompts_returns_required_fields(self, service, mock_db):
        """Verify prompt response has all required fields."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = service.get_smart_prompts(user_id=1, count=3)
        
        assert "prompts" in result
        assert "user_mood" in result
        assert "detected_patterns" in result
        assert "sentiment_avg" in result
        
        for prompt in result["prompts"]:
            assert "id" in prompt
            assert "prompt" in prompt
            assert "category" in prompt
            assert "context_reason" in prompt
    
    def test_high_stress_user_gets_stress_prompts(self, service, mock_db):
        """User with high stress should receive stress-related prompts."""
        # Mock high stress journal entries
        mock_entry = MagicMock()
        mock_entry.sentiment_score = 40
        mock_entry.stress_level = 8
        mock_entry.emotional_patterns = '"stressed"'
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_entry]
        
        result = service.get_smart_prompts(user_id=1, count=3)
        
        # Should have at least one stress-related category
        categories = [p["category"] for p in result["prompts"]]
        assert any(c in ["stress", "anxiety"] for c in categories), f"Expected stress prompts, got: {categories}"
    
    def test_positive_mood_user_gets_gratitude_prompts(self, service, mock_db):
        """User with positive mood should receive gratitude/positivity prompts."""
        mock_entry = MagicMock()
        mock_entry.sentiment_score = 85
        mock_entry.stress_level = 2
        mock_entry.emotional_patterns = None
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_entry]
        
        result = service.get_smart_prompts(user_id=1, count=3)
        
        categories = [p["category"] for p in result["prompts"]]
        assert any(c in ["gratitude", "positivity"] for c in categories), f"Expected positive prompts, got: {categories}"
    
    def test_new_user_gets_general_prompts(self, service, mock_db):
        """New user with no history should receive general prompts."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = service.get_smart_prompts(user_id=1, count=3)
        
        categories = [p["category"] for p in result["prompts"]]
        assert "general" in categories or "gratitude" in categories
    
    def test_prompts_are_unique(self, service, mock_db):
        """Verify no duplicate prompts are returned."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = service.get_smart_prompts(user_id=1, count=5)
        
        prompt_ids = [p["id"] for p in result["prompts"]]
        assert len(prompt_ids) == len(set(prompt_ids)), "Duplicate prompts returned"


class TestSmartPromptsAPI:
    """Integration tests for the API endpoint (mocked)."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock FastAPI test client."""
        # This would be used in actual API integration tests
        return MagicMock()
    
    def test_endpoint_requires_authentication(self):
        """Verify endpoint requires valid auth token."""
        # Placeholder - actual implementation would use TestClient
        pass
    
    def test_endpoint_validates_count_parameter(self):
        """Verify count parameter validation (1-5)."""
        # Placeholder - actual implementation would test boundary cases
        pass


class TestContextAnalysis:
    """Test the user context analysis functionality."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_db):
        return SmartPromptService(mock_db)
    
    def test_context_includes_all_required_fields(self, service, mock_db):
        """Verify context dictionary has all expected keys."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        context = service.get_user_context(user_id=1)
        
        required_keys = [
            "latest_eq_score", "avg_sentiment_7d", "sentiment_trend",
            "recent_stress_avg", "detected_patterns", "entry_count_7d",
            "current_time_category"
        ]
        for key in required_keys:
            assert key in context, f"Missing context key: {key}"
    
    def test_sentiment_trend_detection_improving(self, service, mock_db):
        """Test trend detection when sentiment is improving."""
        # Create entries with improving sentiment
        entries = []
        for i, score in enumerate([30, 35, 45, 50, 55, 60, 70, 75]):
            entry = MagicMock()
            entry.sentiment_score = score
            entry.stress_level = 5
            entry.emotional_patterns = None
            entries.append(entry)
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = list(reversed(entries))
        
        context = service.get_user_context(user_id=1)
        
        # Recent entries (first half) have higher scores, so trend should be improving
        assert context["sentiment_trend"] == "improving"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
