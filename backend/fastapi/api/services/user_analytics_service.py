from datetime import datetime, timedelta, UTC
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select

from app.models import Score, JournalEntry
from ..schemas import (
    UserAnalyticsSummary,
    EQScorePoint,
    WellbeingPoint,
    UserTrendsResponse
)

class UserAnalyticsService:
    @classmethod
    async def get_dashboard_summary(cls, db: AsyncSession, user_id: int) -> UserAnalyticsSummary:
        """
        Calculate headline stats for the user dashboard.
        Handles edge cases like zero data gracefully.
        """
        # 1. Basic Aggregates
        stmt = select(
            func.count(Score.id),
            func.avg(Score.total_score),
            func.max(Score.total_score)
        ).filter(Score.user_id == user_id)
        
        result = await db.execute(stmt)
        stats = result.first()
        
        total_exams = stats[0] or 0
        average_score = float(stats[1]) if stats[1] is not None else 0.0
        best_score = stats[2] or 0
        
        # 2. Latest Score
        latest_stmt = select(Score).filter(
            Score.user_id == user_id
        ).order_by(Score.id.desc()).limit(1)
        
        latest_result = await db.execute(latest_stmt)
        latest_exam = latest_result.scalar_one_or_none()
        
        latest_score = latest_exam.total_score if latest_exam else 0
        
        # 3. Consistency Score (Coefficient of Variation)
        consistency_score = None
        if total_exams >= 2 and average_score > 0:
            scores_stmt = select(Score.total_score).filter(Score.user_id == user_id)
            scores_result = await db.execute(scores_stmt)
            score_values = scores_result.scalars().all()
            
            import statistics
            if len(score_values) > 1:
                stdev = statistics.stdev([float(s) for s in score_values])
                consistency_score = (stdev / average_score) * 100
        
        # 4. Sentiment Trend (Slope of last 5)
        sentiment_trend = "stable"
        if total_exams >= 3:
            recent_stmt = select(Score.total_score).filter(
                Score.user_id == user_id
            ).order_by(Score.id.desc()).limit(5)
            
            recent_result = await db.execute(recent_stmt)
            recent_scores = recent_result.scalars().all()
            
            # Reverse to chronological order [oldest ... newest]
            recent_values = [float(s) for s in recent_scores][::-1]
            
            if len(recent_values) >= 2:
                # Simple rise/fall check
                delta = recent_values[-1] - recent_values[0]
                if delta > 5:
                    sentiment_trend = "improving"
                elif delta < -5:
                    sentiment_trend = "declining"
                    
        # 5. Streak (Consecutive days with activity)
        streak_days = 0 
        
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
    async def get_eq_trends(cls, db: AsyncSession, user_id: int, days: int = 30) -> List[EQScorePoint]:
        """
        Get EQ score history for charting.
        """
        # Calculate cut-off date
        cutoff = datetime.now(UTC) - timedelta(days=days)
        
        stmt = select(Score).filter(
            Score.user_id == user_id,
            Score.timestamp >= cutoff.isoformat()
        ).order_by(Score.timestamp.asc())
        
        result = await db.execute(stmt)
        scores = result.scalars().all()
        
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
    async def get_wellbeing_trends(cls, db: AsyncSession, user_id: int, days: int = 30) -> List[WellbeingPoint]:
        """
        Get wellbeing metrics from Journal (Sleep, Stress, Energy).
        Handles sparse data by returning None for missing fields.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        # ISO format textual comparison works for YYYY-MM-DD
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= cutoff_str
        ).order_by(JournalEntry.entry_date.asc())
        
        result = await db.execute(stmt)
        entries = result.scalars().all()
        
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
