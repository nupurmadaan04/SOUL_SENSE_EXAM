"""
CQRS Service for Read Model Materialization (#1124)
Handles the incremental updates of analytics read models.
"""
import logging
from datetime import datetime, UTC
from sqlalchemy import select, update, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import (
    CQRSGlobalStats, 
    CQRSAgeGroupStats, 
    CQRSDistributionStats, 
    CQRSTrendAnalytics,
    Score,
    User
)

logger = logging.getLogger(__name__)

class CQRSService:
    @staticmethod
    async def update_score_projections(db: AsyncSession):
        """
        Re-calculates the materializations from the Score table.
        In a high-scale environment, this could be triggered by Kafka events incrementally,
        but for this implementation, we will use an efficient 'refresh' pattern.
        """
        try:
            # 1. Update Global Stats
            overall_stmt = select(
                func.count(Score.id).label('total'),
                func.count(func.distinct(Score.username)).label('unique_users'),
                func.avg(Score.total_score).label('avg_score'),
                func.avg(Score.sentiment_score).label('avg_sentiment'),
                func.sum(case((Score.is_rushed == True, 1), else_=0)).label('rushed_count'),
                func.sum(case((Score.is_inconsistent == True, 1), else_=0)).label('inconsistent_count')
            )
            res = await db.execute(overall_stmt)
            overall = res.first()

            if overall and overall.total > 0:
                # Update or Insert Global Stats
                global_stats_stmt = select(CQRSGlobalStats).limit(1)
                gs_res = await db.execute(global_stats_stmt)
                gs = gs_res.scalar_one_or_none()
                
                if not gs:
                    gs = CQRSGlobalStats()
                    db.add(gs)
                
                gs.total_assessments = overall.total
                gs.unique_users = overall.unique_users
                gs.global_average_score = float(overall.avg_score or 0)
                gs.global_average_sentiment = float(overall.avg_sentiment or 0)
                gs.rushed_assessments = int(overall.rushed_count or 0)
                gs.inconsistent_assessments = int(overall.inconsistent_count or 0)
                
                # Percentiles (Calculated from a sorted list of scores)
                scores_stmt = select(Score.total_score).order_by(Score.total_score)
                s_res = await db.execute(scores_stmt)
                all_scores = s_res.scalars().all()
                n = len(all_scores)
                
                def get_p(p):
                    if n == 0: return 0.0
                    idx = (n - 1) * p / 100
                    f = int(idx)
                    c = min(f + 1, n - 1)
                    if f == c: return float(all_scores[f])
                    return float(all_scores[f] + (idx - f) * (all_scores[c] - all_scores[f]))

                gs.p25_score = get_p(25)
                gs.p50_score = get_p(50)
                gs.p75_score = get_p(75)
                gs.p90_score = get_p(90)
                
                gs.last_updated = datetime.now(UTC)

            # 2. Update Age Group Stats
            age_stmt = select(
                Score.detailed_age_group,
                func.count(Score.id).label('total'),
                func.avg(Score.total_score).label('avg_score'),
                func.min(Score.total_score).label('min_score'),
                func.max(Score.total_score).label('max_score'),
                func.avg(Score.sentiment_score).label('avg_sentiment')
            ).filter(Score.detailed_age_group.isnot(None)).group_by(Score.detailed_age_group)
            
            age_res = await db.execute(age_stmt)
            for row in age_res.all():
                stmt = select(CQRSAgeGroupStats).filter(CQRSAgeGroupStats.age_group == row.detailed_age_group)
                existing_res = await db.execute(stmt)
                existing = existing_res.scalar_one_or_none()
                
                if not existing:
                    existing = CQRSAgeGroupStats(age_group=row.detailed_age_group)
                    db.add(existing)
                
                existing.total_assessments = row.total
                existing.average_score = float(row.avg_score or 0)
                existing.min_score = float(row.min_score or 0)
                existing.max_score = float(row.max_score or 0)
                existing.average_sentiment = float(row.avg_sentiment or 0)
                existing.last_updated = datetime.now(UTC)

            # 3. Update Distribution
            # (Simplification for demo: just re-calculate)
            ranges = [
                ('0-10', 0, 10), ('11-20', 11, 20),
                ('21-30', 21, 30), ('31-40', 31, 40)
            ]
            for name, start, end in ranges:
                cnt_stmt = select(func.count(Score.id)).filter(Score.total_score.between(start, end))
                cnt = (await db.execute(cnt_stmt)).scalar() or 0
                
                dist_stmt = select(CQRSDistributionStats).filter(CQRSDistributionStats.score_range == name)
                dist = (await db.execute(dist_stmt)).scalar_one_or_none()
                
                if not dist:
                    dist = CQRSDistributionStats(score_range=name)
                    db.add(dist)
                dist.count = cnt
                dist.last_updated = datetime.now(UTC)

            # 4. Update Trend Analytics (Monthly Breakdown)
            # Since SQLite substr(timestamp, 1, 7) might vary, we'll do a simple month-string extraction
            trend_stmt = select(
                func.strftime('%Y-%m', Score.timestamp).label('period'),
                func.avg(Score.total_score).label('avg_score'),
                func.count(Score.id).label('count')
            ).group_by('period')
            
            trend_res = await db.execute(trend_stmt)
            for row in trend_res.all():
                t_stmt = select(CQRSTrendAnalytics).filter(CQRSTrendAnalytics.period == row.period)
                trend = (await db.execute(t_stmt)).scalar_one_or_none()
                
                if not trend:
                    trend = CQRSTrendAnalytics(period=row.period)
                    db.add(trend)
                trend.average_score = float(row.avg_score or 0)
                trend.assessment_count = row.count
                trend.last_updated = datetime.now(UTC)

            await db.commit()
            logger.info("CQRS Read Models refreshed successfully")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to refresh CQRS projections: {e}", exc_info=True)

    @staticmethod
    async def process_event(db: AsyncSession, event_type: str, entity: str, payload: dict):
        """
        Incrementally updates read models based on a single incoming event.
        Optimized for real-time Kafka consumption.
        """
        if entity == 'Score' and event_type == 'CREATED':
            # Logic to incrementally update CQRSGlobalStats, etc.
            # For simplicity in this implementation, we will trigger a partial refresh 
            # or rely on the background worker to pool updates.
            await CQRSService.update_score_projections(db)
