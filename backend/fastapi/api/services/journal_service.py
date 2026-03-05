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
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Import models from models module
from ..models import JournalEntry, User
from .gamification_service import GamificationService
from ..utils.cache import cache_manager


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
        """Create entry (Async)."""
        
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
            entry_date=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
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
            # Don't fail the whole request if gamification fails
            print(f"Gamification update failed: {e}")
            
        return entry

    async def get_entries_cursor(
        self,
        current_user: User,
        limit: int = 20,
        cursor: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[JournalEntry], Optional[str], bool]:
        """Keyset pagination (Async)."""
        
        # Cap limit at 100
        limit = min(limit, 100)
        
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        # Date filtering
        if start_date:
            stmt = stmt.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.filter(JournalEntry.entry_date <= end_date)

        # Apply Keyset Pagination (Cursor)
        if cursor:
            try:
                # Format: timestamp|id for tie-breaking
                if "|" in cursor:
                    cursor_ts, cursor_id = cursor.split("|")
                    stmt = stmt.filter(
                        or_(
                            JournalEntry.timestamp < cursor_ts,
                            and_(
                                JournalEntry.timestamp == cursor_ts,
                                JournalEntry.id < int(cursor_id)
                            )
                        )
                    )
                else:
                    # Fallback for simple timestamp cursor
                    stmt = stmt.filter(JournalEntry.timestamp < cursor)
            except (ValueError, IndexError):
                pass # Gracefully ignore malformed cursors
        
        # Fetch limit + 1 to determine if has_more
        stmt = stmt.order_by(
            JournalEntry.timestamp.desc(),
            JournalEntry.id.desc()
        ).limit(limit + 1)
        
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        
        has_more = len(entries) > limit
        if has_more:
            entries = entries[:limit]
            last_entry = entries[-1]
            next_cursor = f"{last_entry.timestamp}|{last_entry.id}"
        else:
            next_cursor = None
        
        # Attach dynamic fields
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, next_cursor, has_more

    async def get_entries(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[JournalEntry], int]:
        """Get paginated entries (Async)."""
        limit = min(limit, 100)
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        if start_date:
            stmt = stmt.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.filter(JournalEntry.entry_date <= end_date)
        
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        stmt = stmt.order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, total

    async def get_entry_by_id(self, entry_id: int, current_user: User) -> JournalEntry:
        """Get by ID (Async)."""
        stmt = select(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        
        if not entry:
            logger.warning(f"Journal entry {entry_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Journal entry not found")
            
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        return entry

    async def update_entry(
        self,
        entry_id: int,
        current_user: User,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        privacy_level: Optional[str] = None,
        **kwargs
    ) -> JournalEntry:
        """Update entry (Async)."""
        entry = await self.get_entry_by_id(entry_id, current_user)
        
        if content is not None and content != entry.content:
            entry.content = content
            entry.sentiment_score = analyze_sentiment(content)
            entry.emotional_patterns = detect_emotional_patterns(content, entry.sentiment_score)
            entry.word_count = calculate_word_count(content)
        
        if tags is not None:
            entry.tags = self._parse_tags(tags)
        if privacy_level is not None:
            entry.privacy_level = privacy_level
            
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        try:
            await self.db.commit()
            await self.db.refresh(entry)
            
            # Attach dynamic fields
            entry.reading_time_mins = round(entry.word_count / 200, 2)
            
            return entry
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete_entry(self, entry_id: int, current_user: User) -> bool:
        """Soft delete (Async)."""
        entry = await self.get_entry_by_id(entry_id, current_user)
        entry.is_deleted = True
        await self.db.commit()
        return True

    async def search_entries(
        self,
        current_user: User,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_sentiment: Optional[float] = None,
        max_sentiment: Optional[float] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[JournalEntry], int]:
        """Search entries (Async)."""
        limit = min(limit, 100)
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )

        if query:
            safe_query = query[:500]
            stmt = stmt.filter(JournalEntry.content.ilike("%" + safe_query + "%"))

        if tags:
            for tag in tags:
                safe_tag = tag[:200]
                stmt = stmt.filter(JournalEntry.tags.ilike("%" + safe_tag + "%"))
        
        if start_date:
            stmt = stmt.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            stmt = stmt.filter(JournalEntry.entry_date <= end_date)
        
        if min_sentiment is not None:
            stmt = stmt.filter(JournalEntry.sentiment_score >= min_sentiment)
        if max_sentiment is not None:
            stmt = stmt.filter(JournalEntry.sentiment_score <= max_sentiment)
        
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        stmt = stmt.order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        entries = list(result.scalars().all())
        
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, total

    @cache_manager.cache(ttl=300, prefix="journal_analytics")
    async def get_analytics(self, current_user: User) -> dict:
        """Get analytics (Async)."""
        stmt = select(
            func.count(JournalEntry.id).label('total'),
            func.avg(JournalEntry.sentiment_score).label('avg_sentiment'),
            func.avg(JournalEntry.stress_level).label('avg_stress'),
            func.avg(JournalEntry.sleep_quality).label('avg_sleep')
        ).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        result = await self.db.execute(stmt)
        stats = result.first()
        
        total_entries = stats.total or 0
        avg_sentiment = stats.avg_sentiment or 50.0
        avg_stress = stats.avg_stress
        avg_sleep = stats.avg_sleep

        if total_entries == 0:
             return {
                "total_entries": 0, "average_sentiment": 50.0, "sentiment_trend": "stable",
                "most_common_tags": [], "average_stress_level": None, "average_sleep_quality": None,
                "entries_this_week": 0, "entries_this_month": 0
            }

        now = datetime.utcnow()
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        two_weeks_ago = (now - timedelta(days=14)).strftime("%Y-%m-%d")

        recent_stmt = select(func.avg(JournalEntry.sentiment_score)).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False,
            JournalEntry.entry_date >= week_ago
        )
        recent_avg = (await self.db.execute(recent_stmt)).scalar() or 50.0
            
        older_stmt = select(func.avg(JournalEntry.sentiment_score)).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False,
            JournalEntry.entry_date >= two_weeks_ago,
            JournalEntry.entry_date < week_ago
        )
        older_avg = (await self.db.execute(older_stmt)).scalar() or 50.0
        
        trend = "improving" if recent_avg > older_avg + 5 else "declining" if recent_avg < older_avg - 5 else "stable"

        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        
        week_count = (await self.db.execute(select(func.count(JournalEntry.id)).filter(
            JournalEntry.user_id == current_user.id, JournalEntry.is_deleted == False, JournalEntry.entry_date >= week_ago
        ))).scalar() or 0
            
        month_count = (await self.db.execute(select(func.count(JournalEntry.id)).filter(
            JournalEntry.user_id == current_user.id, JournalEntry.is_deleted == False, JournalEntry.entry_date >= month_ago
        ))).scalar() or 0

        tag_entries = (await self.db.execute(select(JournalEntry.tags).filter(
            JournalEntry.user_id == current_user.id, JournalEntry.is_deleted == False
        ))).all()
        
        all_tags = []
        for (t_str,) in tag_entries:
             all_tags.extend(self._load_tags(t_str))
             
        from collections import Counter
        tag_counts = Counter(all_tags)
        most_common = [t for t, c in tag_counts.most_common(5)]
        
        return {
            "total_entries": total_entries, "average_sentiment": round(avg_sentiment, 2),
            "sentiment_trend": trend, "most_common_tags": most_common,
            "average_stress_level": round(avg_stress, 1) if avg_stress else None,
            "average_sleep_quality": round(avg_sleep, 1) if avg_sleep else None,
            "entries_this_week": week_count, "entries_this_month": month_count
        }

    async def export_entries(
        self,
        current_user: User,
        format: str = "json",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> str:
        """Export (Async)."""
        entries, _ = await self.get_entries(current_user, skip=0, limit=limit, start_date=start_date, end_date=end_date)
        
        if format == "json":
            return json.dumps([
                {
                    "id": e.id, "entry_date": e.entry_date, "content": e.content,
                    "sentiment_score": e.sentiment_score, "tags": self._load_tags(e.tags),
                    "sleep_hours": e.sleep_hours, "sleep_quality": e.sleep_quality,
                    "energy_level": e.energy_level, "stress_level": e.stress_level
                }
                for e in entries
            ], indent=2)
        
        elif format == "txt":
            lines = []
            for e in entries:
                lines.append(f"=== {e.entry_date} ===")
                lines.append(f"Sentiment: {e.sentiment_score}/100")
                lines.append(f"Tags: {', '.join(self._load_tags(e.tags))}")
                lines.append("")
                lines.append(e.content)
                lines.append("")
                lines.append("-" * 50)
                lines.append("")
            return "\n".join(lines)
        
        raise HTTPException(status_code=400, detail="Unsupported format")


# ============================================================================
# AI Journal Prompts
# ============================================================================

JOURNAL_PROMPTS = [
    {"id": 1, "category": "gratitude", "prompt": "What are three things you're grateful for today?", "description": "Focus on positive aspects of your day"},
    {"id": 2, "category": "gratitude", "prompt": "Who made a positive impact on your life recently?", "description": "Reflect on supportive relationships"},
    {"id": 3, "category": "reflection", "prompt": "What lesson did you learn this week?", "description": "Extract wisdom from recent experiences"},
    {"id": 4, "category": "reflection", "prompt": "How have you grown as a person in the last month?", "description": "Track personal development"},
    {"id": 5, "category": "goals", "prompt": "What's one small step you can take tomorrow toward your biggest goal?", "description": "Break down big goals into actions"},
    {"id": 6, "category": "goals", "prompt": "What would you attempt if you knew you couldn't fail?", "description": "Explore ambitions without fear"},
    {"id": 7, "category": "emotions", "prompt": "How are you really feeling right now? Describe it in detail.", "description": "Deep emotional check-in"},
    {"id": 8, "category": "emotions", "prompt": "What's been weighing on your mind lately?", "description": "Release mental burdens"},
    {"id": 9, "category": "creativity", "prompt": "If you could live anywhere for a year, where would you go and why?", "description": "Explore dreams and desires"},
    {"id": 10, "category": "creativity", "prompt": "Describe your perfect day from start to finish.", "description": "Envision your ideal life"},
]


def get_journal_prompts(category: Optional[str] = None) -> List[dict]:
    """Get journal prompts, optionally filtered by category."""
    if category:
        return [p for p in JOURNAL_PROMPTS if p["category"] == category]
    return JOURNAL_PROMPTS
