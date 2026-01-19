"""
Tests for UserEmotionalPatterns feature (Issue #269).

Tests the following:
- Model creation and relationships
- JSON field handling for common_emotions
- Cascade delete behavior
- Integration with journal analysis
"""

import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, UserEmotionalPatterns


@pytest.fixture
def temp_db():
    """Create a temporary in-memory database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestUserEmotionalPatternsModel:
    """Tests for UserEmotionalPatterns database model."""
    
    def test_create_emotional_patterns(self, temp_db):
        """Test creating a new UserEmotionalPatterns record."""
        # Create user first
        user = User(username="emotion_test_user", password_hash="test_hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Create emotional patterns
        ep = UserEmotionalPatterns(
            user_id=user.id,
            common_emotions='["Anxiety", "Stress", "Overthinking"]',
            emotional_triggers="Work deadlines, social situations",
            coping_strategies="Deep breathing, exercise, journaling",
            preferred_support="Encouraging & Motivating"
        )
        temp_db.add(ep)
        temp_db.commit()
        
        # Verify
        saved_ep = temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).first()
        assert saved_ep is not None
        assert saved_ep.preferred_support == "Encouraging & Motivating"
        assert "Anxiety" in saved_ep.common_emotions
    
    def test_emotional_patterns_json_parsing(self, temp_db):
        """Test that common_emotions JSON can be properly parsed."""
        user = User(username="json_test_user", password_hash="test_hash")
        temp_db.add(user)
        temp_db.commit()
        
        emotions_list = ["Calmness", "Joy", "Contentment"]
        ep = UserEmotionalPatterns(
            user_id=user.id,
            common_emotions=json.dumps(emotions_list)
        )
        temp_db.add(ep)
        temp_db.commit()
        
        # Retrieve and parse
        saved_ep = temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).first()
        parsed_emotions = json.loads(saved_ep.common_emotions)
        
        assert isinstance(parsed_emotions, list)
        assert len(parsed_emotions) == 3
        assert "Calmness" in parsed_emotions
        assert "Joy" in parsed_emotions
    
    def test_user_relationship(self, temp_db):
        """Test that User and UserEmotionalPatterns have proper relationship."""
        user = User(username="relation_test", password_hash="test_hash")
        temp_db.add(user)
        temp_db.commit()
        
        ep = UserEmotionalPatterns(
            user_id=user.id,
            common_emotions='["Frustration"]',
            preferred_support="Just Listen & Validate"
        )
        temp_db.add(ep)
        temp_db.commit()
        
        # Access via relationship
        temp_db.refresh(user)
        assert user.emotional_patterns is not None
        assert user.emotional_patterns.preferred_support == "Just Listen & Validate"
        
        # Access user from emotional patterns
        assert ep.user.username == "relation_test"
    
    def test_cascade_delete(self, temp_db):
        """Test that deleting user cascades to UserEmotionalPatterns."""
        user = User(username="cascade_test", password_hash="test_hash")
        temp_db.add(user)
        temp_db.commit()
        
        ep = UserEmotionalPatterns(user_id=user.id, common_emotions='[]')
        temp_db.add(ep)
        temp_db.commit()
        
        # Verify existence
        assert temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).count() == 1
        
        # Delete user
        temp_db.delete(user)
        temp_db.commit()
        
        # Verify cascade
        assert temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).count() == 0
    
    def test_default_values(self, temp_db):
        """Test default values for optional fields."""
        user = User(username="default_test", password_hash="test_hash")
        temp_db.add(user)
        temp_db.commit()
        
        # Create with minimal data
        ep = UserEmotionalPatterns(user_id=user.id)
        temp_db.add(ep)
        temp_db.commit()
        
        saved_ep = temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).first()
        assert saved_ep.common_emotions == "[]"  # Default empty list
        assert saved_ep.emotional_triggers is None
        assert saved_ep.coping_strategies is None
        assert saved_ep.preferred_support is None
    
    def test_all_support_styles(self, temp_db):
        """Test all supported AI response styles can be stored."""
        support_styles = [
            "Encouraging & Motivating",
            "Problem-Solving & Practical",
            "Just Listen & Validate",
            "Distraction & Positivity"
        ]
        
        for i, style in enumerate(support_styles):
            user = User(username=f"style_test_{i}", password_hash="test_hash")
            temp_db.add(user)
            temp_db.commit()
            
            ep = UserEmotionalPatterns(user_id=user.id, preferred_support=style)
            temp_db.add(ep)
            temp_db.commit()
            
            saved = temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).first()
            assert saved.preferred_support == style
    
    def test_update_emotional_patterns(self, temp_db):
        """Test updating existing emotional patterns."""
        user = User(username="update_test", password_hash="test_hash")
        temp_db.add(user)
        temp_db.commit()
        
        ep = UserEmotionalPatterns(
            user_id=user.id,
            common_emotions='["Anxiety"]',
            preferred_support="Encouraging & Motivating"
        )
        temp_db.add(ep)
        temp_db.commit()
        
        # Update
        ep.common_emotions = '["Anxiety", "Stress", "Calmness"]'
        ep.preferred_support = "Problem-Solving & Practical"
        temp_db.commit()
        
        # Verify
        saved = temp_db.query(UserEmotionalPatterns).filter_by(user_id=user.id).first()
        emotions = json.loads(saved.common_emotions)
        assert len(emotions) == 3
        assert saved.preferred_support == "Problem-Solving & Practical"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
