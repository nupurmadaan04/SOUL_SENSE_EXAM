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

# Import models from root_models module (handles namespace collision)
from api.root_models import JournalEntry, User


# ============================================================================
# Sentiment Analysis
# ============================================================================

def analyze_sentiment(content: str) -> float:
    """
    Analyze sentiment using NLTK VADER.
    Returns score from 0-100 (50 = neutral).
    Falls back to 50 if NLTK unavailable.
    """
    if not content or len(content.strip()) < 10:
        return 50.0
    
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(content)
        # Convert compound score (-1 to 1) to 0-100 scale
        return round((scores['compound'] + 1) * 50, 2)
    except Exception:
        # Graceful fallback if NLTK not available
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

    def __init__(self, db: Session):
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

    def create_entry(
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
            self.db.commit()
            self.db.refresh(entry)
        except Exception as e:
            self.db.rollback()
            raise e
        
        # Attach dynamic fields
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entry

    def get_entries(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[JournalEntry], int]:
        """Get paginated journal entries for the current user."""
        
        # Cap limit at 100
        limit = min(limit, 100)
        
        query = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        # Date filtering
        if start_date:
            query = query.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.entry_date <= end_date)
        
        # Get total count
        total = query.count()
        
        # Get paginated entries
        entries = query.order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit).all()
        
        # Attach dynamic fields
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, total

    def get_entry_by_id(self, entry_id: int, current_user: User) -> JournalEntry:
        """Get a specific journal entry by ID."""
        entry = self.db.query(JournalEntry).filter(
            JournalEntry.id == entry_id,
            JournalEntry.is_deleted == False
        ).first()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        # Attach dynamic fields
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        self._validate_ownership(entry, current_user)
        return entry

    def update_entry(
        self,
        entry_id: int,
        current_user: User,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        privacy_level: Optional[str] = None,
        **wellbeing_fields
    ) -> JournalEntry:
        """Update a journal entry. Re-analyzes sentiment if content changes."""
        
        entry = self.get_entry_by_id(entry_id, current_user)
        
        # Update content and re-analyze sentiment/word count
        if content is not None:
            entry.content = content
            entry.sentiment_score = analyze_sentiment(content)
            entry.emotional_patterns = detect_emotional_patterns(content, entry.sentiment_score)
            entry.word_count = calculate_word_count(content)
        
        # Update tags
        if tags is not None:
            entry.tags = self._parse_tags(tags)
        
        # Update wellbeing fields
        for field, value in wellbeing_fields.items():
            if value is not None and hasattr(entry, field):
                setattr(entry, field, value)
        
        self.db.commit()
        self.db.refresh(entry)
        
        # Attach dynamic fields
        entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entry

    def delete_entry(self, entry_id: int, current_user: User) -> bool:
        """Soft delete a journal entry."""
        entry = self.get_entry_by_id(entry_id, current_user)
        
        entry.is_deleted = True
        self.db.commit()
        
        return True

    def search_entries(
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
        """Search journal entries with filters."""
        
        limit = min(limit, 100)
        
        db_query = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        )
        
        # Content search (case-insensitive LIKE)
        if query:
            db_query = db_query.filter(
                JournalEntry.content.ilike(f"%{query}%")
            )
        
        # Tag filtering
        if tags:
            for tag in tags:
                db_query = db_query.filter(
                    JournalEntry.tags.ilike(f"%{tag}%")
                )
        
        # Date filtering
        if start_date:
            db_query = db_query.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            db_query = db_query.filter(JournalEntry.entry_date <= end_date)
        
        # Sentiment filtering
        if min_sentiment is not None:
            db_query = db_query.filter(JournalEntry.sentiment_score >= min_sentiment)
        if max_sentiment is not None:
            db_query = db_query.filter(JournalEntry.sentiment_score <= max_sentiment)
        
        total = db_query.count()
        entries = db_query.order_by(JournalEntry.entry_date.desc()).offset(skip).limit(limit).all()
        
        # Attach dynamic fields
        for entry in entries:
            entry.reading_time_mins = round(entry.word_count / 200, 2)
        
        return entries, total

    def get_analytics(self, current_user: User) -> dict:
        """Get journal analytics for the current user."""
        
        entries = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == current_user.id,
            JournalEntry.is_deleted == False
        ).all()
        
        if not entries:
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
        
        # Calculate averages
        sentiments = [e.sentiment_score for e in entries if e.sentiment_score]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 50.0
        
        stress_levels = [e.stress_level for e in entries if e.stress_level]
        avg_stress = sum(stress_levels) / len(stress_levels) if stress_levels else None
        
        sleep_qualities = [e.sleep_quality for e in entries if e.sleep_quality]
        avg_sleep = sum(sleep_qualities) / len(sleep_qualities) if sleep_qualities else None
        
        # Calculate trend (compare last week to previous week)
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        
        recent_entries = [e for e in entries if e.entry_date and e.entry_date >= week_ago.strftime("%Y-%m-%d")]
        older_entries = [e for e in entries if e.entry_date and two_weeks_ago.strftime("%Y-%m-%d") <= e.entry_date < week_ago.strftime("%Y-%m-%d")]
        
        if recent_entries and older_entries:
            recent_avg = sum(e.sentiment_score or 50 for e in recent_entries) / len(recent_entries)
            older_avg = sum(e.sentiment_score or 50 for e in older_entries) / len(older_entries)
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Count tags
        all_tags = []
        for entry in entries:
            all_tags.extend(self._load_tags(entry.tags))
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        most_common = sorted(tag_counts.keys(), key=lambda t: tag_counts[t], reverse=True)[:5]
        
        # Count recent entries
        month_ago = now - timedelta(days=30)
        entries_this_week = len(recent_entries)
        entries_this_month = len([e for e in entries if e.entry_date and e.entry_date >= month_ago.strftime("%Y-%m-%d")])
        
        return {
            "total_entries": len(entries),
            "average_sentiment": round(avg_sentiment, 2),
            "sentiment_trend": trend,
            "most_common_tags": most_common,
            "average_stress_level": round(avg_stress, 1) if avg_stress else None,
            "average_sleep_quality": round(avg_sleep, 1) if avg_sleep else None,
            "entries_this_week": entries_this_week,
            "entries_this_month": entries_this_month
        }

    def export_entries(
        self,
        current_user: User,
        format: str = "json",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> str:
        """Export journal entries in specified format."""
        
        entries, _ = self.get_entries(
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
                    "tags": self._load_tags(e.tags),
                    "sleep_hours": e.sleep_hours,
                    "sleep_quality": e.sleep_quality,
                    "energy_level": e.energy_level,
                    "stress_level": e.stress_level
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
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Use 'json' or 'txt'"
            )


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
