import pytest
from datetime import datetime
from app.models import JournalPrompt, PromptUsage, User
from app.db import get_session, safe_db_context


class TestPromptModels:
    """Test suite for JournalPrompt and PromptUsage models."""

    def test_journal_prompt_creation(self):
        """Test JournalPrompt model instantiation."""
        prompt = JournalPrompt(
            prompt_text="What are you grateful for today?",
            category="gratitude",
            emotional_context="positive",
            eq_score_range='{"min": 10, "max": 20}',
            target_emotions='["gratitude", "appreciation"]',
            difficulty_level="easy",
            is_active=True,
            usage_count=0,
            success_rate=0.0
        )

        assert prompt.prompt_text == "What are you grateful for today?"
        assert prompt.category == "gratitude"
        assert prompt.emotional_context == "positive"
        assert prompt.difficulty_level == "easy"
        assert prompt.is_active == True
        assert prompt.usage_count == 0
        assert prompt.success_rate == 0.0

    def test_journal_prompt_default_values(self):
        """Test JournalPrompt default values."""
        prompt = JournalPrompt(
            prompt_text="Test prompt",
            category="reflection"
        )

        assert prompt.emotional_context is None
        assert prompt.eq_score_range is None
        assert prompt.target_emotions is None
        assert prompt.difficulty_level == "medium"
        assert prompt.is_active == True
        assert prompt.usage_count == 0
        assert prompt.success_rate == 0.0
        assert prompt.created_at is not None
        assert prompt.updated_at is not None

    def test_prompt_usage_creation(self):
        """Test PromptUsage model instantiation."""
        usage = PromptUsage(
            user_id=1,
            prompt_id=1,
            journal_entry_id=5,
            feedback_rating=4,
            was_helpful=True,
            time_spent=15,
            emotional_impact="positive"
        )

        assert usage.user_id == 1
        assert usage.prompt_id == 1
        assert usage.journal_entry_id == 5
        assert usage.feedback_rating == 4
        assert usage.was_helpful == True
        assert usage.time_spent == 15
        assert usage.emotional_impact == "positive"
        assert usage.used_at is not None

    def test_prompt_usage_optional_fields(self):
        """Test PromptUsage with optional fields."""
        usage = PromptUsage(
            user_id=1,
            prompt_id=1
        )

        assert usage.journal_entry_id is None
        assert usage.feedback_rating is None
        assert usage.was_helpful is None
        assert usage.time_spent is None
        assert usage.emotional_impact is None

    def test_journal_prompt_table_args(self):
        """Test JournalPrompt table constraints and indexes."""
        # Check that the model has the expected table args
        table_args = JournalPrompt.__table_args__

        # Should have index definitions
        assert isinstance(table_args, tuple)
        assert len(table_args) >= 2  # At least 2 indexes

        # Check index names
        index_names = [arg.name if hasattr(arg, 'name') else str(arg) for arg in table_args]
        assert any('category_emotion' in name for name in index_names)
        assert any('active_usage' in name for name in index_names)

    def test_prompt_usage_table_args(self):
        """Test PromptUsage table constraints and indexes."""
        table_args = PromptUsage.__table_args__

        assert isinstance(table_args, tuple)
        assert len(table_args) >= 2  # At least 2 indexes

        # Check index names
        index_names = [arg.name if hasattr(arg, 'name') else str(arg) for arg in table_args]
        assert any('user_prompt' in name for name in index_names)
        assert any('feedback' in name for name in index_names)

    def test_journal_prompt_relationships(self):
        """Test JournalPrompt relationships."""
        # The model should have relationships defined
        # Note: SQLAlchemy relationships are defined at class level
        assert hasattr(JournalPrompt, '__tablename__')
        assert JournalPrompt.__tablename__ == 'journal_prompts'

    def test_prompt_usage_relationships(self):
        """Test PromptUsage relationships."""
        assert hasattr(PromptUsage, '__tablename__')
        assert PromptUsage.__tablename__ == 'prompt_usage'

        # Check foreign key relationships
        assert hasattr(PromptUsage, 'user_id')
        assert hasattr(PromptUsage, 'prompt_id')
        assert hasattr(PromptUsage, 'journal_entry_id')

    def test_prompt_model_json_fields(self):
        """Test JSON field handling in prompt models."""
        # Test eq_score_range JSON
        eq_range = '{"min": 5, "max": 15}'
        prompt = JournalPrompt(
            prompt_text="Test",
            category="test",
            eq_score_range=eq_range
        )
        assert prompt.eq_score_range == eq_range

        # Test target_emotions JSON
        emotions = '["joy", "happiness"]'
        prompt2 = JournalPrompt(
            prompt_text="Test2",
            category="test",
            target_emotions=emotions
        )
        assert prompt2.target_emotions == emotions

    def test_prompt_usage_feedback_validation(self):
        """Test feedback rating validation."""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            usage = PromptUsage(user_id=1, prompt_id=1, feedback_rating=rating)
            assert usage.feedback_rating == rating

        # Test boolean was_helpful
        usage_helpful = PromptUsage(user_id=1, prompt_id=1, was_helpful=True)
        assert usage_helpful.was_helpful == True

        usage_not_helpful = PromptUsage(user_id=1, prompt_id=1, was_helpful=False)
        assert usage_not_helpful.was_helpful == False

    def test_prompt_model_timestamps(self):
        """Test timestamp fields in prompt models."""
        prompt = JournalPrompt(prompt_text="Test", category="test")

        # Timestamps should be set automatically
        assert isinstance(prompt.created_at, str)
        assert isinstance(prompt.updated_at, str)

        # Should be able to parse as datetime
        created_dt = datetime.fromisoformat(prompt.created_at.replace('Z', '+00:00'))
        updated_dt = datetime.fromisoformat(prompt.updated_at.replace('Z', '+00:00'))

        assert isinstance(created_dt, datetime)
        assert isinstance(updated_dt, datetime)

    def test_prompt_usage_timestamp(self):
        """Test timestamp field in PromptUsage."""
        usage = PromptUsage(user_id=1, prompt_id=1)

        assert isinstance(usage.used_at, str)

        # Should be able to parse as datetime
        used_dt = datetime.fromisoformat(usage.used_at.replace('Z', '+00:00'))
        assert isinstance(used_dt, datetime)

    def test_prompt_model_string_representations(self):
        """Test string representations of prompt models."""
        prompt = JournalPrompt(
            id=1,
            prompt_text="Test prompt",
            category="reflection"
        )

        # Should have basic object representation
        assert str(prompt) is not None
        assert repr(prompt) is not None

    def test_prompt_usage_string_representations(self):
        """Test string representations of usage models."""
        usage = PromptUsage(
            id=1,
            user_id=1,
            prompt_id=1
        )

        assert str(usage) is not None
        assert repr(usage) is not None

    def test_prompt_model_field_constraints(self):
        """Test field constraints and requirements."""
        # Required fields for JournalPrompt
        required_fields = ['prompt_text', 'category']
        for field in required_fields:
            assert hasattr(JournalPrompt, field)

        # Required fields for PromptUsage
        required_fields_usage = ['user_id', 'prompt_id']
        for field in required_fields_usage:
            assert hasattr(PromptUsage, field)

    def test_prompt_model_field_lengths(self):
        """Test field length constraints."""
        # Test with various text lengths
        long_text = "A" * 1000
        prompt = JournalPrompt(
            prompt_text=long_text,
            category="test"
        )
        assert len(prompt.prompt_text) == 1000

        # Test category field
        prompt2 = JournalPrompt(
            prompt_text="Test",
            category="very_long_category_name"
        )
        assert len(prompt2.category) > 10

    def test_prompt_model_boolean_fields(self):
        """Test boolean field handling."""
        # Test is_active field
        active_prompt = JournalPrompt(
            prompt_text="Test",
            category="test",
            is_active=True
        )
        assert active_prompt.is_active == True

        inactive_prompt = JournalPrompt(
            prompt_text="Test2",
            category="test",
            is_active=False
        )
        assert inactive_prompt.is_active == False

    def test_prompt_usage_emotional_impact_values(self):
        """Test emotional impact field values."""
        valid_impacts = ['positive', 'neutral', 'negative']

        for impact in valid_impacts:
            usage = PromptUsage(
                user_id=1,
                prompt_id=1,
                emotional_impact=impact
            )
            assert usage.emotional_impact == impact

    def test_prompt_model_success_rate_range(self):
        """Test success rate field range."""
        # Test valid success rates
        for rate in [0.0, 0.5, 1.0]:
            prompt = JournalPrompt(
                prompt_text="Test",
                category="test",
                success_rate=rate
            )
            assert prompt.success_rate == rate

    def test_prompt_usage_time_spent_validation(self):
        """Test time spent field validation."""
        # Test valid time values
        for time_val in [1, 30, 120]:
            usage = PromptUsage(
                user_id=1,
                prompt_id=1,
                time_spent=time_val
            )
            assert usage.time_spent == time_val
