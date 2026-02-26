"""Analytics service for aggregated, non-sensitive data analysis (Async)."""
from sqlalchemy import func, case, distinct, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, UTC

# Import models from root_models module
from ..root_models import Score, User, AnalyticsEvent


class AnalyticsService:
    """Service for generating aggregated analytics data.
    
    This service ONLY provides aggregated data and never exposes
    individual user information or raw sensitive data.
    """
    
    @staticmethod
    async def log_event(db: AsyncSession, event_data: dict, ip_address: Optional[str] = None) -> AnalyticsEvent:
        """
        Log a user behavior event.
        """
        import json
        
        # Serialize event_data JSON
        data_payload = json.dumps(event_data.get('event_data', {}))
        
        event = AnalyticsEvent(
            anonymous_id=event_data['anonymous_id'],
            event_type=event_data['event_type'],
            event_name=event_data['event_name'],
            event_data=data_payload,
            ip_address=ip_address,
            timestamp=datetime.now(UTC)
        )
        
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def get_age_group_statistics(db: AsyncSession) -> List[Dict]:
        """
        Get aggregated statistics by age group.
        
        Returns only aggregated data - no individual records.
        """
        stmt = select(
            Score.detailed_age_group,
            func.count(Score.id).label('total'),
            func.avg(Score.total_score).label('avg_score'),
            func.min(Score.total_score).label('min_score'),
            func.max(Score.total_score).label('max_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        ).filter(
            Score.detailed_age_group.isnot(None)
        ).group_by(
            Score.detailed_age_group
        )
        
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
        """
        Get score distribution across ranges.
        
        Returns aggregated distribution - no individual scores.
        """
        total_stmt = select(func.count(Score.id))
        total_result = await db.execute(total_stmt)
        total_count = total_result.scalar() or 0
        
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
        for range_name, min_score, max_score in ranges:
            range_stmt = select(func.count(Score.id)).filter(
                Score.total_score >= min_score,
                Score.total_score <= max_score
            )
            range_result = await db.execute(range_stmt)
            count = range_result.scalar() or 0
            
            percentage = (count / total_count * 100) if total_count > 0 else 0
            
            distribution.append({
                'score_range': range_name,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        return distribution
    
    @staticmethod
    async def get_overall_summary(db: AsyncSession) -> Dict:
        """
        Get overall analytics summary.
        
        Returns aggregated metrics only - no individual user data.
        """
        # Overall statistics
        overall_stmt = select(
            func.count(Score.id).label('total'),
            func.count(distinct(Score.username)).label('unique_users'),
            func.avg(Score.total_score).label('avg_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment')
        )
        overall_result = await db.execute(overall_stmt)
        overall_stats = overall_result.first()
        
        # Quality metrics (aggregated counts)
        quality_stmt = select(
            func.sum(case((Score.is_rushed == True, 1), else_=0)).label('rushed_count'),
            func.sum(case((Score.is_inconsistent == True, 1), else_=0)).label('inconsistent_count')
        )
        quality_result = await db.execute(quality_stmt)
        quality_metrics = quality_result.first()
        
        # Age group stats
        age_group_stats = await AnalyticsService.get_age_group_statistics(db)
        
        # Score distribution
        score_dist = await AnalyticsService.get_score_distribution(db)
        
        return {
            'total_assessments': overall_stats.total or 0,
            'unique_users': overall_stats.unique_users or 0,
            'global_average_score': round(overall_stats.avg_score or 0, 2),
            'global_average_sentiment': round(overall_stats.avg_sentiment or 0, 3),
            'age_group_stats': age_group_stats,
            'score_distribution': score_dist,
            'assessment_quality_metrics': {
                'rushed_assessments': quality_metrics.rushed_count or 0,
                'inconsistent_assessments': quality_metrics.inconsistent_count or 0
            }
        }
    
    @staticmethod
    async def get_trend_analytics(
        db: AsyncSession,
        period_type: str = 'monthly',
        limit: int = 12
    ) -> Dict:
        """
        Get trend analytics over time.
        
        Args:
            period_type: Type of period (daily, weekly, monthly)
            limit: Number of periods to return
            
        Returns aggregated time-series data.
        """
        # For simplicity, we'll do monthly trends
        # In production, you'd want more sophisticated date handling
        
        trend_stmt = select(
            func.substr(Score.timestamp, 1, 7).label('period'),  # YYYY-MM
            func.avg(Score.total_score).label('avg_score'),
            func.count(Score.id).label('count')
        ).group_by(
            func.substr(Score.timestamp, 1, 7)
        ).order_by(
            desc(func.substr(Score.timestamp, 1, 7))
        ).limit(limit)
        
        trend_result = await db.execute(trend_stmt)
        trends = trend_result.all()
        
        data_points = [
            {
                'period': t.period,
                'average_score': round(t.avg_score or 0, 2),
                'assessment_count': t.count
            }
            for t in reversed(trends)  # Chronological order
        ]
        
        # Determine trend direction
        if len(data_points) >= 2:
            first_avg = data_points[0]['average_score']
            last_avg = data_points[-1]['average_score']
            
            if last_avg > first_avg + 1:
                trend_direction = 'increasing'
            elif last_avg < first_avg - 1:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        return {
            'period_type': period_type,
            'data_points': data_points,
            'trend_direction': trend_direction
        }
    
    @staticmethod
    async def get_benchmark_comparison(db: AsyncSession) -> List[Dict]:
        """
        Get benchmark comparison data.
        
        Returns percentile-based benchmarks - no individual data.
        """
        # Get all scores for percentile calculation
        score_stmt = select(Score.total_score).filter(
            Score.total_score.isnot(None)
        ).order_by(Score.total_score)
        
        score_result = await db.execute(score_stmt)
        scores = score_result.scalars().all()
        
        if not scores:
            return []
        
        score_list = [float(s) for s in scores]
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
        """
        Get population-level insights.
        
        Returns aggregated population metrics - no individual data.
        """
        # Most common age group
        common_stmt = select(
            Score.detailed_age_group,
            func.count(Score.id).label('count')
        ).filter(
            Score.detailed_age_group.isnot(None)
        ).group_by(
            Score.detailed_age_group
        ).order_by(
            desc(func.count(Score.id))
        ).limit(1)
        
        common_result = await db.execute(common_stmt)
        most_common = common_result.first()
        
        # Highest performing age group
        highest_stmt = select(
            Score.detailed_age_group,
            func.avg(Score.total_score).label('avg')
        ).filter(
            Score.detailed_age_group.isnot(None)
        ).group_by(
            Score.detailed_age_group
        ).order_by(
            desc(func.avg(Score.total_score))
        ).limit(1)
        
        highest_result = await db.execute(highest_stmt)
        highest_performing = highest_result.first()
        
        # Total population
        users_stmt = select(func.count(distinct(Score.username)))
        users_result = await db.execute(users_stmt)
        total_users = users_result.scalar() or 0
        
        assess_stmt = select(func.count(Score.id))
        assess_result = await db.execute(assess_stmt)
        total_assessments = assess_result.scalar() or 0
        
        # Completion rate (simplified - assumes all scores are completed)
        completion_rate = 100.0 if total_assessments > 0 else None
        
        return {
            'most_common_age_group': most_common.detailed_age_group if most_common else 'Unknown',
            'highest_performing_age_group': highest_performing.detailed_age_group if highest_performing else 'Unknown',
            'total_population_size': total_users,
            'assessment_completion_rate': completion_rate
        }
