"""
Advanced Analytics Service for Emotional Pattern Recognition.

This service provides high-level analytics combining pattern recognition,
recommendations, and forecasting capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from app.db import safe_db_context
from app.models import Score, JournalEntry, User
from .pattern_recognition import PatternRecognitionService
from .recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Comprehensive analytics service for emotional wellbeing."""

    def __init__(self):
        """Initialize the analytics service."""
        self.pattern_service = PatternRecognitionService()
        self.recommendation_engine = RecommendationEngine()

    def get_emotional_forecast(self, username: str, days: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive emotional forecast.

        Args:
            username: Username to forecast for
            days: Number of days to forecast

        Returns:
            Dictionary containing forecast data and insights
        """
        try:
            # Get mood predictions
            mood_forecast = self.pattern_service.predict_mood(username, days)

            # Get pattern insights
            patterns = self.pattern_service.detect_temporal_patterns(username)

            # Generate forecast insights
            forecast_insights = self._generate_forecast_insights(
                mood_forecast.get("predictions", []),
                patterns.get("patterns", [])
            )

            return {
                "forecast": mood_forecast,
                "patterns": patterns,
                "insights": forecast_insights,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting emotional forecast for {username}: {e}")
            return {"forecast": {}, "error": str(e)}

    def get_correlation_matrix(self, username: str, metrics: List[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive correlation analysis.

        Args:
            username: Username to analyze
            metrics: Optional list of metrics to include

        Returns:
            Dictionary containing correlation matrix and insights
        """
        try:
            correlations = self.pattern_service.find_correlations(username, metrics)

            # Enhance with insights
            correlation_insights = self._analyze_correlation_insights(
                correlations.get("significant_correlations", [])
            )

            return {
                "correlations": correlations,
                "insights": correlation_insights,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting correlation matrix for {username}: {e}")
            return {"correlations": {}, "error": str(e)}

    def get_comparative_benchmarks(self, username: str, age_group: str = None) -> Dict[str, Any]:
        """
        Get comparative benchmarks (opt-in feature).

        Args:
            username: Username to benchmark
            age_group: Optional age group filter

        Returns:
            Dictionary containing benchmark comparisons
        """
        try:
            with safe_db_context() as session:
                # Get user's scores
                user_scores = session.query(Score).filter(Score.username == username).all()

                if not user_scores:
                    return {"benchmarks": [], "message": "No user scores available"}

                user_avg = np.mean([s.total_score for s in user_scores])

                # Get population statistics
                population_stats = self._calculate_population_stats(session, age_group)

                # Calculate percentiles
                user_percentile = self._calculate_percentile(user_avg, population_stats)

                benchmarks = {
                    "user_average": round(user_avg, 1),
                    "population_average": population_stats.get("mean", 0),
                    "user_percentile": user_percentile,
                    "percentiles": population_stats.get("percentiles", {}),
                    "comparison_group": age_group or "all_users",
                    "sample_size": population_stats.get("count", 0)
                }

                # Generate benchmark insights
                insights = self._generate_benchmark_insights(benchmarks)

                return {
                    "benchmarks": benchmarks,
                    "insights": insights,
                    "generated_at": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting comparative benchmarks for {username}: {e}")
            return {"benchmarks": {}, "error": str(e)}

    def get_personalized_recommendations(self, username: str) -> Dict[str, Any]:
        """
        Get comprehensive personalized recommendations.

        Args:
            username: Username to generate recommendations for

        Returns:
            Dictionary containing recommendations and insights
        """
        try:
            # Generate insights
            insights = self.recommendation_engine.generate_insights(username)

            # Get current risk level
            risk_level = self._assess_risk_level(username)

            # Get interventions
            interventions = self.recommendation_engine.suggest_interventions(username, risk_level)

            # Get personalized prompts
            trends = self.pattern_service.detect_temporal_patterns(username).get("patterns", [])
            prompts = self.recommendation_engine.create_personalized_prompts(username, trends)

            return {
                "insights": insights,
                "interventions": interventions,
                "journal_prompts": prompts,
                "risk_level": risk_level,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting personalized recommendations for {username}: {e}")
            return {"insights": {}, "error": str(e)}

    def get_analytics_dashboard(self, username: str) -> Dict[str, Any]:
        """
        Get complete analytics dashboard data.

        Args:
            username: Username to get dashboard for

        Returns:
            Dictionary containing all dashboard analytics
        """
        try:
            # Get all analytics components
            forecast = self.get_emotional_forecast(username)
            correlations = self.get_correlation_matrix(username)
            recommendations = self.get_personalized_recommendations(username)

            # Get patterns summary
            patterns = self.pattern_service.detect_temporal_patterns(username)

            # Get triggers summary
            triggers = self.pattern_service.identify_triggers(username)

            return {
                "forecast": forecast,
                "correlations": correlations,
                "recommendations": recommendations,
                "patterns": patterns,
                "triggers": triggers,
                "dashboard_generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting analytics dashboard for {username}: {e}")
            return {"dashboard": {}, "error": str(e)}

    def _generate_forecast_insights(self, predictions: List[Dict], patterns: List[Dict]) -> List[Dict[str, Any]]:
        """Generate insights from forecast data."""
        insights = []

        if not predictions:
            return insights

        # Analyze forecast trend
        scores = [p.get("predicted_score", 0) for p in predictions]
        if len(scores) >= 2:
            trend = scores[-1] - scores[0]
            if abs(trend) > 5:
                direction = "improving" if trend > 0 else "declining"
                insights.append({
                    "type": "forecast_trend",
                    "title": f"Forecast Trend: {direction.title()}",
                    "description": f"Your predicted emotional scores show a {direction} trend over the next {len(predictions)} days.",
                    "recommendation": "Monitor your activities and adjust as needed to influence this trend.",
                    "confidence": 0.7
                })

        # Check for concerning predictions
        low_scores = [p for p in predictions if p.get("predicted_score", 100) < 40]
        if low_scores:
            insights.append({
                "type": "forecast_concern",
                "title": "Potential Low Periods Ahead",
                "description": f"Forecast indicates {len(low_scores)} days with potentially low emotional scores.",
                "recommendation": "Consider proactive stress management and reach out to support networks.",
                "confidence": 0.6,
                "priority": "medium"
            })

        return insights

    def _analyze_correlation_insights(self, significant_correlations: List[Dict]) -> List[Dict[str, Any]]:
        """Generate insights from correlation analysis."""
        insights = []

        for corr in significant_correlations:
            metric1 = corr.get("metric1", "")
            metric2 = corr.get("metric2", "")
            correlation = corr.get("correlation", 0)
            strength = corr.get("strength", "")

            if strength in ["strong", "moderate"]:
                if metric1 == "eq_score" and metric2 == "sleep_hours":
                    if correlation > 0:
                        insights.append({
                            "type": "correlation_insight",
                            "title": "Sleep Quality Matters",
                            "description": f"Sleep quality shows a {strength} positive correlation with your EQ scores.",
                            "recommendation": "Prioritize good sleep hygiene to support emotional intelligence.",
                            "impact": "high"
                        })
                    else:
                        insights.append({
                            "type": "correlation_insight",
                            "title": "Sleep May Need Attention",
                            "description": f"Poor sleep quality correlates with lower EQ scores.",
                            "recommendation": "Address sleep issues to potentially improve emotional wellbeing.",
                            "impact": "high"
                        })

        return insights

    def _calculate_population_stats(self, session, age_group: str = None) -> Dict[str, Any]:
        """Calculate population statistics for benchmarking."""
        query = session.query(Score.total_score)

        if age_group:
            # This would need age group logic - simplified for now
            pass

        scores = [s[0] for s in query.all()]

        if not scores:
            return {"mean": 0, "count": 0, "percentiles": {}}

        stats = {
            "mean": np.mean(scores),
            "count": len(scores),
            "std": np.std(scores),
            "percentiles": {
                "25th": np.percentile(scores, 25),
                "50th": np.percentile(scores, 50),
                "75th": np.percentile(scores, 75),
                "90th": np.percentile(scores, 90)
            }
        }

        return stats

    def _calculate_percentile(self, user_score: float, population_stats: Dict) -> int:
        """Calculate user's percentile ranking."""
        percentiles = population_stats.get("percentiles", {})

        if user_score >= percentiles.get("90th", 0):
            return 90
        elif user_score >= percentiles.get("75th", 0):
            return 75
        elif user_score >= percentiles.get("50th", 0):
            return 50
        elif user_score >= percentiles.get("25th", 0):
            return 25
        else:
            return 10

    def _generate_benchmark_insights(self, benchmarks: Dict) -> List[Dict[str, Any]]:
        """Generate insights from benchmark data."""
        insights = []

        user_percentile = benchmarks.get("user_percentile", 50)
        population_avg = benchmarks.get("population_average", 0)
        user_avg = benchmarks.get("user_average", 0)

        if user_percentile >= 75:
            insights.append({
                "type": "benchmark_insight",
                "title": "Above Average Performance",
                "description": f"You're in the top {100 - user_percentile}% of users, scoring above the population average.",
                "recommendation": "Consider sharing your strategies with others or mentoring.",
                "sentiment": "positive"
            })
        elif user_percentile <= 25:
            insights.append({
                "type": "benchmark_insight",
                "title": "Area for Growth",
                "description": f"You're in the bottom {user_percentile}% of users compared to the population average.",
                "recommendation": "Consider professional support and focus on consistent improvement practices.",
                "sentiment": "supportive"
            })
        else:
            insights.append({
                "type": "benchmark_insight",
                "title": "Average Performance",
                "description": "Your scores are in the average range compared to other users.",
                "recommendation": "Focus on personal growth goals and consistent practice.",
                "sentiment": "neutral"
            })

        return insights

    def _assess_risk_level(self, username: str) -> str:
        """Assess user's current risk level."""
        try:
            with safe_db_context() as session:
                # Get recent scores
                recent_scores = session.query(Score).filter(
                    Score.username == username
                ).order_by(Score.id.desc()).limit(5).all()

                if not recent_scores:
                    return "unknown"

                scores = [s.total_score for s in recent_scores]
                avg_score = np.mean(scores)

                # Simple risk assessment
                if avg_score < 30:
                    return "high"
                elif avg_score < 50:
                    return "medium"
                else:
                    return "low"

        except Exception as e:
            logger.error(f"Error assessing risk level for {username}: {e}")
            return "unknown"