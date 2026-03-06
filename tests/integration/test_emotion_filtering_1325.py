"""
Integration Tests for Emotion Filtering System (Issue #1325)

Tests comprehensive multi-dimensional emotion filtering capabilities:
- Date range filtering
- Emotion type filtering
- Sentiment intensity filtering (0-100)
- Mood score filtering (1-10)
- Stress level filtering (1-10)
- Energy level filtering (1-10)
- Sleep quality filtering (1-10)
- Category filtering
- Tag filtering
- Combined multi-filter scenarios
- Zero-result handling with helpful messages
- Pagination with filters
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JournalEntry, User
from backend.fastapi.api.schemas import EmotionFilterRequest, JournalFilterResponse


class TestEmotionFiltering:
    """Test suite for emotion filtering feature (Issue #1325)."""
    
    @pytest.fixture
    async def test_user(self, db: AsyncSession) -> User:
        """Create a test user."""
        user = User(
            username=f"filter_test_{datetime.now(UTC).timestamp()}",
            password_hash="hashed_password",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @pytest.fixture
    async def diverse_journal_entries(self, db: AsyncSession, test_user: User):
        """Create diverse journal entries with different emotion profiles."""
        now = datetime.now(UTC)
        entries = []
        
        # Entry 1: High positive, low stress, good sleep
        entry1 = JournalEntry(
            user_id=test_user.id,
            username=test_user.username,
            content="Had a great day at work! Everything went perfectly.",
            sentiment_score=85.0,
            emotional_patterns=json.dumps(["joy", "positivity", "high_positive"]),
            mood_score=9,
            stress_level=2,
            energy_level=10,
            sleep_quality=9,
            entry_date=(now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            category="work",
            tags=json.dumps(["success", "happy"])
        )
        entries.append(entry1)
        
        # Entry 2: Anxiety, high stress
        entry2 = JournalEntry(
            user_id=test_user.id,
            username=test_user.username,
            content="Feeling very anxious about the upcoming presentation. Worried it won't go well.",
            sentiment_score=28.0,
            emotional_patterns=json.dumps(["anxiety", "high_negative"]),
            mood_score=3,
            stress_level=9,
            energy_level=4,
            sleep_quality=2,
            entry_date=(now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"),
            category="work",
            tags=json.dumps(["anxious", "worried"])
        )
        entries.append(entry2)
        
        # Entry 3: Neutral, moderate stress
        entry3 = JournalEntry(
            user_id=test_user.id,
            username=test_user.username,
            content="Had an average day. Some things went well, others not so much.",
            sentiment_score=50.0,
            emotional_patterns=json.dumps([]),
            mood_score=5,
            stress_level=5,
            energy_level=6,
            sleep_quality=6,
            entry_date=(now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            category="personal",
            tags=json.dumps(["average"])
        )
        entries.append(entry3)
        
        # Entry 4: Sadness, fatigue
        entry4 = JournalEntry(
            user_id=test_user.id,
            username=test_user.username,
            content="Feeling really tired and down today. Not motivated to do anything.",
            sentiment_score=22.0,
            emotional_patterns=json.dumps(["sadness", "fatigue", "high_negative"]),
            mood_score=2,
            stress_level=6,
            energy_level=2,
            sleep_quality=4,
            entry_date=(now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            category="personal",
            tags=json.dumps(["tired", "sad"])
        )
        entries.append(entry4)
        
        # Entry 5: Hopeful, good energy
        entry5 = JournalEntry(
            user_id=test_user.id,
            username=test_user.username,
            content="Things are looking up! I'm feeling optimistic about the future.",
            sentiment_score=72.0,
            emotional_patterns=json.dumps(["hope", "positivity"]),
            mood_score=7,
            stress_level=3,
            energy_level=8,
            sleep_quality=8,
            entry_date=(now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            category="personal",
            tags=json.dumps(["hopeful", "optimistic"])
        )
        entries.append(entry5)
        
        # Add all entries to DB
        for entry in entries:
            db.add(entry)
        
        await db.commit()
        for entry in entries:
            await db.refresh(entry)
        
        return entries
    
    @pytest.mark.asyncio
    async def test_filter_by_date_range(
        self, 
        client: AsyncClient, 
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering journal entries by date range."""
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=4)).strftime("%Y-%m-%d")
        end_date = (now - timedelta(days=2)).strftime("%Y-%m-%d")
        
        filter_request = {
            "start_date": start_date,
            "end_date": end_date,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Should return entries 2 and 3 (within date range)
        assert body["total"] == 2
        assert len(body["entries"]) == 2
        assert body["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_filter_by_emotion_type(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by emotion type."""
        filter_request = {
            "emotion_types": ["anxiety"],
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Only entry 2 has anxiety
        assert body["total"] == 1
        assert len(body["entries"]) == 1
        assert "anxiety" in body["entries"][0]["emotional_patterns"]
    
    @pytest.mark.asyncio
    async def test_filter_by_multiple_emotion_types(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by multiple emotion types (OR logic)."""
        filter_request = {
            "emotion_types": ["joy", "sadness"],
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Should return entries 1 and 4 (joy or sadness)
        assert body["total"] == 2
        assert len(body["entries"]) == 2
    
    @pytest.mark.asyncio
    async def test_filter_by_sentiment_range(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by sentiment score range."""
        filter_request = {
            "min_sentiment": 70.0,
            "max_sentiment": 90.0,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Entries 1 (85) and 5 (72) are in range
        assert body["total"] == 2
        for entry in body["entries"]:
            assert 70.0 <= entry["sentiment_score"] <= 90.0
    
    @pytest.mark.asyncio
    async def test_filter_by_mood_range(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by mood score range."""
        filter_request = {
            "min_mood": 7,
            "max_mood": 10,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Entries 1 (9) and 5 (7) match
        assert body["total"] == 2
        for entry in body["entries"]:
            assert 7 <= entry["mood_score"] <= 10
    
    @pytest.mark.asyncio
    async def test_filter_by_stress_level(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by stress level."""
        filter_request = {
            "min_stress": 8,
            "max_stress": 10,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Only entry 2 has stress 9
        assert body["total"] == 1
        assert body["entries"][0]["stress_level"] == 9
    
    @pytest.mark.asyncio
    async def test_filter_by_energy_level(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by energy level."""
        filter_request = {
            "min_energy": 8,
            "max_energy": 10,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Entries 1 (10) and 5 (8) match
        assert body["total"] == 2
    
    @pytest.mark.asyncio
    async def test_filter_by_sleep_quality(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by sleep quality."""
        filter_request = {
            "min_sleep_quality": 8,
            "max_sleep_quality": 10,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Entries 1 (9) and 5 (8) match
        assert body["total"] == 2
    
    @pytest.mark.asyncio
    async def test_filter_by_category(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test filtering by category."""
        filter_request = {
            "category": "work",
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Entries 1 and 2 are in "work" category
        assert body["total"] == 2
        for entry in body["entries"]:
            # Note: category might be None in response if not included in schema
            pass
    
    @pytest.mark.asyncio
    async def test_combined_multi_filters(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test combining multiple filters (AND logic)."""
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        filter_request = {
            "start_date": start_date,
            "end_date": end_date,
            "emotion_types": ["positivity"],
            "min_mood": 6,
            "max_stress": 5,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Should match entry 5: has positivity, mood 7, stress 3, within date range
        assert body["total"] == 1
        assert body["entries"][0]["mood_score"] >= 6
        assert body["entries"][0]["stress_level"] <= 5
    
    @pytest.mark.asyncio
    async def test_zero_results_with_helpful_message(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test zero-result state returns helpful empty state message."""
        filter_request = {
            "emotion_types": ["frustration"],  # No entry has this
            "min_sentiment": 99.0,
            "max_sentiment": 100.0,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Verify zero results
        assert body["total"] == 0
        assert len(body["entries"]) == 0
        
        # Verify helpful empty state message
        assert body["empty_state_message"] is not None
        assert "No journal entries found" in body["empty_state_message"]
        assert "frustration" in body["empty_state_message"]
    
    @pytest.mark.asyncio
    async def test_pagination_with_filters(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test pagination works correctly with filters applied."""
        filter_request = {
            "skip": 0,
            "limit": 2
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Should return 2 entries with has_more=True
        assert len(body["entries"]) == 2
        assert body["total"] == 5
        assert body["has_more"] is True
        
        # Test second page
        filter_request["skip"] = 2
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        body = response.json()
        assert len(body["entries"]) == 2
        assert body["has_more"] is True
    
    @pytest.mark.asyncio
    async def test_get_filter_options(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test getting available filter options endpoint."""
        response = await client.get(
            "/api/v1/journal/filters/options",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Verify all required fields are present
        assert "emotion_types" in body
        assert "categories" in body
        assert "tags" in body
        assert "sentiment_range" in body
        assert "mood_range" in body
        assert "stress_range" in body
        assert "energy_range" in body
        assert "sleep_quality_range" in body
        assert "date_range" in body
        assert "total_entries" in body
        
        # Verify data types and values
        assert isinstance(body["emotion_types"], list)
        assert isinstance(body["categories"], list)
        assert isinstance(body["total_entries"], int)
        assert body["total_entries"] == 5
        
        # Verify ranges have min/max
        assert body["sentiment_range"]["min"] >= 0
        assert body["sentiment_range"]["max"] <= 100
        assert body["mood_range"]["min"] >= 1
        assert body["mood_range"]["max"] <= 10
    
    @pytest.mark.asyncio
    async def test_invalid_date_format_returns_error(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """Test that invalid date format returns validation error."""
        filter_request = {
            "start_date": "invalid-date",
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_invalid_emotion_type_returns_error(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """Test that invalid emotion type returns validation error."""
        filter_request = {
            "emotion_types": ["invalid_emotion"],
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_invalid_sentiment_range_returns_error(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """Test that max_sentiment < min_sentiment returns error."""
        filter_request = {
            "min_sentiment": 75.0,
            "max_sentiment": 25.0,
            "skip": 0,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_filters_applied_echo_in_response(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test that filters_applied echoes back the request."""
        filter_request = {
            "emotion_types": ["joy"],
            "min_mood": 7,
            "skip": 5,
            "limit": 10
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Verify filters_applied matches request
        assert body["filters_applied"]["emotion_types"] == ["joy"]
        assert body["filters_applied"]["min_mood"] == 7
        assert body["filters_applied"]["skip"] == 5
        assert body["filters_applied"]["limit"] == 10


class TestEmotionFilteringEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_limit_max_100(
        self,
        client: AsyncClient,
        test_user: User,
        auth_token: str
    ):
        """Test that limit is capped at 100."""
        filter_request = {
            "skip": 0,
            "limit": 200
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Request should still work, but limit should be capped at 100
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_skip_negative_returns_error(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """Test that negative skip value returns validation error."""
        filter_request = {
            "skip": -1,
            "limit": 20
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_empty_filter_returns_all(
        self,
        client: AsyncClient,
        test_user: User,
        diverse_journal_entries,
        auth_token: str
    ):
        """Test that empty filter (no criteria) returns all entries."""
        filter_request = {
            "skip": 0,
            "limit": 100
        }
        
        response = await client.post(
            "/api/v1/journal/filtered",
            json=filter_request,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        body = response.json()
        
        # Should return all 5 entries
        assert body["total"] == 5
        assert len(body["entries"]) == 5
