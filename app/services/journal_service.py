import logging
from typing import List, Optional, Any, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy import desc, asc
from app.db import safe_db_context
from app.models import JournalEntry, User, UserStreak
from app.exceptions import DatabaseError
from app.latency_budget import monitor_latency

logger = logging.getLogger(__name__)

class JournalService:
    """
    Service layer for handling Journal Entry operations.
    Decouples UI from direct Database access.
    """

    @staticmethod
    @monitor_latency(
        operation_name="journal_service.create_entry",
        budget_ms=1000,
        operation_type="command",
        alert_threshold_percent=75
    )
    def create_entry(
        username: str, 
        content: str, 
        sentiment_score: float, 
        emotional_patterns: str,
        entry_date: Optional[str] = None,
        **kwargs
    ) -> JournalEntry:
        """
        Creates and saves a new journal entry.
        
        Latency Budget: 1000ms (Command operation)
        Alert Threshold: 75% (750ms)
        
        Args:
            username: The user's username
            content: The text content of the entry
            sentiment_score: Calculated sentiment score
            emotional_patterns: Stringified emotional patterns/tags
            entry_date: Optional specific date (YYYY-MM-DD HH:MM:SS), defaults to now
            **kwargs: Additional fields (sleep_hours, stress_level, etc.)
            
        Returns:
            The created JournalEntry object (detached)
            
        Raises:
            DatabaseError: If the save fails
        """
        try:
            if not entry_date:
                entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with safe_db_context() as session:
                session.expire_on_commit = False
                entry = JournalEntry(
                    username=username,
                    content=content,
                    sentiment_score=sentiment_score,
                    emotional_patterns=emotional_patterns,
                    entry_date=entry_date,
                    **kwargs
                )
                session.add(entry)
                
                # Update streak
                try:
                    user = session.query(User).filter_by(username=username).first()
                    if user:
                        JournalService._update_streak(session, user.id, entry_date)
                except Exception as streak_err:
                    logger.warning(f"Failed to update streak for {username}: {streak_err}")

                # Commit is handled by safe_db_context
                
                # Refresh/Expunge to allow usage outside session if needed, 
                # but returning ID or simple DTO is often safer. 
                # For now, we rely on the fact that simple attributes are accessible.
                return entry
                
        except Exception as e:
            logger.error(f"Failed to create journal entry for {username}: {e}")
            raise DatabaseError("Failed to save journal entry", original_exception=e)

    @staticmethod
    @monitor_latency(
        operation_name="journal_service.get_entries",
        budget_ms=600,
        operation_type="query",
        alert_threshold_percent=80
    )
    def get_entries(
        username: str, 
        month_filter: Optional[str] = None, 
        type_filter: Optional[str] = None
    ) -> List[JournalEntry]:
        """
        Retrieves journal entries for a user with optional filters.
        
        Latency Budget: 600ms (Query operation)
        Alert Threshold: 80% (480ms)
        
        Args:
            username: The user's username
            month_filter: Optional "Month Year" string (e.g. "January 2024")
            type_filter: Optional filter string ("High Stress", "Great Days", etc.)
            
        Returns:
            List of JournalEntry objects
        """
        try:
            with safe_db_context() as session:
                query = session.query(JournalEntry)\
                    .filter_by(username=username)\
                    .filter(JournalEntry.is_deleted == False)\
                    .order_by(desc(JournalEntry.entry_date))
                
                session.expire_on_commit = False
                
                # Basic fetching - Logic for complex filters (Month/Type) 
                # is currently done in memory in the UI because of the 
                # nature of SQLite date strings and complex business logic.
                # Ideally, we would move that logic here.
                
                entries = query.all()
                
                # If we want to move filtering here later, we can.
                # For now, return all and let UI filter or implement basic filtering here.
                # Since the UI implementation was doing in-memory filtering, 
                # we'll return the full list or implement the filtering logic here 
                # if we want to be pure.
                
                # Let's return all and let the client filter for now to minimize risk 
                # of breaking the complex UI loop, BUT this is where we'd add 
                # server-side filtering logic in Phase 3.
                
                return entries
                
        except Exception as e:
            logger.error(f"Failed to retrieve journal entries for {username}: {e}")
            raise DatabaseError("Failed to retrieve journal history", original_exception=e)

    @staticmethod
    def get_recent_entries(username: str, days: int = 7) -> List[JournalEntry]:
        """
        Retrieves journal entries from the last N days.
        """
        try:
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with safe_db_context() as session:
                session.expire_on_commit = False
                entries = session.query(JournalEntry)\
                    .filter(JournalEntry.username == username)\
                    .filter(JournalEntry.entry_date >= start_date)\
                    .filter(JournalEntry.is_deleted == False)\
                    .order_by(desc(JournalEntry.entry_date))\
                    .all()
                return entries
        except Exception as e:
            logger.error(f"Failed to retrieve recent entries: {e}")
            return []
    @staticmethod
    def delete_entry(entry_id: int) -> bool:
        """
        Soft-delete a journal entry (Issue #1331).
        Sets is_deleted flag and records deletion timestamp.
        
        Args:
            entry_id: The ID of the entry to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with safe_db_context() as session:
                entry = session.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
                if not entry:
                    logger.warning(f"Entry {entry_id} not found")
                    return False
                
                entry.is_deleted = True
                entry.deleted_at = datetime.now()
                session.commit()
                logger.info(f"Entry {entry_id} soft-deleted successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {e}")
            return False

    # === TIMELINE METHODS FOR ISSUE #1324 ===

    @staticmethod
    def get_emotion_timeline(
        username: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        order: str = "desc"
    ) -> List[JournalEntry]:
        """
        Fetches user emotion logs sorted by timestamp for timeline visualization.
        
        Args:
            username: The user's username
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            order: "desc" for newest first (default), "asc" for oldest first
            
        Returns:
            List of JournalEntry objects sorted by timestamp
        """
        try:
            with safe_db_context() as session:
                session.expire_on_commit = False
                query = session.query(JournalEntry)\
                    .filter(JournalEntry.username == username)\
                    .filter(JournalEntry.is_deleted == False)
                
                # Apply date range filters
                if start_date:
                    query = query.filter(JournalEntry.entry_date >= start_date)
                if end_date:
                    query = query.filter(JournalEntry.entry_date <= end_date)
                
                # Sort by timestamp
                sort_order = desc(JournalEntry.entry_date) if order == "desc" else asc(JournalEntry.entry_date)
                entries = query.order_by(sort_order).all()
                
                return entries
        except Exception as e:
            logger.error(f"Failed to retrieve emotion timeline for {username}: {e}")
            raise DatabaseError("Failed to retrieve emotion timeline", original_exception=e)

    @staticmethod
    def get_timeline_grouped_by_period(
        username: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, List[JournalEntry]]:
        """
        Groups emotion entries by time period for timeline visualization.
        
        Args:
            username: The user's username
            period: "daily", "weekly", or "monthly"
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            Dictionary with period keys and lists of JournalEntry objects
            Example: {"2025-01-15": [entry1, entry2], "2025-01-16": [entry3]}
        """
        try:
            entries = JournalService.get_emotion_timeline(
                username, start_date, end_date, order="asc"
            )
            
            grouped = {}
            
            for entry in entries:
                # Parse entry_date timestamp
                entry_dt = datetime.strptime(entry.entry_date, "%Y-%m-%d %H:%M:%S")
                
                if period == "daily":
                    key = entry_dt.strftime("%Y-%m-%d")
                elif period == "weekly":
                    # ISO week format: YYYY-Www (e.g., 2025-W03)
                    key = entry_dt.strftime("%Y-W%V")
                elif period == "monthly":
                    key = entry_dt.strftime("%Y-%m")
                else:
                    key = entry_dt.strftime("%Y-%m-%d")  # Default to daily
                
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(entry)
            
            return grouped
        except Exception as e:
            logger.error(f"Failed to group timeline entries for {username}: {e}")
            raise DatabaseError("Failed to group timeline entries", original_exception=e)

    @staticmethod
    def get_timeline_paginated(
        username: str,
        page: int = 1,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[List[JournalEntry], int, int]:
        """
        Retrieves paginated emotion entries for timeline with pagination support.
        
        Args:
            username: The user's username
            page: Page number (1-indexed)
            limit: Number of entries per page (default 20)
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            Tuple of (entries_list, total_count, total_pages)
        """
        try:
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20
            
            with safe_db_context() as session:
                session.expire_on_commit = False
                query = session.query(JournalEntry)\
                    .filter(JournalEntry.username == username)\
                    .filter(JournalEntry.is_deleted == False)
                
                # Apply date range filters
                if start_date:
                    query = query.filter(JournalEntry.entry_date >= start_date)
                if end_date:
                    query = query.filter(JournalEntry.entry_date <= end_date)
                
                # Get total count before pagination
                total_count = query.count()
                total_pages = (total_count + limit - 1) // limit  # Ceiling division
                
                # Apply pagination
                offset = (page - 1) * limit
                entries = query.order_by(desc(JournalEntry.entry_date))\
                    .offset(offset)\
                    .limit(limit)\
                    .all()
                
                return entries, total_count, total_pages
        except Exception as e:
            logger.error(f"Failed to retrieve paginated timeline for {username}: {e}")
            raise DatabaseError("Failed to retrieve paginated timeline", original_exception=e)

    @staticmethod
    def get_emotion_trends(
        username: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily"
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculates emotion trends (average mood, sentiment) for graph visualization.
        
        Args:
            username: The user's username
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            period: "daily", "weekly", or "monthly"
            
        Returns:
            Dictionary with trend data for each period
            Example: {"2025-01-15": {"avg_mood": 7.2, "sentiment": 0.35, "count": 3}}
        """
        try:
            grouped = JournalService.get_timeline_grouped_by_period(
                username, period, start_date, end_date
            )
            
            trends = {}
            
            for period_key, entries in grouped.items():
                if not entries:
                    continue
                
                # Calculate averages
                moods = [e.mood_score for e in entries if e.mood_score is not None]
                sentiments = [e.sentiment_score for e in entries if e.sentiment_score is not None]
                energy_levels = [e.energy_level for e in entries if e.energy_level is not None]
                stress_levels = [e.stress_level for e in entries if e.stress_level is not None]
                
                trends[period_key] = {
                    "avg_mood": sum(moods) / len(moods) if moods else 0,
                    "avg_sentiment": sum(sentiments) / len(sentiments) if sentiments else 0,
                    "avg_energy": sum(energy_levels) / len(energy_levels) if energy_levels else 0,
                    "avg_stress": sum(stress_levels) / len(stress_levels) if stress_levels else 0,
                    "entry_count": len(entries)
                }
            
            return trends
        except Exception as e:
            logger.error(f"Failed to calculate emotion trends for {username}: {e}")
            raise DatabaseError("Failed to calculate emotion trends", original_exception=e)

    @staticmethod
    def _update_streak(session, user_id: int, entry_date_str: str):
        """
        Internal logic to update user journal streak using the UserStreak model.
        
        Args:
            session: SQLAlchemy session
            user_id: ID of the user
            entry_date_str: Date of the entry (YYYY-MM-DD HH:MM:SS)
        """
        try:
            # Parse entry date (ignoring time for streak calculation)
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d %H:%M:%S").date()
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)

            # Get or create streak record for journal activity
            streak_record = session.query(UserStreak).filter_by(
                user_id=user_id, 
                activity_type='journal'
            ).first()

            if not streak_record:
                streak_record = UserStreak(
                    user_id=user_id,
                    activity_type='journal',
                    current_streak=1,
                    longest_streak=1,
                    last_activity_date=datetime.combine(entry_date, datetime.min.time())
                )
                session.add(streak_record)
                return

            if streak_record.last_activity_date:
                last_date = streak_record.last_activity_date.date()
                
                # If already recorded for this day, do nothing
                if last_date == entry_date:
                    return

                # If it's consecutive (e.g., last was yesterday and entry is today)
                if last_date == entry_date - timedelta(days=1):
                    streak_record.current_streak += 1
                # If there's a gap (except if entering a past date that doesn't break the current "today" streak)
                elif entry_date > last_date + timedelta(days=1):
                    streak_record.current_streak = 1
                # If entry is in the past, we don't necessarily reset the current forward streak,
                # but for simplicity in this version, any non-consecutive forward entry resets.
                # If entry_date is before last_date, we just ignore it for streak increment.
                elif entry_date < last_date:
                    return

            else:
                streak_record.current_streak = 1

            # Update last activity and longest streak
            streak_record.last_activity_date = datetime.combine(entry_date, datetime.min.time())
            if streak_record.current_streak > streak_record.longest_streak:
                streak_record.longest_streak = streak_record.current_streak

        except Exception as e:
            logger.error(f"Error in _update_streak: {e}")
            # Don't raise, as streak update shouldn't break the main flow

