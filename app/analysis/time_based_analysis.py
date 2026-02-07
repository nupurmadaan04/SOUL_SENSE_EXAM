"""
Time-Based Analysis Module for SOUL_SENSE_EXAM

This module provides comprehensive time-based analysis of response patterns
for returning users, enabling insights into how emotional intelligence scores
and response patterns change over time.

Key Features:
- Analyze response patterns across time periods (daily, weekly, monthly)
- Calculate temporal trends in EQ scores
- Identify response pattern changes for returning users
- Generate time-based statistics and visualizations
"""

import logging
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from statistics import mean, stdev
from typing import Dict, List, Tuple, Optional

from sqlalchemy import func
from app.db import safe_db_context
from app.models import User, Score, Response, JournalEntry

logger = logging.getLogger(__name__)


class TimeBasedAnalyzer:
    """Analyzer for temporal patterns in user responses and emotional intelligence scores."""

    def __init__(self):
        """Initialize the time-based analyzer."""
        self.logger = logging.getLogger(__name__)

    def get_user_timeline(self, username: str) -> Dict:
        """
        Get complete timeline of user activity including all scores and responses.
        
        Args:
            username: Username to analyze
            
        Returns:
            Dictionary containing timeline data sorted by timestamp
        """
        try:
            with safe_db_context() as session:
                # Get all scores for the user
                scores = session.query(Score).filter_by(username=username).order_by(Score.timestamp).all()
                
                # Get all responses for the user
                responses = session.query(Response).filter_by(username=username).order_by(Response.timestamp).all()
                
                # Get all journal entries
                journals = session.query(JournalEntry).filter_by(username=username).order_by(JournalEntry.entry_date).all()
                
                timeline_data = {
                    "username": username,
                    "scores": [
                        {
                            "id": s.id,
                            "score": s.total_score,
                            "age": s.age,
                            "age_group": s.detailed_age_group,
                            "timestamp": s.timestamp,
                        }
                        for s in scores
                    ],
                    "responses": [
                        {
                            "id": r.id,
                            "question_id": r.question_id,
                            "response_value": r.response_value,
                            "timestamp": r.timestamp,
                        }
                        for r in responses
                    ],
                    "journal_entries": [
                        {
                            "id": j.id,
                            "sentiment_score": j.sentiment_score,
                            "entry_date": j.entry_date,
                            "emotional_patterns": j.emotional_patterns,
                        }
                        for j in journals
                    ],
                }
                
                return timeline_data
        except Exception as e:
            self.logger.error(f"Error retrieving user timeline for {username}: {e}")
            return {}

    def analyze_score_trends(self, username: str) -> Dict:
        """
        Analyze trends in EQ scores over time for a returning user.
        
        Args:
            username: Username to analyze
            
        Returns:
            Dictionary containing trend analysis
        """
        try:
            with safe_db_context() as session:
                scores = session.query(Score).filter_by(username=username).order_by(Score.timestamp).all()
                
                if not scores:
                    return {"error": "No score data available"}
                
                score_values = [s.total_score for s in scores]
                timestamps = [s.timestamp for s in scores]
                
                trend_analysis = {
                    "username": username,
                    "total_attempts": len(scores),
                    "first_score": score_values[0],
                    "last_score": score_values[-1],
                    "average_score": mean(score_values),
                    "max_score": max(score_values),
                    "min_score": min(score_values),
                    "first_attempt_date": timestamps[0],
                    "last_attempt_date": timestamps[-1],
                }
                
                # Calculate improvement
                improvement = score_values[-1] - score_values[0]
                trend_analysis["total_improvement"] = improvement
                
                if score_values[0] != 0:
                    trend_analysis["improvement_percentage"] = (improvement / score_values[0]) * 100
                else:
                    trend_analysis["improvement_percentage"] = 0
                
                # Calculate standard deviation if more than one score
                if len(score_values) > 1:
                    trend_analysis["score_std_dev"] = stdev(score_values)
                    
                    # Calculate moving average (3-point)
                    moving_avgs = []
                    for i in range(len(score_values) - 2):
                        moving_avgs.append(mean(score_values[i:i+3]))
                    trend_analysis["moving_average_3"] = moving_avgs
                
                # Determine trend direction
                if len(score_values) >= 3:
                    recent_avg = mean(score_values[-3:])
                    early_avg = mean(score_values[:3])
                    trend_direction = recent_avg - early_avg
                    
                    if trend_direction > 5:
                        trend_analysis["trend_direction"] = "Strong Upward"
                    elif trend_direction > 0:
                        trend_analysis["trend_direction"] = "Moderate Upward"
                    elif trend_direction < -5:
                        trend_analysis["trend_direction"] = "Strong Downward"
                    elif trend_direction < 0:
                        trend_analysis["trend_direction"] = "Moderate Downward"
                    else:
                        trend_analysis["trend_direction"] = "Stable"
                
                return trend_analysis
        except Exception as e:
            self.logger.error(f"Error analyzing score trends for {username}: {e}")
            return {}

    def analyze_response_patterns_over_time(self, username: str) -> Dict:
        """
        Analyze how response patterns change over time.
        
        Examines which questions users tend to answer differently over time
        and identifies patterns in emotional responses.
        
        Args:
            username: Username to analyze
            
        Returns:
            Dictionary containing response pattern analysis
        """
        try:
            with safe_db_context() as session:
                responses = session.query(Response).filter_by(username=username).order_by(Response.timestamp).all()
                
                if not responses:
                    return {"error": "No response data available"}
                
                # Group responses by question_id and track changes
                question_responses = defaultdict(list)
                for resp in responses:
                    question_responses[resp.question_id].append({
                        "response_value": resp.response_value,
                        "timestamp": resp.timestamp,
                    })
                
                pattern_analysis = {
                    "username": username,
                    "total_responses": len(responses),
                    "unique_questions_answered": len(question_responses),
                    "question_patterns": {},
                }
                
                # Analyze pattern for each question
                for question_id, resp_history in question_responses.items():
                    if len(resp_history) >= 2:
                        values = [r["response_value"] for r in resp_history]
                        first_response = values[0]
                        last_response = values[-1]
                        
                        pattern_analysis["question_patterns"][question_id] = {
                            "times_answered": len(values),
                            "first_response": first_response,
                            "last_response": last_response,
                            "response_change": last_response - first_response,
                            "average_response": mean(values),
                            "response_history": values,
                        }
                
                # Calculate overall response consistency
                all_values = [r.response_value for r in responses]
                if len(all_values) > 1:
                    pattern_analysis["overall_response_std_dev"] = stdev(all_values)
                    pattern_analysis["overall_average_response"] = mean(all_values)
                
                return pattern_analysis
        except Exception as e:
            self.logger.error(f"Error analyzing response patterns for {username}: {e}")
            return {}

    def get_time_period_stats(self, username: str, period: str = "weekly") -> Dict:
        """
        Get statistics grouped by time period (daily, weekly, monthly).
        
        Args:
            username: Username to analyze
            period: Time period ('daily', 'weekly', 'monthly')
            
        Returns:
            Dictionary containing statistics grouped by time period
        """
        try:
            with safe_db_context() as session:
                scores = session.query(Score).filter_by(username=username).order_by(Score.timestamp).all()
                
                if not scores:
                    return {"error": "No score data available"}
                
                # Group scores by period
                period_stats = defaultdict(list)
                
                for score in scores:
                    try:
                        score_time = datetime.fromisoformat(score.timestamp)
                    except (ValueError, TypeError):
                        # Try alternative parsing
                        try:
                            score_time = datetime.strptime(score.timestamp, "%Y-%m-%d %H:%M:%S")
                        except:
                            continue
                    
                    if period == "daily":
                        period_key = score_time.strftime("%Y-%m-%d")
                    elif period == "weekly":
                        # Get ISO week
                        period_key = f"{score_time.isocalendar()[0]}-W{score_time.isocalendar()[1]}"
                    elif period == "monthly":
                        period_key = score_time.strftime("%Y-%m")
                    else:
                        period_key = score_time.strftime("%Y-%m-%d")
                    
                    period_stats[period_key].append(score.total_score)
                
                # Calculate statistics for each period
                result = {
                    "username": username,
                    "period": period,
                    "period_statistics": {},
                }
                
                for period_key in sorted(period_stats.keys()):
                    scores_in_period = period_stats[period_key]
                    result["period_statistics"][period_key] = {
                        "average_score": mean(scores_in_period),
                        "min_score": min(scores_in_period),
                        "max_score": max(scores_in_period),
                        "attempts_count": len(scores_in_period),
                    }
                
                return result
        except Exception as e:
            self.logger.error(f"Error analyzing period stats for {username}: {e}")
            return {}

    def identify_returning_users(self, min_attempts: int = 2) -> List[Dict]:
        """
        Identify all returning users (those with multiple attempts).
        
        Args:
            min_attempts: Minimum number of attempts to be considered a returning user
            
        Returns:
            List of returning users with their activity summaries
        """
        try:
            with safe_db_context() as session:
                # Get users with multiple scores
                user_scores = session.query(
                    Score.username,
                    func.count(Score.id).label("attempt_count"),
                    func.min(Score.timestamp).label("first_attempt"),
                    func.max(Score.timestamp).label("last_attempt"),
                    func.avg(Score.total_score).label("avg_score"),
                ).group_by(Score.username).filter(
                    func.count(Score.id) >= min_attempts
                ).all()
                
                returning_users = [
                    {
                        "username": user[0],
                        "total_attempts": user[1],
                        "first_attempt_date": user[2],
                        "last_attempt_date": user[3],
                        "average_score": user[4],
                    }
                    for user in user_scores
                ]
                
                return sorted(returning_users, key=lambda x: x["total_attempts"], reverse=True)
        except Exception as e:
            self.logger.error(f"Error identifying returning users: {e}")
            return []

    def get_comparative_analysis(self, username: str, lookback_days: int = 30) -> Dict:
        """
        Compare recent user performance with their historical average.
        
        Args:
            username: Username to analyze
            lookback_days: Number of days to look back for "recent" activity
            
        Returns:
            Dictionary containing comparative analysis
        """
        try:
            with safe_db_context() as session:
                all_scores = session.query(Score).filter_by(username=username).order_by(Score.timestamp).all()
                
                if not all_scores:
                    return {"error": "No score data available"}
                
                # Separate historical and recent scores
                cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
                
                historical_scores = []
                recent_scores = []
                
                for score in all_scores:
                    try:
                        score_time = datetime.fromisoformat(score.timestamp)
                    except (ValueError, TypeError):
                        try:
                            score_time = datetime.strptime(score.timestamp, "%Y-%m-%d %H:%M:%S")
                        except:
                            continue
                    
                    if score_time < cutoff_date:
                        historical_scores.append(score.total_score)
                    else:
                        recent_scores.append(score.total_score)
                
                comparative = {
                    "username": username,
                    "lookback_days": lookback_days,
                }
                
                if historical_scores:
                    comparative["historical"] = {
                        "average_score": mean(historical_scores),
                        "attempts": len(historical_scores),
                        "max_score": max(historical_scores),
                        "min_score": min(historical_scores),
                    }
                
                if recent_scores:
                    comparative["recent"] = {
                        "average_score": mean(recent_scores),
                        "attempts": len(recent_scores),
                        "max_score": max(recent_scores),
                        "min_score": min(recent_scores),
                    }
                    
                    # Calculate difference
                    if historical_scores:
                        hist_avg = mean(historical_scores)
                        recent_avg = mean(recent_scores)
                        comparative["performance_change"] = recent_avg - hist_avg
                        comparative["performance_change_percentage"] = (recent_avg - hist_avg) / hist_avg * 100 if hist_avg != 0 else 0
                
                return comparative
        except Exception as e:
            self.logger.error(f"Error in comparative analysis for {username}: {e}")
            return {}

    def get_user_activity_summary(self, username: str) -> Dict:
        """
        Get comprehensive activity summary for a user.
        
        Args:
            username: Username to analyze
            
        Returns:
            Dictionary containing comprehensive activity summary
        """
        try:
            with safe_db_context() as session:
                user = session.query(User).filter_by(username=username).first()
                
                if not user:
                    return {"error": "User not found"}
                
                scores_count = session.query(func.count(Score.id)).filter_by(username=username).scalar()
                responses_count = session.query(func.count(Response.id)).filter_by(username=username).scalar()
                journal_count = session.query(func.count(JournalEntry.id)).filter_by(username=username).scalar()
                
                summary = {
                    "username": username,
                    "user_created": user.created_at,
                    "last_login": user.last_login,
                    "total_assessments": scores_count or 0,
                    "total_responses": responses_count or 0,
                    "total_journal_entries": journal_count or 0,
                }
                
                # Check if user is returning
                summary["is_returning_user"] = (scores_count or 0) >= 2
                
                return summary
        except Exception as e:
            self.logger.error(f"Error getting activity summary for {username}: {e}")
            return {}


# Create a global analyzer instance
time_analyzer = TimeBasedAnalyzer()
