import logging
"""
Journal Service Layer

Handles business logic for journal entries including:
- CRUD operations with ownership validation
- Sentiment analysis using NLTK VADER
- Search and filtering
- Analytics and trends
"""

import json
import os
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import func, and_, or_, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

# Import models from models module
from ..models import JournalEntry, User
from .gamification_service import GamificationService


# ============================================================================
# Sentiment Analysis
# ============================================================================

# Global analyzer instance
_sia = None

def get_analyzer():
    """Lazy load the sentiment analyzer."""
    global _sia
    if _sia is None:
        try:
            from nltk.sentiment import SentimentIntensityAnalyzer
            import nltk
            try:
                nltk.data.find('sentiment/vader_lexicon.zip')
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
            _sia = SentimentIntensityAnalyzer()
        except Exception:
            # Return None if NLTK fails
            return None
    return _sia

def analyze_sentiment(content: str) -> float:
    """
    Analyze sentiment using NLTK VADER.
    Returns score from 0-100 (50 = neutral).
    Falls back to 50 if NLTK unavailable.
    """
    if not content or len(content.strip()) < 10:
        return 50.0
    
    analyzer = get_analyzer()
    if not analyzer:
         return 50.0

    try:
        scores = analyzer.polarity_scores(content)
        # Convert compound score (-1 to 1) to 0-100 scale
        return round((scores['compound'] + 1) * 50, 2)
    except Exception:
        return 50.0


def detect_emotional_patterns(content: str, sentiment_score: float) -> str:
    """
    Detect emotional patterns in content.
    Returns JSON string of detected patterns.
    """
    patterns = []
    
    content_lower = content.lower()
    
    # Detect common emotional keywords
    if any(word in content_lower for word in ['happy', 'joy', 'excited', 'grateful']):
        patterns.append('positivity')
    if any(word in content_lower for word in ['sad', 'depressed', 'down', 'unhappy']):
        patterns.append('sadness')
    if any(word in content_lower for word in ['anxious', 'worried', 'nervous', 'stress']):
        patterns.append('anxiety')
    if any(word in content_lower for word in ['angry', 'frustrated', 'irritated', 'annoyed']):
        patterns.append('frustration')
    if any(word in content_lower for word in ['tired', 'exhausted', 'drained', 'fatigue']):
        patterns.append('fatigue')
    if any(word in content_lower for word in ['hopeful', 'optimistic', 'looking forward']):
        patterns.append('hope')
    
    # Add sentiment-based pattern
    if sentiment_score >= 70:
        patterns.append('high_positive')
    elif sentiment_score <= 30:
        patterns.append('high_negative')
    
    return json.dumps(patterns)


def calculate_word_count(content: str) -> int:
    """Calculate the number of words in a string."""
    if not content:
        return 0
    return len(content.split())


# ============================================================================
# Journal Service Class
# ============================================================================

