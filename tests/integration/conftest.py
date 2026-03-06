"""
Pytest fixtures for emotion filtering integration tests (Issue #1325).

Provides test-specific fixtures that extend the base test infrastructure.
Uses SQLAlchemy synchronous session for compatibility with existing project patterns.
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from sqlalchemy.orm import Session

from app.models import User, JournalEntry


@pytest.fixture
def test_user(temp_db: Session) -> User:
    """Create a test user for emotion filtering tests."""
    user = User(
        username=f"test_emotion_filter_{datetime.now(UTC).timestamp()}",
        password_hash="hashed_password_test",
        is_active=True
    )
    temp_db.add(user)
    temp_db.commit()
    temp_db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """
    Generate a test JWT token for user authentication.
    Note: In a real integration test environment, this should use the project's
    actual JWT encoder. For now, this is a placeholder that passes authentication checks.
    """
    # Placeholder token format - would be replaced with actual JWT encoding
    # in a full integration test environment
    return f"test_token_for_user_{test_user.id}"


@pytest.fixture
def diverse_journal_entries(temp_db: Session, test_user: User):
    """
    Create 5 diverse journal entries with different emotion profiles.
    
    Entry profiles:
    1. Positive (joy, high mood, low stress, high energy)
    2. Negative (anxiety, low mood, high stress, low energy)
    3. Mixed (hope, medium metrics)
    4. Sad (sadness, low mood, low energy)
    5. Hopeful (hope, good metrics, good sleep)
    """
    now = datetime.now(UTC)
    
    entries = [
        JournalEntry(
            user_id=test_user.id,
            title="Positive Work Day",
            content="Had great meetings today",
            category="work",
            sentiment_score=85.0,
            emotional_patterns=json.dumps(["joy", "positivity"]),
            mood_score=9,
            stress_level=2,
            energy_level=10,
            sleep_quality=9,
            entry_date=now - timedelta(days=5)
        ),
        JournalEntry(
            user_id=test_user.id,
            title="Stressful Day",
            content="Too many things to do",
            category="work",
            sentiment_score=25.0,
            emotional_patterns=json.dumps(["anxiety", "negative"]),
            mood_score=3,
            stress_level=9,
            energy_level=2,
            sleep_quality=3,
            entry_date=now - timedelta(days=4)
        ),
        JournalEntry(
            user_id=test_user.id,
            title="Mixed Feelings",
            content="Some good, some challenging",
            category="personal",
            sentiment_score=50.0,
            emotional_patterns=json.dumps(["hope", "positivity"]),
            mood_score=5,
            stress_level=5,
            energy_level=5,
            sleep_quality=5,
            entry_date=now - timedelta(days=3)
        ),
        JournalEntry(
            user_id=test_user.id,
            title="Sad Day",
            content="Didn't go as planned",
            category="personal",
            sentiment_score=20.0,
            emotional_patterns=json.dumps(["sadness", "negative"]),
            mood_score=2,
            stress_level=6,
            energy_level=3,
            sleep_quality=4,
            entry_date=now - timedelta(days=2)
        ),
        JournalEntry(
            user_id=test_user.id,
            title="Hopeful Tomorrow",
            content="Looking forward to new opportunities",
            category="work",
            sentiment_score=72.0,
            emotional_patterns=json.dumps(["hope", "positivity"]),
            mood_score=7,
            stress_level=3,
            energy_level=8,
            sleep_quality=8,
            entry_date=now - timedelta(days=1)
        ),
    ]
    
    for entry in entries:
        temp_db.add(entry)
    
    temp_db.commit()
    
    for entry in entries:
        temp_db.refresh(entry)
    
    return entries

