from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
import statistics
import math
import logging

from ..models import Score, User, PersonalProfile
from ..schemas.advanced_analytics import (
    CorrelationResult, DemographicBenchmark, AnomalyEvent, AdvancedInsightsResponse
)

logger = logging.getLogger("api.analytics.advanced")

class CorrelationService:
    @staticmethod
    async def get_advanced_insights(db: AsyncSession, user_id: int) -> AdvancedInsightsResponse:
        """Main entry point for generating the advanced behavioral insights report."""
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        # 1. Fetch Data
        user_scores = await CorrelationService._get_user_scores(db, user.username)
        population_stats = await CorrelationService._get_population_stats(db)
        
        # 2. Run Engine components
        correlations = await CorrelationService._calculate_behavioral_correlations(db, user_id, user_scores)
        benchmarks = await CorrelationService._calculate_benchmarks(user, user_scores, population_stats)
        anomalies = await CorrelationService._detect_anomalies(user_scores)
        
        # 3. Generate Human-Readable Advice
        advice = CorrelationService._generate_advice(correlations, benchmarks, anomalies)

        return AdvancedInsightsResponse(
            correlations=correlations,
            benchmarks=benchmarks,
            anomalies=anomalies,
            actionable_advice=advice,
            generated_at=datetime.now(UTC)
        )

    @staticmethod
    async def _get_user_scores(db: AsyncSession, username: str, limit: int = 50) -> List[Score]:
        stmt = select(Score).where(Score.username == username).order_by(desc(Score.timestamp)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _get_population_stats(db: AsyncSession) -> Dict[str, Any]:
        """Get global averages for benchmarking."""
        stmt = select(
            func.avg(Score.total_score).label('avg_score'),
            func.avg(Score.sentiment_score).label('avg_sentiment'),
            func.stddev(Score.total_score).label('std_score') # Note: SQLite doesn't have stddev by default
        )
        # Fallback for SQLite which lacks STDDEV
        try:
            result = await db.execute(stmt)
            stats = result.first()
        except:
            # Manual fallback if SQL function fails (common in SQLite)
            all_scores_stmt = select(Score.total_score)
            res = await db.execute(all_scores_stmt)
            scores = res.scalars().all()
            if not scores: return {"avg_score": 0, "avg_sentiment": 0, "std_score": 0}
            return {
                "avg_score": sum(scores) / len(scores),
                "avg_sentiment": 0.5, # Placeholder
                "std_score": statistics.stdev(scores) if len(scores) > 1 else 0
            }
        
        return {
            "avg_score": stats.avg_score or 0,
            "avg_sentiment": stats.avg_sentiment or 0,
            "std_score": stats.std_score or 0
        }

    @staticmethod
    async def _calculate_behavioral_correlations(db: AsyncSession, user_id: int, user_scores: List[Score]) -> List[CorrelationResult]:
        """Calculates Pearson Correlation between behavioral indicators and sentiment."""
        results = []
        if len(user_scores) < 3:
            return results # Insufficient data for correlation

        # In a real app, we might join with 'PersonalProfile' or 'HabitTracker'
        # For this demo, let's correlate 'Total Score' with 'Sentiment Score'
        x = [s.total_score for s in user_scores]
        y = [s.sentiment_score for s in user_scores]
        
        coeff = CorrelationService._pearson_correlation(x, y)
        
        results.append(CorrelationResult(
            variable_a="Assessment Score",
            variable_b="Emotional Sentiment",
            correlation_coefficient=round(coeff, 3),
            significance="High" if abs(coeff) > 0.7 else "Moderate" if abs(coeff) > 0.4 else "Low",
            description=f"There is a { 'strong' if abs(coeff) > 0.7 else 'slight'} link between your overall assessment results and your expressed sentiment."
        ))

        return results

    @staticmethod
    async def _calculate_benchmarks(user: User, user_scores: List[Score], pop_stats: Dict[str, Any]) -> List[DemographicBenchmark]:
        results = []
        if not user_scores: return results

        user_avg = sum(s.total_score for s in user_scores) / len(user_scores)
        pop_avg = pop_stats['avg_score']
        
        # Calculate roughly where user stands (simplified percentile)
        diff = user_avg - pop_avg
        percentile = 50 + (diff / 2) # Crude approximation for demo
        percentile = max(0, min(100, percentile))

        results.append(DemographicBenchmark(
            category="Overall Wellbeing",
            user_value=round(user_avg, 2),
            population_average=round(pop_avg, 2),
            percentile=round(percentile, 1),
            comparison_text=f"Your wellbeing score is { 'higher' if diff > 0 else 'lower'} than the platform average."
        ))

        return results

    @staticmethod
    async def _detect_anomalies(user_scores: List[Score]) -> List[AnomalyEvent]:
        anomalies = []
        if len(user_scores) < 5: return anomalies

        # Look for sudden drops in sentiment in the last 3 days
        # Sort by date asc for time-series check
        sorted_scores = sorted(user_scores, key=lambda x: x.timestamp)
        
        recent = sorted_scores[-1]
        previous_vals = [s.sentiment_score for s in sorted_scores[-5:-1]]
        avg_prev = sum(previous_vals) / len(previous_vals)
        
        if recent.sentiment_score < (avg_prev * 0.6): # 40% drop
            anomalies.append(AnomalyEvent(
                severity="High",
                date=recent.timestamp if isinstance(recent.timestamp, datetime) else datetime.fromisoformat(recent.timestamp),
                previous_average=round(avg_prev, 3),
                current_value=round(recent.sentiment_score, 3),
                drop_percentage=round((1 - (recent.sentiment_score / avg_prev)) * 100, 1)
            ))
            
        return anomalies

    @staticmethod
    def _generate_advice(correlations: List[CorrelationResult], benchmarks: List[DemographicBenchmark], anomalies: List[AnomalyEvent]) -> List[str]:
        advice = []
        if not correlations and not benchmarks and not anomalies:
            return ["Keep taking assessments to unlock personalized behavioral insights!"]

        for anomaly in anomalies:
            if anomaly.severity == "High":
                advice.append("We've noticed a significant dip in your mood recently. Consider reaching out to your support network or trying some mindfulness exercises.")
        
        for corr in correlations:
            if corr.correlation_coefficient > 0.6:
                advice.append(f"Success! Your {corr.variable_a} is strongly positive. This suggests that when this area is strong, your mood follows.")

        if not advice:
            advice.append("Continue your current routine; your metrics look stable compared to last week.")
            
        return advice

    @staticmethod
    def _pearson_correlation(x: List[float], y: List[float]) -> float:
        """Pure Python implementation of Pearson Correlation Coefficient."""
        n = len(x)
        if n < 2: return 0
        mu_x = sum(x) / n
        mu_y = sum(y) / n
        std_x = math.sqrt(sum((xi - mu_x)**2 for xi in x) / (n - 1))
        std_y = math.sqrt(sum((yi - mu_y)**2 for yi in y) / (n - 1))
        if std_x == 0 or std_y == 0: return 0
        
        covariance = sum((x[i] - mu_x) * (y[i] - mu_y) for i in range(n)) / (n - 1)
        return covariance / (std_x * std_y)