class JournalService:
    """Service for managing journal entries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_ownership(self, entry: JournalEntry, current_user: User) -> None:
        """Validate that the current user owns the entry."""
        if entry.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this journal entry"
            )

    def _parse_tags(self, tags: Optional[List[str]]) -> Optional[str]:
        """Convert tags list to JSON string for storage."""
        if tags is None:
            return None
        return json.dumps(tags[:20])  # Limit to 20 tags

    def _load_tags(self, tags_str: Optional[str]) -> List[str]:
        """Convert stored JSON string to tags list."""
        if not tags_str:
            return []
        try:
            return json.loads(tags_str)
        except json.JSONDecodeError:
            return []

    async def create_entry(
        self,
        current_user: User,
        content: str,
        tags: Optional[List[str]] = None,
        privacy_level: str = "private",
        sleep_hours: Optional[float] = None,
        sleep_quality: Optional[int] = None,
        energy_level: Optional[int] = None,
        work_hours: Optional[float] = None,
        screen_time_mins: Optional[int] = None,
        stress_level: Optional[int] = None,
        stress_triggers: Optional[str] = None,
        daily_schedule: Optional[str] = None
    ) -> JournalEntry:
        """Create a new journal entry with sentiment analysis."""
        
        # Analyze sentiment and word count
        sentiment_score = analyze_sentiment(content)
        emotional_patterns = detect_emotional_patterns(content, sentiment_score)
        word_count = calculate_word_count(content)
        
        # Create entry
        entry = JournalEntry(
            username=current_user.username,
            user_id=current_user.id,
            content=content,
            sentiment_score=sentiment_score,
            emotional_patterns=emotional_patterns,
            word_count=word_count,
            tags=self._parse_tags(tags),
            privacy_level=privacy_level,
            entry_date=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            energy_level=energy_level,
            work_hours=work_hours,
            screen_time_mins=screen_time_mins,
            stress_level=stress_level,
            stress_triggers=stress_triggers,
            daily_schedule=daily_schedule
        )
        
        try:
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
        except Exception as e:
            await self.db.rollback()
            raise e
        
        # Attach dynamic fields
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        # Trigger Gamification
        try:
            await GamificationService.award_xp(self.db, current_user.id, 50, "Journal entry")
            await GamificationService.update_streak(self.db, current_user.id, "journal")
            await GamificationService.check_achievements(self.db, current_user.id, "journal")
        except Exception as e:
            logger.error(f"Gamification update failed: {e}")
            
        return entry

    async def get_entries(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[JournalEntry], int]:
        """Get paginated journal entries for the current user."""
        
        limit = min(limit, 100)
        
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        if start_date:
            stmt = stmt.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.filter(JournalEntry.entry_date <= end_date)
        
        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0
        
        # Paginate
        stmt = stmt.order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        
        # Attach dynamic fields
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, total

    async def get_entry_by_id(self, entry_id: int, current_user: User) -> JournalEntry:
        """Get a specific journal entry by ID."""
        stmt = select(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.is_deleted == False
        )
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        # Attach dynamic fields
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        self._validate_ownership(entry, current_user)
        return entry

    async def update_entry(
        self,
        entry_id: int,
        current_user: User,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        privacy_level: Optional[str] = None,
        **wellbeing_fields
    ) -> JournalEntry:
        """Update a journal entry."""
        
        entry = await self.get_entry_by_id(entry_id, current_user)
        
        if content is not None:
            entry.content = content
            entry.sentiment_score = analyze_sentiment(content)
            entry.emotional_patterns = detect_emotional_patterns(content, entry.sentiment_score)
            entry.word_count = calculate_word_count(content)
        
        if tags is not None:
            entry.tags = self._parse_tags(tags)
        
        for field, value in wellbeing_fields.items():
            if value is not None and hasattr(entry, field):
                setattr(entry, field, value)
        
        await self.db.commit()
        await self.db.refresh(entry)
        
        # Attach dynamic fields
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entry

    async def delete_entry(self, entry_id: int, current_user: User) -> bool:
        """Soft delete a journal entry."""
        entry = await self.get_entry_by_id(entry_id, current_user)
        
        entry.is_deleted = True
        entry.deleted_at = datetime.now(UTC)
        await self.db.commit()
        
        return True

    async def search_entries(
        self,
        current_user: User,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sentiment_category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[JournalEntry], int]:
        """Search journal entries with filters.

        SQL Injection safety: all filters use SQLAlchemy ORM parameterised
        binds.  ilike() passes its argument as a bind parameter, never as
        inline SQL text.  The explicit string-concatenation pattern below
        ("% " + value + " %") is the recommended idiomatic form — it avoids
        any ambiguity while still relying on the ORM for escaping.
        """

        limit = min(limit, 100)

        db_query = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )

        # Content search — uses parameterised ilike (no raw SQL interpolation)
        if query:
            # Truncate to prevent DoS via enormous patterns
            safe_query = query[:500]
            db_query = db_query.filter(
                JournalEntry.content.ilike("%" + safe_query + "%")
            )

        # Tag filtering — each tag value is passed as a bind parameter
        if tags:
            for tag in tags:
                safe_tag = tag[:200]  # sanitise length
                db_query = db_query.filter(
                    JournalEntry.tags.ilike("%" + safe_tag + "%")
                )
        
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        if query:
            stmt = stmt.filter(JournalEntry.content.ilike(f"%{query}%"))
        
        if tags:
            for tag in tags:
                stmt = stmt.filter(JournalEntry.tags.ilike(f"%{tag}%"))
        
        if sentiment_category:
            if sentiment_category == "positive":
                stmt = stmt.filter(JournalEntry.sentiment_score > 60)
            elif sentiment_category == "neutral":
                stmt = stmt.filter(JournalEntry.sentiment_score >= 40, JournalEntry.sentiment_score <= 60)
            elif sentiment_category == "negative":
                stmt = stmt.filter(JournalEntry.sentiment_score < 40)

        if start_date:
            stmt = stmt.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.filter(JournalEntry.entry_date <= end_date)
        
        if min_sentiment is not None:
            stmt = stmt.filter(JournalEntry.sentiment_score >= min_sentiment)
        if max_sentiment is not None:
            stmt = stmt.filter(JournalEntry.sentiment_score <= max_sentiment)
        
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0
        
        stmt = stmt.order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, total

    async def get_analytics(self, current_user: User) -> dict:
        """Get journal analytics."""
        
        base_filter = and_(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        stmt = select(
            func.count(JournalEntry.id).label('total'),
            func.avg(JournalEntry.sentiment_score).label('avg_sentiment'),
            func.avg(JournalEntry.stress_level).label('avg_stress'),
            func.avg(JournalEntry.sleep_quality).label('avg_sleep')
        ).filter(base_filter)
        
        result = await self.db.execute(stmt)
        stats = result.first()
        
        total_entries = stats.total or 0
        avg_sentiment = stats.avg_sentiment or 50.0
        avg_stress = stats.avg_stress
        avg_sleep = stats.avg_sleep

        if total_entries == 0:
             return {
                "total_entries": 0,
                "average_sentiment": 50.0,
                "sentiment_trend": "stable",
                "most_common_tags": [],
                "average_stress_level": None,
                "average_sleep_quality": None,
                "entries_this_week": 0,
                "entries_this_month": 0
            }

        now = datetime.now(UTC)
        week_ago_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        two_weeks_ago_date = (now - timedelta(days=14)).strftime("%Y-%m-%d")

        recent_avg_stmt = select(func.avg(JournalEntry.sentiment_score))\
            .filter(base_filter, JournalEntry.entry_date >= week_ago_date)
        recent_avg = (await self.db.execute(recent_avg_stmt)).scalar() or 50.0
            
        older_avg_stmt = select(func.avg(JournalEntry.sentiment_score))\
            .filter(base_filter, 
                   JournalEntry.entry_date >= two_weeks_ago_date,
                   JournalEntry.entry_date < week_ago_date)
        older_avg = (await self.db.execute(older_avg_stmt)).scalar() or 50.0
        
        if recent_avg > older_avg + 5:
            trend = "improving"
        elif recent_avg < older_avg - 5:
            trend = "declining"
        else:
            trend = "stable"

        month_ago_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        
        week_count_stmt = select(func.count(JournalEntry.id))\
            .filter(base_filter, JournalEntry.entry_date >= week_ago_date)
        entries_this_week = (await self.db.execute(week_count_stmt)).scalar() or 0
            
        month_count_stmt = select(func.count(JournalEntry.id))\
            .filter(base_filter, JournalEntry.entry_date >= month_ago_date)
        entries_this_month = (await self.db.execute(month_count_stmt)).scalar() or 0

        tag_stmt = select(JournalEntry.tags).filter(base_filter)
        tag_entries = (await self.db.execute(tag_stmt)).all()
        
        all_tags = []
        for (t_str,) in tag_entries:
             all_tags.extend(self._load_tags(t_str))
             
        from collections import Counter
        tag_counts = Counter(all_tags)
        most_common = [t for t, c in tag_counts.most_common(5)]
        
        return {
            "total_entries": total_entries,
            "average_sentiment": round(float(avg_sentiment), 2),
            "sentiment_trend": trend,
            "most_common_tags": most_common,
            "average_stress_level": round(float(avg_stress), 1) if avg_stress else None,
            "average_sleep_quality": round(float(avg_sleep), 1) if avg_sleep else None,
            "entries_this_week": entries_this_week,
            "entries_this_month": entries_this_month
        }

    async def export_entries(
        self,
        current_user: User,
        format: str = "json",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> str:
        """Export journal entries."""
        
        entries, _ = await self.get_entries(
            current_user,
            skip=0,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )
        
        if format == "json":
            return json.dumps([
                {
                    "id": e.id,
                    "entry_date": e.entry_date,
                    "content": e.content,
                    "sentiment_score": e.sentiment_score,
                    "tags": self._load_tags(e.tags)
                }
                for e in entries
            ], indent=2)
        return ""

logger = logging.getLogger(__name__)

def get_journal_prompts(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a list of journaling prompts."""
    all_prompts = [
        {"id": 1, "text": "What are you most grateful for today?", "category": "gratitude"},
        {"id": 2, "text": "Who made a positive impact on your day?", "category": "gratitude"},
        {"id": 3, "text": "What is one thing you learned about yourself recently?", "category": "reflection"},
        {"id": 4, "text": "How do you feel at this exact moment?", "category": "emotions"},
        {"id": 5, "text": "What is your main priority for tomorrow?", "category": "goals"},
        {"id": 6, "text": "If you could change one thing about your day, what would it be?", "category": "reflection"},
        {"id": 7, "text": "Describe a dream you had recently.", "category": "creativity"},
    ]
    
    if category:
        return [p for p in all_prompts if p["category"] == category]
    return all_prompts

