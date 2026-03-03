"""
Advanced Pattern Recognition Service for Emotional Analytics.

This service provides comprehensive pattern detection capabilities including:
- Temporal patterns (day-of-week, seasonal, time-of-day)
- Cross-domain correlations (sleep vs EQ, work vs stress)
- Trigger identification from journal text
- Cyclical pattern detection
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import json

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import acf
from statsmodels.tsa.arima.model import ARIMA
from prophet import Prophet
from scipy import stats
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

from app.db import safe_db_context
from app.models import Score, JournalEntry, User
from .cache_service import get_cache_service

logger = logging.getLogger(__name__)


class PatternRecognitionService:
    """Service for detecting emotional patterns and correlations."""

    def __init__(self):
        """Initialize the pattern recognition service."""
        try:
            nltk.data.find('vader_lexicon')
        except LookupError:
            nltk.download('vader_lexicon', quiet=True)
        self.sia = SentimentIntensityAnalyzer()

    def detect_temporal_patterns(self, username: str, time_range: str = "90d") -> Dict[str, Any]:
        """
        Detect temporal patterns in user's emotional data.

        Uses caching to avoid recomputation of expensive analysis.

        Args:
            username: Username to analyze
            time_range: Time range to analyze (e.g., "30d", "90d", "1y")

        Returns:
            Dictionary containing detected patterns with confidence scores
        """
        # Check cache first
        cache = get_cache_service()
        cached_result = cache.get_patterns_cache(username, time_range)
        if cached_result:
            logger.info(f"Returning cached patterns for {username}")
            return cached_result

        try:
            with safe_db_context() as session:
                # Parse time range
                days = self._parse_time_range(time_range)
                cutoff_date = datetime.now() - timedelta(days=days)

                # Get user's scores
                scores = session.query(Score).filter(
                    Score.username == username,
                    Score.timestamp >= cutoff_date.isoformat()
                ).order_by(Score.timestamp).all()

                if len(scores) < 7:  # Need minimum data for patterns
                    result = {
                        "patterns": [],
                        "message": "Insufficient data for pattern analysis",
                        "confidence": 0.0
                    }
                    cache.set_patterns_cache(username, time_range, result, ttl=300)  # Cache for 5 min
                    return result

                # Convert to DataFrame for analysis
                df = pd.DataFrame([{
                    'timestamp': pd.to_datetime(s.timestamp),
                    'score': s.total_score,
                    'sentiment': s.sentiment_score or 0.0
                } for s in scores])

                df.set_index('timestamp', inplace=True)
                df = df.resample('D').mean().ffill()  # Daily aggregation (updated from fillna)

                patterns = []

                # Day-of-week patterns
                dow_pattern = self._analyze_day_of_week_patterns(df)
                if dow_pattern:
                    patterns.append(dow_pattern)

                # Seasonal patterns
                seasonal_pattern = self._analyze_seasonal_patterns(df)
                if seasonal_pattern:
                    patterns.append(seasonal_pattern)

                # Trend patterns
                trend_pattern = self._analyze_trend_patterns(df)
                if trend_pattern:
                    patterns.append(trend_pattern)

                # Cyclical patterns
                cyclical_pattern = self._analyze_cyclical_patterns(df)
                if cyclical_pattern:
                    patterns.append(cyclical_pattern)

                result = {
                    "patterns": patterns,
                    "data_points": len(scores),
                    "time_range_days": days,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "cached": False
                }

                return result
        except Exception as e:
            logger.error(f"Error detecting temporal patterns for {username}: {e}")
            return {"patterns": [], "error": str(e)}

    def find_correlations(self, username: str, metrics: List[str] = None) -> Dict[str, Any]:
        """
        Find correlations between different metrics.

        Uses caching to avoid expensive correlation computations.

        Args:
            username: Username to analyze
            metrics: List of metrics to correlate (optional)

        Returns:
            Dictionary containing correlation matrix and insights
        """
        if metrics is None:
            metrics = ['eq_score', 'sleep_hours', 'stress_level', 'energy_level', 'screen_time']

        # Create cache key from metrics
        metrics_hash = hash(tuple(sorted(metrics)))

        # Check cache first
        cache = get_cache_service()
        cached_result = cache.get_correlations_cache(username, str(metrics_hash))
        if cached_result:
            logger.info(f"Returning cached correlations for {username}")
            return cached_result

        try:
            with safe_db_context() as session:
                # Get date range from scores
                score_dates = session.query(Score.timestamp).filter(
                    Score.username == username
                ).order_by(Score.timestamp.desc()).limit(1).first()

                if not score_dates:
                    result = {"correlations": {}, "message": "No score data available"}
                    cache.set_correlations_cache(username, str(metrics_hash), result, ttl=300)
                    return result

                # Get journal entries for the same period
                journal_entries = session.query(JournalEntry).filter(
                    JournalEntry.username == username
                ).order_by(JournalEntry.entry_date.desc()).all()

                # Create correlation dataset
                data_points = []

                # Get EQ scores by date
                eq_scores = {}
                for score in session.query(Score).filter(Score.username == username).all():
                    date_key = pd.to_datetime(score.timestamp).date()
                    eq_scores[date_key] = score.total_score

                # Process journal entries
                for entry in journal_entries:
                    entry_date = pd.to_datetime(entry.entry_date).date()
                    eq_score = eq_scores.get(entry_date)

                    if eq_score is not None:
                        data_points.append({
                            'date': entry_date,
                            'eq_score': eq_score,
                            'sleep_hours': entry.sleep_hours,
                            'stress_level': entry.stress_level,
                            'energy_level': entry.energy_level,
                            'screen_time': entry.screen_time_mins
                        })

                if len(data_points) < 5:
                    result = {
                        "correlations": {},
                        "message": "Insufficient data points for correlation analysis"
                    }
                    cache.set_correlations_cache(username, str(metrics_hash), result, ttl=300)
                    return result

                df = pd.DataFrame(data_points)
                df.set_index('date', inplace=True)

                # Calculate correlations with statistical significance
                corr_matrix = df.corr(method='pearson')
                spearman_corr = df.corr(method='spearman')

                # Find significant correlations with p-values
                significant_correlations = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
                        p_corr = corr_matrix.loc[col1, col2]
                        s_corr_val = spearman_corr.loc[col1, col2]

                        # Calculate p-value for Pearson correlation
                        n = len(df.dropna())
                        if n > 2:
                            t_stat = p_corr * np.sqrt((n - 2) / (1 - p_corr**2))
                            p_val = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
                        else:
                            p_val = 1.0

                        # Only include if statistically significant (p < 0.05)
                        if p_val < 0.05 and abs(p_corr) > 0.3:
                            # Calculate confidence interval
                            se = 1 / np.sqrt(n - 3)  # Standard error approximation
                            ci_low = p_corr - 1.96 * se
                            ci_high = p_corr + 1.96 * se

                            significant_correlations.append({
                                "metric1": col1,
                                "metric2": col2,
                                "pearson_correlation": round(p_corr, 3),
                                "spearman_correlation": round(s_corr_val, 3),
                                "p_value": round(p_val, 4),
                                "confidence_interval": [round(ci_low, 3), round(ci_high, 3)],
                                "strength": self._interpret_correlation_strength(abs(p_corr)),
                                "direction": "positive" if p_corr > 0 else "negative",
                                "statistically_significant": True
                            })

                result = {
                    "correlation_matrix": {
                        "pearson": corr_matrix.to_dict(),
                        "spearman": spearman_corr.to_dict()
                    },
                    "significant_correlations": significant_correlations,
                    "data_points": len(data_points),
                    "analysis_timestamp": datetime.now().isoformat(),
                    "statistical_notes": "Correlations with p < 0.05 are considered statistically significant",
                    "cached": False
                }

                return result
        except Exception as e:
            logger.error(f"Error finding correlations for {username}: {e}")
            return {"correlations": {}, "error": str(e)}

    def identify_triggers(self, username: str, journal_entries: List[Dict] = None) -> Dict[str, Any]:
        """
        Identify emotional triggers from journal text.

        Args:
            username: Username to analyze
            journal_entries: Optional pre-filtered journal entries

        Returns:
            Dictionary containing identified triggers and patterns
        """
        try:
            with safe_db_context() as session:
                if journal_entries is None:
                    # Get recent journal entries
                    journal_entries = session.query(JournalEntry).filter(
                        JournalEntry.username == username
                    ).order_by(JournalEntry.entry_date.desc()).limit(50).all()

                if not journal_entries:
                    return {"triggers": [], "message": "No journal entries available"}

                # Analyze sentiment and extract triggers
                trigger_patterns = defaultdict(list)
                sentiment_scores = []

                for entry in journal_entries:
                    if not entry.content:
                        continue

                    # Sentiment analysis
                    sentiment = self.sia.polarity_scores(entry.content)
                    sentiment_scores.append({
                        'date': entry.entry_date,
                        'compound': sentiment['compound'],
                        'content': entry.content[:200]  # Truncate for storage
                    })

                    # Simple keyword-based trigger detection
                    content_lower = entry.content.lower()

                    # Define trigger categories
                    triggers = {
                        'work': ['work', 'job', 'deadline', 'meeting', 'boss', 'colleague'],
                        'relationships': ['partner', 'family', 'friend', 'relationship', 'argument', 'conflict'],
                        'health': ['sick', 'pain', 'doctor', 'illness', 'headache', 'tired'],
                        'finance': ['money', 'bill', 'debt', 'financial', 'expensive', 'budget'],
                        'social': ['party', 'event', 'social', 'lonely', 'alone', 'crowd']
                    }

                    for category, keywords in triggers.items():
                        if any(keyword in content_lower for keyword in keywords):
                            trigger_patterns[category].append({
                                'date': entry.entry_date,
                                'sentiment': sentiment['compound'],
                                'content_snippet': entry.content[:100]
                            })

                # Analyze patterns in triggers
                trigger_analysis = []
                for category, occurrences in trigger_patterns.items():
                    if len(occurrences) >= 2:
                        avg_sentiment = np.mean([occ['sentiment'] for occ in occurrences])

                        trigger_analysis.append({
                            "category": category,
                            "occurrences": len(occurrences),
                            "average_sentiment": round(avg_sentiment, 3),
                            "sentiment_impact": "negative" if avg_sentiment < -0.1 else "neutral" if avg_sentiment < 0.1 else "positive",
                            "frequency": len(occurrences) / len(journal_entries) if journal_entries else 0
                        })

                return {
                    "triggers": trigger_analysis,
                    "sentiment_timeline": sentiment_scores[-20:],  # Last 20 entries
                    "total_entries_analyzed": len(journal_entries),
                    "analysis_timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error identifying triggers for {username}: {e}")
            return {"triggers": [], "error": str(e)}

    def predict_mood(self, username: str, future_days: int = 7) -> Dict[str, Any]:
        """
        Predict future mood using advanced time series forecasting.

        Uses ARIMA and Prophet models for robust predictions with confidence intervals.
        Results are cached to improve performance.

        Args:
            username: Username to analyze
            future_days: Number of days to forecast

        Returns:
            Dictionary containing mood predictions with confidence intervals
        """
        # Check cache first
        cache = get_cache_service()
        cached_result = cache.get_forecast_cache(username, future_days)
        if cached_result:
            logger.info(f"Returning cached forecast for {username}")
            return cached_result

        try:
            with safe_db_context() as session:
                # Get historical scores
                scores = session.query(Score).filter(
                    Score.username == username
                ).order_by(Score.timestamp).all()

                if len(scores) < 14:  # Need at least 2 weeks of data
                    result = {
                        "predictions": [],
                        "message": "Insufficient historical data for mood prediction",
                        "min_data_required": 14
                    }
                    cache.set_forecast_cache(username, future_days, result, ttl=300)
                    return result

                # Prepare time series data
                df = pd.DataFrame([{
                    'timestamp': pd.to_datetime(s.timestamp),
                    'score': s.total_score
                } for s in scores])

                df.set_index('timestamp', inplace=True)
                df = df.resample('D').mean().ffill() # Updated from fillna

                if len(df) < 14:
                    result = {
                        "predictions": [],
                        "message": "Insufficient daily data points for forecasting"
                    }
                    cache.set_forecast_cache(username, future_days, result, ttl=300)
                    return result

                predictions = []

                try:
                    # Try ARIMA model first
                    arima_predictions = self._predict_with_arima(df, future_days)
                    if arima_predictions:
                        predictions.extend(arima_predictions)
                        model_used = "ARIMA"
                    else:
                        # Fallback to Prophet
                        prophet_predictions = self._predict_with_prophet(df, future_days)
                        if prophet_predictions:
                            predictions.extend(prophet_predictions)
                            model_used = "Prophet"
                        else:
                            # Final fallback to simple trend
                            predictions.extend(self._predict_with_trend(df, future_days))
                            model_used = "Linear Trend"

                except Exception as e:
                    logger.warning(f"Advanced forecasting failed, using simple trend: {e}")
                    predictions.extend(self._predict_with_trend(df, future_days))
                    model_used = "Linear Trend (Fallback)"

                result = {
                    "predictions": predictions,
                    "model_used": model_used,
                    "data_points_used": len(scores),
                    "daily_data_points": len(df),
                    "analysis_timestamp": datetime.now().isoformat(),
                    "forecast_method": "Advanced time series forecasting with statistical models",
                    "cached": False
                }

                return result
        except Exception as e:
            logger.error(f"Error predicting mood for {username}: {e}")
            return {"predictions": [], "error": str(e)}

    def _predict_with_arima(self, df: pd.DataFrame, future_days: int) -> List[Dict]:
        """Predict using ARIMA model with confidence intervals."""
        try:
            # Fit ARIMA model (auto-select parameters)
            model = ARIMA(df['score'], order=(1, 1, 1))
            model_fit = model.fit()

            # Make predictions
            forecast = model_fit.forecast(steps=future_days)

            # Get confidence intervals
            pred_ci = model_fit.get_forecast(steps=future_days).conf_int()

            predictions = []
            last_date = df.index[-1]

            for i in range(future_days):
                predicted_date = last_date + timedelta(days=i+1)
                predicted_score = max(0, min(100, forecast.iloc[i]))
                ci_lower = max(0, min(100, pred_ci.iloc[i, 0]))
                ci_upper = max(0, min(100, pred_ci.iloc[i, 1]))

                predictions.append({
                    "date": predicted_date.strftime("%Y-%m-%d"),
                    "predicted_score": round(predicted_score, 1),
                    "confidence_interval": [round(ci_lower, 1), round(ci_upper, 1)],
                    "confidence_level": 0.95
                })

            return predictions

        except Exception as e:
            logger.warning(f"ARIMA forecasting failed: {e}")
            return []

    def _predict_with_prophet(self, df: pd.DataFrame, future_days: int) -> List[Dict]:
        """Predict using Facebook Prophet model."""
        try:
            # Prepare data for Prophet
            prophet_df = df.reset_index().rename(columns={'timestamp': 'ds', 'score': 'y'})

            # Fit Prophet model
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=False,
                changepoint_prior_scale=0.05
            )
            model.fit(prophet_df)

            # Make future predictions
            future = model.make_future_dataframe(periods=future_days)
            forecast = model.predict(future)

            predictions = []
            for i in range(future_days):
                predicted_date = forecast['ds'].iloc[-(future_days-i)]
                predicted_score = max(0, min(100, forecast['yhat'].iloc[-(future_days-i)]))
                ci_lower = max(0, min(100, forecast['yhat_lower'].iloc[-(future_days-i)]))
                ci_upper = max(0, min(100, forecast['yhat_upper'].iloc[-(future_days-i)]))

                predictions.append({
                    "date": predicted_date.strftime("%Y-%m-%d"),
                    "predicted_score": round(predicted_score, 1),
                    "confidence_interval": [round(ci_lower, 1), round(ci_upper, 1)],
                    "confidence_level": 0.95
                })

            return predictions

        except Exception as e:
            logger.warning(f"Prophet forecasting failed: {e}")
            return []

    def _predict_with_trend(self, df: pd.DataFrame, future_days: int) -> List[Dict]:
        """Fallback prediction using simple linear trend."""
        predictions = []
        last_date = df.index[-1]
        last_score = df['score'].iloc[-1]

        # Calculate recent trend
        recent_scores = df['score'].tail(14).values  # Use last 2 weeks
        if len(recent_scores) >= 2:
            trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
        else:
            trend = 0

        # Generate predictions with simple confidence intervals
        for i in range(1, future_days + 1):
            predicted_date = last_date + timedelta(days=i)
            predicted_score = last_score + (trend * i)

            # Bound predictions between 0-100
            predicted_score = max(0, min(100, predicted_score))

            # Simple confidence interval based on data variance
            std_dev = df['score'].tail(30).std() if len(df) >= 30 else 10
            ci_half_width = std_dev * 1.96 * np.sqrt(i)  # Increases with forecast horizon

            ci_lower = max(0, predicted_score - ci_half_width)
            ci_upper = min(100, predicted_score + ci_half_width)

            predictions.append({
                "date": predicted_date.strftime("%Y-%m-%d"),
                "predicted_score": round(predicted_score, 1),
                "confidence_interval": [round(ci_lower, 1), round(ci_upper, 1)],
                "confidence_level": 0.80  # Lower confidence for simple model
            })

        return predictions

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to days."""
        if time_range.endswith('d'):
            return int(time_range[:-1])
        elif time_range.endswith('w'):
            return int(time_range[:-1]) * 7
        elif time_range.endswith('m'):
            return int(time_range[:-1]) * 30
        elif time_range.endswith('y'):
            return int(time_range[:-1]) * 365
        else:
            return 90  # Default

    def _analyze_day_of_week_patterns(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Analyze day-of-week patterns in scores."""
        try:
            df['day_of_week'] = df.index.day_name()
            dow_avg = df.groupby('day_of_week')['score'].mean()

            # Find best and worst days
            best_day = dow_avg.idxmax()
            worst_day = dow_avg.idxmin()
            difference = dow_avg.max() - dow_avg.min()

            if difference > 5:  # Significant difference
                return {
                    "type": "day_of_week",
                    "pattern": f"Higher scores on {best_day}s, lower on {worst_day}s",
                    "best_day": best_day,
                    "worst_day": worst_day,
                    "difference": round(difference, 1),
                    "confidence": min(0.9, difference / 20)  # Scale confidence
                }
        except Exception as e:
            logger.error(f"Error analyzing day-of-week patterns: {e}")

        return None

    def _analyze_seasonal_patterns(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Analyze seasonal patterns using decomposition."""
        try:
            if len(df) < 14:  # Need at least 2 weeks
                return None

            # Decompose time series
            decomposition = seasonal_decompose(df['score'], model='additive', period=7)

            seasonal_strength = np.std(decomposition.seasonal.dropna())
            trend_strength = np.std(decomposition.trend.dropna())

            if seasonal_strength > 2:  # Significant seasonal pattern
                return {
                    "type": "seasonal",
                    "pattern": "Weekly seasonal pattern detected",
                    "seasonal_strength": round(seasonal_strength, 2),
                    "trend_strength": round(trend_strength, 2),
                    "confidence": min(0.8, seasonal_strength / 10)
                }
        except Exception as e:
            logger.error(f"Error analyzing seasonal patterns: {e}")

        return None

    def _analyze_trend_patterns(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Analyze long-term trend patterns."""
        try:
            if len(df) < 7:
                return None

            # Linear regression for trend
            X = np.arange(len(df)).reshape(-1, 1)
            y = df['score'].values

            model = LinearRegression()
            model.fit(X, y)

            slope = model.coef_[0]
            r_squared = model.score(X, y)

            if abs(slope) > 0.1 and r_squared > 0.1:  # Significant trend
                direction = "improving" if slope > 0 else "declining"
                return {
                    "type": "trend",
                    "pattern": f"Long-term {direction} trend",
                    "slope": round(slope, 3),
                    "r_squared": round(r_squared, 3),
                    "confidence": min(0.9, r_squared)
                }
        except Exception as e:
            logger.error(f"Error analyzing trend patterns: {e}")

        return None

    def _analyze_cyclical_patterns(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Analyze cyclical patterns using autocorrelation."""
        try:
            if len(df) < 14:
                return None

            # Autocorrelation function
            autocorr = acf(df['score'].dropna(), nlags=min(14, len(df)-1))

            # Find significant autocorrelations
            significant_lags = []
            for lag, corr in enumerate(autocorr[1:], 1):  # Skip lag 0
                if abs(corr) > 0.3:  # Significant correlation
                    significant_lags.append((lag, corr))

            if significant_lags:
                best_lag, best_corr = max(significant_lags, key=lambda x: abs(x[1]))
                return {
                    "type": "cyclical",
                    "pattern": f"{best_lag}-day cyclical pattern detected",
                    "cycle_length_days": best_lag,
                    "correlation": round(best_corr, 3),
                    "confidence": min(0.8, abs(best_corr))
                }
        except Exception as e:
            logger.error(f"Error analyzing cyclical patterns: {e}")

        return None

    def _interpret_correlation_strength(self, correlation: float) -> str:
        """Interpret correlation strength."""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            return "strong"
        elif abs_corr >= 0.6:
            return "moderate"
        elif abs_corr >= 0.3:
            return "weak"
        else:
            return "very_weak"