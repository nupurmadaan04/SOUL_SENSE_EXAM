from datetime import datetime, timedelta, UTC
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..models import Score, JournalEntry
from ..schemas import (
    UserAnalyticsSummary,
    EQScorePoint,
    WellbeingPoint,
    UserTrendsResponse
)

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

class UserAnalyticsService:
    @classmethod
    async def get_dashboard_summary(cls, db: AsyncSession, user_id: int) -> UserAnalyticsSummary:
        """Dashboard summary (Async)."""
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
        
        stmt_latest = select(Score).filter(Score.user_id == user_id).order_by(Score.id.desc())
        latest_exam = (await db.execute(stmt_latest)).scalar_one_or_none()
        latest_score = latest_exam.total_score if latest_exam else 0
        
        consistency_score = None
        if total_exams >= 2 and average_score > 0:
            stmt_scores = select(Score.total_score).filter(Score.user_id == user_id)
            scores = (await db.execute(stmt_scores)).scalars().all()
            score_values = list(scores)
            
            import statistics
            if len(score_values) > 1:
                stdev = statistics.stdev(score_values)
                consistency_score = (stdev / average_score) * 100
        
        sentiment_trend = "stable"
        if total_exams >= 3:
            stmt_recent = select(Score.total_score).filter(Score.user_id == user_id).order_by(Score.id.desc()).limit(5)
            recent_scores = (await db.execute(stmt_recent)).scalars().all()
            recent_values = list(recent_scores)[::-1]
            
            if len(recent_values) >= 2:
                delta = recent_values[-1] - recent_values[0]
                if delta > 5: sentiment_trend = "improving"
                elif delta < -5: sentiment_trend = "declining"
                    
        return UserAnalyticsSummary(
            total_exams=total_exams,
            average_score=round(average_score, 1),
            best_score=best_score,
            latest_score=latest_score,
            sentiment_trend=sentiment_trend,
            streak_days=0,
            consistency_score=round(consistency_score, 1) if consistency_score is not None else None
        )

    @classmethod
    async def get_eq_trends(cls, db: AsyncSession, user_id: int, days: int = 30) -> List[EQScorePoint]:
        """EQ trends (Async)."""
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
                timestamp=s.timestamp,
                total_score=s.total_score,
                sentiment_score=s.sentiment_score
            )
            for s in scores
        ]

    @classmethod
    async def get_wellbeing_trends(cls, db: AsyncSession, user_id: int, days: int = 30) -> List[WellbeingPoint]:
        """Wellbeing trends (Async)."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= cutoff_str
        ).order_by(JournalEntry.entry_date.asc())
        result = await db.execute(stmt)
        entries = result.scalars().all()
        
        points = []
        for entry in entries:
            date_str = entry.entry_date.split(" ")[0]
            points.append(WellbeingPoint(
                date=date_str,
                sleep_hours=entry.sleep_hours,
                stress_level=entry.stress_level,
                energy_level=entry.energy_level,
                screen_time_mins=entry.screen_time_mins
            ))
        return points
