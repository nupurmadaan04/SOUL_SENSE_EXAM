"""Analytics service for aggregated, non-sensitive data analysis."""
from sqlalchemy import func, case, distinct
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

# Import models from models module
from ..models import Score, User, AnalyticsEvent


from sqlalchemy import select, func, case, distinct, desc
from sqlalchemy.ext.asyncio import AsyncSession

class AnalyticsService:
    """Service for generating aggregated analytics data.
    
    This service ONLY provides aggregated data and never exposes
    individual user information or raw sensitive data.
    """
    
    @staticmethod
    async def log_event(db: AsyncSession, event_data: dict, ip_address: Optional[str] = None) -> AnalyticsEvent:
        """Log event (Async)."""
        import json
        
        # Serialize event_data JSON
        data_payload = json.dumps(event_data.get('event_data', {}))
        
        event = AnalyticsEvent(
            anonymous_id=event_data['anonymous_id'],
            event_type=event_data['event_type'],
            event_name=event_data['event_name'],
            event_data=data_payload,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def get_age_group_statistics(db: AsyncSession) -> List[Dict]:
        """Age group stats (Async)."""
        stmt = select(
            Score.detailed_age_group,
            func.count(Score.id).label('total'),
            func.avg(Score.total_score).label('avg_score'),
            func.min(Score.total_score).label('min_score'),
            func.max(Score.total_score).label('max_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        ).filter(Score.detailed_age_group.isnot(None)).group_by(Score.detailed_age_group)
        result = await db.execute(stmt)
        stats = result.all()
        
        return [
            {
                'age_group': s.detailed_age_group,
                'total_assessments': s.total,
                'average_score': round(s.avg_score or 0, 2),
                'min_score': s.min_score or 0,
                'max_score': s.max_score or 0,
                'average_sentiment': round(s.avg_sentiment or 0, 3)
            }
            for s in stats
        ]
    
    @staticmethod
    async def get_score_distribution(db: AsyncSession) -> List[Dict]:
        """Score distribution (Async)."""
        total_count = (await db.execute(select(func.count(Score.id)))).scalar() or 0
        
        if total_count == 0:
            return []
        
        # Define score ranges
        ranges = [
            ('0-10', 0, 10),
            ('11-20', 11, 20),
            ('21-30', 21, 30),
            ('31-40', 31, 40)
        ]
        
        distribution = []
        for name, min_s, max_s in ranges:
            cnt = (await db.execute(select(func.count(Score.id)).filter(
                Score.total_score >= min_s,
                Score.total_score <= max_s
            ))).scalar() or 0
            
            percentage = (cnt / total_count * 100) if total_count > 0 else 0
            
            distribution.append({
                'score_range': name,
                'count': cnt,
                'percentage': round(percentage, 2)
            })
        
        return distribution
    
    @staticmethod
    async def get_overall_summary(db: AsyncSession) -> Dict:
        """Dashboard summary (Async)."""
        # Overall statistics
        overall = (await db.execute(select(
            func.count(Score.id).label('total'),
            func.count(distinct(Score.username)).label('unique_users'),
            func.avg(Score.total_score).label('avg_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        ))).first()
        
        # Quality metrics (aggregated counts)
        quality = (await db.execute(select(
            func.sum(case((Score.is_rushed == True, 1), else_=0)).label('rushed'),
            func.sum(case((Score.is_inconsistent == True, 1), else_=0)).label('inconsistent')
        ))).first()
        
        # Age group stats
        age_stats = await AnalyticsService.get_age_group_statistics(db)
        
        # Score distribution
        score_dist = await AnalyticsService.get_score_distribution(db)
        
        return {
            'total_assessments': overall.total or 0,
            'unique_users': overall.unique_users or 0,
            'global_average_score': round(overall.avg_score or 0, 2),
            'global_average_sentiment': round(overall.avg_sentiment or 0, 3),
            'age_group_stats': age_stats,
            'score_distribution': score_dist,
            'assessment_quality_metrics': {
                'rushed_assessments': quality.rushed or 0,
                'inconsistent_assessments': quality.inconsistent or 0
            }
        }
    
    @staticmethod
    async def get_trend_analytics(
        db: AsyncSession,
        period_type: str = 'monthly',
        limit: int = 12
    ) -> Dict:
        """Trend analytics (Async)."""
        # For simplicity, we'll do monthly trends
        # In production, you'd want more sophisticated date handling
        
        period_expr = func.substr(Score.timestamp, 1, 7) # YYYY-MM
        stmt = select(
            period_expr.label('period'),
            func.avg(Score.total_score).label('avg_score'),
            func.count(Score.id).label('count')
        ).group_by(
            period_expr
        ).order_by(
            period_expr.desc()
        ).limit(limit)
        result = await db.execute(stmt)
        trends = result.all()
        
        data_points = [
            {
                'period': t.period,
                'average_score': round(t.avg_score or 0, 2),
                'assessment_count': t.count
            }
            for t in reversed(trends)  # Chronological order
        ]
        
        # Determine trend direction
        trend_direction = 'stable'
        if len(data_points) >= 2:
            first_avg = data_points[0]['average_score']
            last_avg = data_points[-1]['average_score']
            
            if last_avg > first_avg + 1:
                trend_direction = 'increasing'
            elif last_avg < first_avg - 1:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
        
        return {
            'period_type': period_type,
            'data_points': data_points,
            'trend_direction': trend_direction
        }
    
    @staticmethod
    async def get_benchmark_comparison(db: AsyncSession) -> List[Dict]:
        """Benchmarks (Async)."""
        # Get all scores for percentile calculation
        stmt = select(Score.total_score).filter(
            Score.total_score.isnot(None)
        ).order_by(Score.total_score)
        result = await db.execute(stmt)
        scores = result.scalars().all()
        
        if not scores:
            return []
        
        score_list = list(scores)
        n = len(score_list)
        
        def percentile(p):
            """Calculate percentile value"""
            k = (n - 1) * p / 100
            f = int(k)
            c = min(f + 1, n - 1)
            if f == c:
                return score_list[f]
            return score_list[f] + (k - f) * (score_list[c] - score_list[f])
        
        global_avg = sum(score_list) / n if n > 0 else 0
        
        return [{
            'category': 'Overall',
            'global_average': round(global_avg, 2),
            'percentile_25': round(percentile(25), 2),
            'percentile_50': round(percentile(50), 2),
            'percentile_75': round(percentile(75), 2),
            'percentile_90': round(percentile(90), 2)
        }]
    
    @staticmethod
    async def get_population_insights(db: AsyncSession) -> Dict:
        """Population insights (Async)."""
        # Most common age group
        most_common = (await db.execute(select(
            Score.detailed_age_group,
            func.count(Score.id).label('count')
        ).filter(
            Score.detailed_age_group.isnot(None)
        ).group_by(
            Score.detailed_age_group
        ).order_by(
            desc('count')
        ))).first()
        
        # Highest performing age group
        highest_perf = (await db.execute(select(
            Score.detailed_age_group,
            func.avg(Score.total_score).label('avg')
        ).filter(
            Score.detailed_age_group.isnot(None)
        ).group_by(
            Score.detailed_age_group
        ).order_by(
            desc('avg')
        ))).first()
        
        # Total population
        total_users = (await db.execute(select(func.count(distinct(Score.username))))).scalar() or 0
        total_assessments = (await db.execute(select(func.count(Score.id)))).scalar() or 0
        
        # Completion rate (simplified - assumes all scores are completed)
        completion_rate = 100.0 if total_assessments > 0 else None
        
        return {
            'most_common_age_group': most_common.detailed_age_group if most_common else 'Unknown',
            'highest_performing_age_group': highest_perf.detailed_age_group if highest_perf else 'Unknown',
            'total_population_size': total_users,
            'assessment_completion_rate': completion_rate
        }
