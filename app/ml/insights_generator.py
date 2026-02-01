"""
AI-Powered EQ Insights Generator
Provides personalized EQ improvement suggestions using scikit-learn for pattern recognition.
"""

import logging
import json
import os
try:
    import joblib
except ImportError:
    joblib = None
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from app.db import get_session
from app.models import Score, UserStrengths, UserEmotionalPatterns, User

logger = logging.getLogger(__name__)

class EQInsightsGenerator:
    """
    Generates personalized EQ insights and recommendations using ML techniques.
    """

    def __init__(self):
        """Initialize the insights generator."""
        self.model = None
        self.scaler = None
        self.cluster_model = None
        self.is_trained = False

        # Feature columns for ML model
        self.feature_columns = [
            'age', 'total_score', 'sentiment_score', 'score_variance',
            'avg_response', 'question_count', 'time_per_question'
        ]

        # Load or train model
        self._load_or_train_model()

    def _load_or_train_model(self) -> None:
        """Load existing model or train new one from historical data."""
        try:
            # Try to load pre-trained model
            if joblib is None:
                return

            model_path = os.path.join("models", "eq_insights_model.pkl")
            if os.path.exists(model_path):
                model_data = joblib.load(model_path)
                self.model = model_data.get('model')
                self.scaler = model_data.get('scaler')
                self.cluster_model = model_data.get('cluster_model')
                self.is_trained = True
                logger.info("Loaded pre-trained EQ insights model")
                return

        except Exception as e:
            logger.warning(f"Could not load pre-trained model: {e}")

        # Train new model from historical data
        self._train_model_from_data()

    def _train_model_from_data(self) -> None:
        """Train ML model from historical user data."""
        try:
            session = get_session()
            try:
                # Get historical scores with user data
                scores_query = session.query(
                    Score.id, Score.username, Score.total_score, Score.sentiment_score,
                    Score.age, Score.user_id, Score.timestamp
                ).filter(Score.user_id.isnot(None)).all()

                if len(scores_query) < 10:
                    logger.warning("Insufficient data for training ML model")
                    return

                # Convert to DataFrame
                data = []
                for score in scores_query:
                    # Calculate additional features
                    score_variance = self._calculate_score_variance(session, score.user_id)
                    avg_response = score.total_score / 5  # Assuming 5 questions
                    question_count = 5
                    time_per_question = 60  # Default assumption

                    data.append({
                        'user_id': score.user_id,
                        'age': score.age or 25,
                        'total_score': score.total_score,
                        'sentiment_score': score.sentiment_score or 0.0,
                        'score_variance': score_variance,
                        'avg_response': avg_response,
                        'question_count': question_count,
                        'time_per_question': time_per_question,
                        'timestamp': score.timestamp
                    })

                df = pd.DataFrame(data)

                # Create target variable: improvement potential (future score - current score)
                df['improvement_potential'] = self._calculate_improvement_potential(df)

                # Prepare features and target
                X = df[self.feature_columns]
                y = df['improvement_potential']

                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42
                )

                # Scale features
                self.scaler = StandardScaler()
                X_train_scaled = self.scaler.fit_transform(X_train)
                X_test_scaled = self.scaler.transform(X_test)

                # Train regression model
                self.model = LinearRegression()
                self.model.fit(X_train_scaled, y_train)

                # Train clustering model for user segmentation
                self.cluster_model = KMeans(n_clusters=3, random_state=42)
                self.cluster_model.fit(X_train_scaled)

                # Evaluate model
                y_pred = self.model.predict(X_test_scaled)
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)

                logger.info(f"Trained EQ insights model - MSE: {mse:.2f}, R²: {r2:.2f}")
                self.is_trained = True

                # Save model
                self._save_model()

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to train ML model: {e}")

    def _calculate_score_variance(self, session, user_id: int) -> float:
        """Calculate score variance for a user."""
        try:
            scores = session.query(Score.total_score).filter(
                Score.user_id == user_id
            ).all()

            if len(scores) < 2:
                return 0.0

            score_values = [s.total_score for s in scores]
            return np.var(score_values)

        except Exception:
            return 0.0

    def _calculate_improvement_potential(self, df: pd.DataFrame) -> pd.Series:
        """Calculate improvement potential based on historical trends."""
        improvement_potentials = []

        for user_id in df['user_id'].unique():
            user_scores = df[df['user_id'] == user_id].sort_values('timestamp')

            if len(user_scores) < 2:
                improvement_potentials.extend([0.0] * len(user_scores))
                continue

            # Calculate trend (simple linear regression on scores over time)
            scores = user_scores['total_score'].values
            times = np.arange(len(scores))

            if len(scores) > 1:
                trend_model = LinearRegression()
                trend_model.fit(times.reshape(-1, 1), scores)
                slope = trend_model.coef_[0]
            else:
                slope = 0.0

            # Improvement potential = positive trend + room for growth
            max_score = 25  # Assuming max score
            avg_score = user_scores['total_score'].mean()
            room_for_growth = max_score - avg_score

            improvement = slope * 5 + room_for_growth * 0.1  # Weighted combination
            improvement_potentials.extend([improvement] * len(user_scores))

        return pd.Series(improvement_potentials)

    def _save_model(self) -> None:
        """Save trained model to disk."""
        try:
            if joblib is None:
                return

            os.makedirs("models", exist_ok=True)
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'cluster_model': self.cluster_model,
                'feature_columns': self.feature_columns,
                'trained_at': datetime.now().isoformat()
            }

            joblib.dump(model_data, os.path.join("models", "eq_insights_model.pkl"))
            logger.info("Saved EQ insights model")

        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def generate_insights(self, user_id: int, current_score: int,
                         age: int, sentiment_score: float = 0.0) -> Dict[str, Any]:
        """
        Generate personalized EQ insights and recommendations.

        Args:
            user_id: User ID
            current_score: Current EQ test score
            age: User age
            sentiment_score: Sentiment analysis score

        Returns:
            Dictionary with insights, recommendations, and improvement suggestions
        """
        try:
            session = get_session()
            try:
                # Get user profile data
                user_strengths = session.query(UserStrengths).filter(
                    UserStrengths.user_id == user_id
                ).first()

                user_patterns = session.query(UserEmotionalPatterns).filter(
                    UserEmotionalPatterns.user_id == user_id
                ).first()

                # Get historical scores
                historical_scores = session.query(Score).filter(
                    Score.user_id == user_id
                ).order_by(Score.timestamp.desc()).limit(5).all()

                # Calculate features
                score_variance = self._calculate_score_variance(session, user_id)
                avg_response = current_score / 5  # Assuming 5 questions
                question_count = 5
                time_per_question = 60  # Default

                # Prepare features for ML prediction
                features = np.array([[
                    age, current_score, sentiment_score, score_variance,
                    avg_response, question_count, time_per_question
                ]])

                # Generate insights
                insights = {
                    'improvement_potential': 0.0,
                    'user_cluster': 'unknown',
                    'strengths_analysis': {},
                    'pattern_analysis': {},
                    'recommendations': [],
                    'next_steps': [],
                    'confidence_score': 0.0
                }

                if self.is_trained and self.model and self.scaler:
                    # Scale features
                    features_scaled = self.scaler.transform(features)

                    # Predict improvement potential
                    improvement_pred = self.model.predict(features_scaled)[0]
                    insights['improvement_potential'] = float(improvement_pred)

                    # Predict user cluster
                    cluster_pred = self.cluster_model.predict(features_scaled)[0]
                    cluster_names = ['Beginner', 'Intermediate', 'Advanced']
                    insights['user_cluster'] = cluster_names[cluster_pred]

                    # Calculate confidence (simplified)
                    insights['confidence_score'] = 0.8

                # Analyze strengths
                if user_strengths:
                    insights['strengths_analysis'] = self._analyze_strengths(user_strengths)

                # Analyze emotional patterns
                if user_patterns:
                    insights['pattern_analysis'] = self._analyze_patterns(user_patterns)

                # Generate recommendations
                insights['recommendations'] = self._generate_recommendations(
                    current_score, insights, historical_scores
                )

                # Generate next steps
                insights['next_steps'] = self._generate_next_steps(insights)

                return insights

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return self._get_fallback_insights(current_score)

    def _analyze_strengths(self, user_strengths: UserStrengths) -> Dict[str, Any]:
        """Analyze user strengths for insights."""
        analysis = {
            'top_strengths': [],
            'areas_for_improvement': [],
            'learning_style': user_strengths.learning_style,
            'communication_style': user_strengths.comm_style
        }

        try:
            # Parse JSON fields
            if user_strengths.top_strengths:
                analysis['top_strengths'] = json.loads(user_strengths.top_strengths)

            if user_strengths.areas_for_improvement:
                analysis['areas_for_improvement'] = json.loads(user_strengths.areas_for_improvement)

        except json.JSONDecodeError:
            logger.warning("Failed to parse user strengths JSON")

        return analysis

    def _analyze_patterns(self, user_patterns: UserEmotionalPatterns) -> Dict[str, Any]:
        """Analyze emotional patterns for insights."""
        analysis = {
            'common_emotions': [],
            'triggers': user_patterns.emotional_triggers,
            'coping_strategies': user_patterns.coping_strategies,
            'preferred_support': user_patterns.preferred_support
        }

        try:
            if user_patterns.common_emotions:
                analysis['common_emotions'] = json.loads(user_patterns.common_emotions)

        except json.JSONDecodeError:
            logger.warning("Failed to parse emotional patterns JSON")

        return analysis

    def _generate_recommendations(self, current_score: int, insights: Dict[str, Any],
                                historical_scores: List[Score]) -> List[str]:
        """Generate personalized recommendations based on analysis."""
        recommendations = []

        # Score-based recommendations
        if current_score < 15:
            recommendations.append("Focus on building basic emotional awareness through daily reflection")
            recommendations.append("Practice mindfulness exercises for 5-10 minutes daily")
        elif current_score < 20:
            recommendations.append("Work on emotional regulation techniques during stressful situations")
            recommendations.append("Keep a daily journal to track emotional patterns")
        else:
            recommendations.append("Leverage your emotional intelligence strengths in leadership roles")
            recommendations.append("Mentor others in developing emotional awareness")

        # Cluster-based recommendations
        cluster = insights.get('user_cluster', 'unknown')
        if cluster == 'Beginner':
            recommendations.append("Start with basic EQ assessments to establish a baseline")
            recommendations.append("Read introductory books on emotional intelligence")
        elif cluster == 'Intermediate':
            recommendations.append("Practice active listening in conversations")
            recommendations.append("Work on empathy-building exercises")
        elif cluster == 'Advanced':
            recommendations.append("Focus on teaching EQ skills to others")
            recommendations.append("Explore advanced emotional intelligence applications")

        # Strengths-based recommendations
        strengths = insights.get('strengths_analysis', {})
        top_strengths = strengths.get('top_strengths', [])
        if 'Empathy' in top_strengths:
            recommendations.append("Use your empathy to help others navigate emotional challenges")
        if 'Self-awareness' in top_strengths:
            recommendations.append("Continue developing self-awareness through regular self-reflection")

        # Pattern-based recommendations
        patterns = insights.get('pattern_analysis', {})
        common_emotions = patterns.get('common_emotions', [])
        if 'anxiety' in common_emotions:
            recommendations.append("Practice deep breathing exercises when feeling anxious")
        if 'stress' in common_emotions:
            recommendations.append("Incorporate stress management techniques into your routine")

        # Historical trend recommendations
        if len(historical_scores) > 1:
            recent_scores = [s.total_score for s in historical_scores[:3]]
            if len(recent_scores) > 1:
                trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                if trend > 0:
                    recommendations.append("Continue the positive trend with consistent practice")
                elif trend < 0:
                    recommendations.append("Review recent experiences to understand score changes")

        return recommendations[:5]  # Limit to top 5 recommendations

    def _generate_next_steps(self, insights: Dict[str, Any]) -> List[str]:
        """Generate actionable next steps."""
        next_steps = [
            "Take the EQ assessment again in 2-4 weeks to track progress",
            "Practice one recommended technique daily for a week",
            "Discuss your EQ insights with a trusted friend or mentor",
            "Set specific, measurable EQ improvement goals"
        ]

        # Add personalized next steps based on improvement potential
        improvement = insights.get('improvement_potential', 0)
        if improvement > 5:
            next_steps.append("Focus on advanced EQ development activities")
        elif improvement > 2:
            next_steps.append("Build on your current strengths while addressing weak areas")
        else:
            next_steps.append("Start with foundational EQ building exercises")

        return next_steps

    def _get_fallback_insights(self, current_score: int) -> Dict[str, Any]:
        """Provide fallback insights when ML model is not available."""
        return {
            'improvement_potential': 0.0,
            'user_cluster': 'unknown',
            'strengths_analysis': {},
            'pattern_analysis': {},
            'recommendations': [
                "Continue practicing emotional awareness exercises",
                "Keep a regular journal of your emotional experiences",
                "Seek feedback from others about your emotional responses"
            ],
            'next_steps': [
                "Retake the assessment in a few weeks",
                "Practice mindfulness daily",
                "Read about emotional intelligence"
            ],
            'confidence_score': 0.5
        }

    def collect_feedback(self, user_id: int, insights: Dict[str, Any],
                        feedback_rating: int, feedback_text: str = "") -> None:
        """
        Collect user feedback on insights to improve future recommendations.

        Args:
            user_id: User ID
            insights: Generated insights
            feedback_rating: Rating 1-5 (1=poor, 5=excellent)
            feedback_text: Optional feedback text
        """
        try:
            # Store feedback for future model improvement
            # This would typically go to a feedback table
            logger.info(f"Collected feedback from user {user_id}: rating={feedback_rating}")

            # In a real implementation, this would update a feedback database
            # and potentially retrain the model periodically

        except Exception as e:
            logger.error(f"Failed to collect feedback: {e}")
