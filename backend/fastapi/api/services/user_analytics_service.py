from datetime import datetime, timedelta, UTC
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models import Score, JournalEntry
from ..schemas import (
    UserAnalyticsSummary,
    EQScorePoint,
    WellbeingPoint,
    UserTrendsResponse
)

class UserAnalyticsService:
    @classmethod
    def get_dashboard_summary(cls, db: Session, user_id: int) -> UserAnalyticsSummary:
        """
        Calculate headline stats for the user dashboard.
        Handles edge cases like zero data gracefully.
        """
        # 1. Basic Aggregates
        stats = db.query(
            func.count(Score.id),
            func.avg(Score.total_score),
            func.max(Score.total_score)
        ).filter(Score.user_id == user_id).first()
        
        total_exams = stats[0] or 0
        average_score = float(stats[1]) if stats[1] is not None else 0.0
        best_score = stats[2] or 0
        
        # 2. Latest Score
        latest_exam = db.query(Score).filter(
            Score.user_id == user_id
        ).order_by(Score.id.desc()).first()
        
        latest_score = latest_exam.total_score if latest_exam else 0
        
        # 3. Consistency Score (Coefficient of Variation)
        # CV = (StdDev / Mean) * 100. Lower is more consistent.
        consistency_score = None
        if total_exams >= 2 and average_score > 0:
            # Check if database supports stddev, otherwise calc in python
            # SQLite doesn't strictly support STDDEV in all versions, 
            # so we fetch scores to be safe and portable.
            scores = db.query(Score.total_score).filter(Score.user_id == user_id).all()
            score_values = [s[0] for s in scores]
            
            import statistics
            if len(score_values) > 1:
                stdev = statistics.stdev(score_values)
                consistency_score = (stdev / average_score) * 100
        
        # 4. Sentiment Trend (Slope of last 5)
        sentiment_trend = "stable"
        if total_exams >= 3:
            recent_scores = db.query(Score.total_score).filter(
                Score.user_id == user_id
            ).order_by(Score.id.desc()).limit(5).all()
            
            # Reverse to chronological order [oldest ... newest]
            recent_values = [s[0] for s in recent_scores][::-1]
            
            if len(recent_values) >= 2:
                # Simple rise/fall check
                delta = recent_values[-1] - recent_values[0]
                if delta > 5:
                    sentiment_trend = "improving"
                elif delta < -5:
                    sentiment_trend = "declining"
                    
        # 5. Streak (Consecutive days with activity)
        # Using Journal or Exams
        streak_days = 0 
        # (Simplified streak logic: check last login or just hardcode 0 for now as specified in plan)
        # A real implementation would require complex date queries.
        
        return UserAnalyticsSummary(
            total_exams=total_exams,
            average_score=round(average_score, 1),
            best_score=best_score,
            latest_score=latest_score,
            sentiment_trend=sentiment_trend,
            streak_days=streak_days,
            consistency_score=round(consistency_score, 1) if consistency_score is not None else None
        )

    @classmethod
    def get_eq_trends(cls, db: Session, user_id: int, days: int = 30) -> List[EQScorePoint]:
        """
        Get EQ score history for charting.
        """
        # Calculate cut-off date
        cutoff = datetime.now(UTC) - timedelta(days=days)
        
        scores = db.query(Score).filter(
            Score.user_id == user_id,
            Score.timestamp >= cutoff.isoformat()
        ).order_by(Score.timestamp.asc()).all()
        
        return [
            EQScorePoint(
                id=s.id,
                timestamp=s.timestamp, # Assumes already ISO string in DB
                total_score=s.total_score,
                sentiment_score=s.sentiment_score
            )
            for s in scores
        ]

    @classmethod
    def get_wellbeing_trends(cls, db: Session, user_id: int, days: int = 30) -> List[WellbeingPoint]:
        """
        Get wellbeing metrics from Journal (Sleep, Stress, Energy).
        Handles sparse data by returning None for missing fields.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        # ISO format textual comparison works for YYYY-MM-DD
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        entries = db.query(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= cutoff_str
        ).order_by(JournalEntry.entry_date.asc()).all()
        
        points = []
        for entry in entries:
            # entry_date might be "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
            # Normalize to YYYY-MM-DD for chart
            date_str = entry.entry_date.split(" ")[0]
            
            points.append(WellbeingPoint(
                date=date_str,
                sleep_hours=entry.sleep_hours,
                stress_level=entry.stress_level,
                energy_level=entry.energy_level,
                screen_time_mins=entry.screen_time_mins
            ))
            
        return points
