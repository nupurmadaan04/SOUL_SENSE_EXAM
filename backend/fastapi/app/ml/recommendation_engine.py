"""
Recommendation Engine for Personalized Emotional Wellbeing Insights.

This service generates actionable recommendations based on:
- Detected patterns and correlations
- User's emotional triggers and risk factors
- Personalized improvement suggestions
- Goal setting and progress tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random

from app.db import safe_db_context
from app.models import Score, JournalEntry, User, UserEmotionalPatterns
from .pattern_recognition import PatternRecognitionService

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Engine for generating personalized recommendations."""

    def __init__(self):
        """Initialize the recommendation engine."""
        self.pattern_service = PatternRecognitionService()

    def generate_insights(self, username: str, patterns: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate comprehensive insights and recommendations.

        Args:
            username: Username to generate insights for
            patterns: Optional pre-computed patterns

        Returns:
            Dictionary containing insights and recommendations
        """
        try:
            with safe_db_context() as session:
                if patterns is None:
                    patterns = self.pattern_service.detect_temporal_patterns(username)["patterns"]

                # Get user data
                user = session.query(User).filter(User.username == username).first()
                if not user:
                    return {"insights": [], "message": "User not found"}

                # Get recent scores and journal entries
                recent_scores = session.query(Score).filter(
                    Score.username == username
                ).order_by(Score.id.desc()).limit(10).all()

                recent_entries = session.query(JournalEntry).filter(
                    JournalEntry.username == username
                ).order_by(JournalEntry.entry_date.desc()).limit(10).all()

                insights = []

                # Pattern-based insights
                pattern_insights = self._analyze_patterns(patterns, recent_scores)
                insights.extend(pattern_insights)

                # Correlation-based insights
                correlation_insights = self._analyze_correlations(username)
                insights.extend(correlation_insights)

                # Trigger-based insights
                trigger_insights = self._analyze_triggers(username, recent_entries)
                insights.extend(trigger_insights)

                # Progress insights
                progress_insights = self._analyze_progress(recent_scores)
                insights.extend(progress_insights)

                # Goal suggestions
                goal_suggestions = self._suggest_goals(username, insights)
                insights.extend(goal_suggestions)

                return {
                    "insights": insights,
                    "total_insights": len(insights),
                    "categories": list(set(insight.get("category", "general") for insight in insights)),
                    "generated_at": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error generating insights for {username}: {e}")
            return {"insights": [], "error": str(e)}

    def suggest_interventions(self, username: str, risk_level: str = "medium") -> Dict[str, Any]:
        """
        Suggest specific interventions based on risk level.

        Args:
            username: Username to suggest interventions for
            risk_level: Risk level (low, medium, high)

        Returns:
            Dictionary containing intervention suggestions
        """
        try:
            with safe_db_context() as session:
                # Get user's emotional patterns
                patterns = session.query(UserEmotionalPatterns).filter(
                    UserEmotionalPatterns.user_id == session.query(User.id).filter(
                        User.username == username
                    ).first()
                ).first()

                interventions = []

                if risk_level == "high":
                    interventions.extend(self._high_risk_interventions(patterns))
                elif risk_level == "medium":
                    interventions.extend(self._medium_risk_interventions(patterns))
                else:
                    interventions.extend(self._low_risk_interventions(patterns))

                # Add personalized interventions based on patterns
                pattern_based = self._pattern_based_interventions(username)
                interventions.extend(pattern_based)

                return {
                    "interventions": interventions,
                    "risk_level": risk_level,
                    "total_suggestions": len(interventions),
                    "generated_at": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error suggesting interventions for {username}: {e}")
            return {"interventions": [], "error": str(e)}

    def create_personalized_prompts(self, username: str, trends: List[Dict]) -> List[Dict[str, Any]]:
        """
        Create personalized journaling prompts based on trends.

        Args:
            username: Username to create prompts for
            trends: User's emotional trends

        Returns:
            List of personalized prompts
        """
        try:
            with safe_db_context() as session:
                # Get user's recent journal entries to avoid repetition
                recent_entries = session.query(JournalEntry).filter(
                    JournalEntry.username == username
                ).order_by(JournalEntry.entry_date.desc()).limit(5).all()

                used_themes = set()
                for entry in recent_entries:
                    if entry.content:
                        content_lower = entry.content.lower()
                        if "grateful" in content_lower:
                            used_themes.add("gratitude")
                        if "stress" in content_lower or "anxious" in content_lower:
                            used_themes.add("stress")
                        if "relationship" in content_lower:
                            used_themes.add("relationships")

                prompts = []

                # Base prompts
                base_prompts = [
                    {
                        "theme": "reflection",
                        "prompt": "What emotions did you experience today, and what triggered them?",
                        "category": "emotional_awareness"
                    },
                    {
                        "theme": "gratitude",
                        "prompt": "What are three things you're grateful for today, and why?",
                        "category": "positive_focus"
                    },
                    {
                        "theme": "growth",
                        "prompt": "What did you learn about yourself today?",
                        "category": "self_improvement"
                    },
                    {
                        "theme": "relationships",
                        "prompt": "How did your interactions with others affect your emotional state today?",
                        "category": "social_connections"
                    },
                    {
                        "theme": "wellbeing",
                        "prompt": "What did you do today to take care of your mental health?",
                        "category": "self_care"
                    }
                ]

                # Filter out recently used themes
                available_prompts = [p for p in base_prompts if p["theme"] not in used_themes]

                # If we filtered too much, add back some
                if len(available_prompts) < 3:
                    available_prompts = base_prompts

                # Select prompts based on trends
                selected_prompts = random.sample(available_prompts, min(3, len(available_prompts)))

                # Personalize based on trends
                for prompt in selected_prompts:
                    personalized = self._personalize_prompt(prompt, trends)
                    prompts.append(personalized)

                return prompts
        except Exception as e:
            logger.error(f"Error creating personalized prompts for {username}: {e}")
            return []

    def _analyze_patterns(self, patterns: List[Dict], recent_scores: List) -> List[Dict[str, Any]]:
        """Analyze patterns and generate insights."""
        insights = []

        for pattern in patterns:
            pattern_type = pattern.get("type")

            if pattern_type == "day_of_week":
                best_day = pattern.get("best_day", "")
                worst_day = pattern.get("worst_day", "")
                insights.append({
                    "type": "pattern",
                    "category": "temporal",
                    "title": f"Day-of-Week Pattern Detected",
                    "description": f"You tend to have higher emotional scores on {best_day}s and lower scores on {worst_day}s.",
                    "recommendation": f"Consider scheduling important activities for {best_day}s when you're likely to perform better emotionally.",
                    "confidence": pattern.get("confidence", 0.5),
                    "priority": "medium"
                })

            elif pattern_type == "trend":
                direction = pattern.get("pattern", "").split()[1]  # "improving" or "declining"
                if direction == "improving":
                    insights.append({
                        "type": "pattern",
                        "category": "progress",
                        "title": "Positive Trend Detected",
                        "description": "Your emotional scores have been trending upward over time.",
                        "recommendation": "Keep up the good work! Consider identifying what practices are contributing to this improvement.",
                        "confidence": pattern.get("confidence", 0.5),
                        "priority": "high"
                    })
                else:
                    insights.append({
                        "type": "pattern",
                        "category": "concern",
                        "title": "Declining Trend Detected",
                        "description": "Your emotional scores have been trending downward over time.",
                        "recommendation": "Consider reaching out to a mental health professional and reviewing your current coping strategies.",
                        "confidence": pattern.get("confidence", 0.5),
                        "priority": "high"
                    })

        return insights

    def _analyze_correlations(self, username: str) -> List[Dict[str, Any]]:
        """Analyze correlations and generate insights."""
        insights = []

        correlations = self.pattern_service.find_correlations(username)
        significant_correlations = correlations.get("significant_correlations", [])

        for corr in significant_correlations:
            metric1 = corr.get("metric1", "")
            metric2 = corr.get("metric2", "")
            correlation = corr.get("correlation", 0)
            direction = corr.get("direction", "")

            if metric1 == "eq_score" and metric2 == "sleep_hours":
                if direction == "positive":
                    insights.append({
                        "type": "correlation",
                        "category": "wellbeing",
                        "title": "Sleep- EQ Connection",
                        "description": "Better sleep quality correlates with higher emotional intelligence scores.",
                        "recommendation": "Prioritize good sleep hygiene to support your emotional wellbeing.",
                        "confidence": abs(correlation),
                        "priority": "high"
                    })
                else:
                    insights.append({
                        "type": "correlation",
                        "category": "concern",
                        "title": "Sleep Impact on EQ",
                        "description": "Poor sleep quality may be affecting your emotional intelligence scores.",
                        "recommendation": "Consider improving your sleep habits and monitoring their impact on your emotional state.",
                        "confidence": abs(correlation),
                        "priority": "high"
                    })

            elif metric1 == "eq_score" and metric2 == "stress_level":
                if direction == "negative":
                    insights.append({
                        "type": "correlation",
                        "category": "stress_management",
                        "title": "Stress-EQ Relationship",
                        "description": "Higher stress levels correlate with lower emotional intelligence scores.",
                        "recommendation": "Practice stress-reduction techniques and monitor how they affect your EQ scores.",
                        "confidence": abs(correlation),
                        "priority": "high"
                    })

        return insights

    def _analyze_triggers(self, username: str, recent_entries: List) -> List[Dict[str, Any]]:
        """Analyze triggers and generate insights."""
        insights = []

        triggers = self.pattern_service.identify_triggers(username)
        trigger_analysis = triggers.get("triggers", [])

        for trigger in trigger_analysis:
            category = trigger.get("category", "")
            occurrences = trigger.get("occurrences", 0)
            sentiment_impact = trigger.get("sentiment_impact", "")

            if sentiment_impact == "negative" and occurrences >= 3:
                insights.append({
                    "type": "trigger",
                    "category": "emotional_triggers",
                    "title": f"{category.title()} Trigger Pattern",
                    "description": f"You've mentioned {category} challenges {occurrences} times recently, often with negative emotional impact.",
                    "recommendation": f"Consider developing specific coping strategies for {category}-related stressors.",
                    "confidence": 0.7,
                    "priority": "medium"
                })

        return insights

    def _analyze_progress(self, recent_scores: List) -> List[Dict[str, Any]]:
        """Analyze progress and generate insights."""
        insights = []

        if len(recent_scores) >= 2:
            latest_score = recent_scores[0].total_score
            previous_score = recent_scores[1].total_score
            change = latest_score - previous_score

            if abs(change) >= 10:
                direction = "increased" if change > 0 else "decreased"
                insights.append({
                    "type": "progress",
                    "category": "score_change",
                    "title": f"Recent Score Change",
                    "description": f"Your latest EQ score {direction} by {abs(change)} points compared to your previous assessment.",
                    "recommendation": "Reflect on what factors may have contributed to this change in your journal.",
                    "confidence": 0.8,
                    "priority": "medium"
                })

        return insights

    def _suggest_goals(self, username: str, insights: List[Dict]) -> List[Dict[str, Any]]:
        """Suggest goals based on insights."""
        goals = []

        # Analyze insight categories to suggest goals
        categories = [insight.get("category") for insight in insights]
        category_counts = defaultdict(int)

        for category in categories:
            category_counts[category] += 1

        # Suggest goals based on most common categories
        most_common = max(category_counts.items(), key=lambda x: x[1]) if category_counts else None

        if most_common:
            category, count = most_common

            if category == "stress_management":
                goals.append({
                    "type": "goal",
                    "category": "stress_reduction",
                    "title": "Stress Management Goal",
                    "description": "Develop consistent stress management practices over the next month.",
                    "specific_actions": [
                        "Practice daily mindfulness or meditation for 10 minutes",
                        "Identify and limit exposure to stress triggers",
                        "Track stress levels in your journal"
                    ],
                    "timeframe": "4 weeks",
                    "priority": "high"
                })

            elif category == "wellbeing":
                goals.append({
                    "type": "goal",
                    "category": "wellbeing_improvement",
                    "title": "Wellbeing Enhancement Goal",
                    "description": "Focus on improving overall emotional wellbeing through targeted practices.",
                    "specific_actions": [
                        "Maintain consistent sleep schedule",
                        "Incorporate daily exercise or movement",
                        "Practice gratitude journaling"
                    ],
                    "timeframe": "6 weeks",
                    "priority": "high"
                })

        return goals

    def _high_risk_interventions(self, patterns: UserEmotionalPatterns) -> List[Dict[str, Any]]:
        """Generate high-risk interventions."""
        return [
            {
                "type": "intervention",
                "priority": "urgent",
                "title": "Professional Support Recommended",
                "description": "Based on your patterns, consider consulting a mental health professional.",
                "actions": [
                    "Contact a licensed therapist or counselor",
                    "Reach out to a trusted healthcare provider",
                    "Consider crisis hotlines if needed"
                ],
                "resources": ["988 Suicide & Crisis Lifeline", "Local mental health services"]
            },
            {
                "type": "intervention",
                "priority": "high",
                "title": "Immediate Coping Strategies",
                "description": "Practice these techniques when experiencing intense emotions.",
                "actions": [
                    "Use deep breathing exercises (4-7-8 technique)",
                    "Take a 10-minute walk outside",
                    "Call a trusted friend or family member"
                ]
            }
        ]

    def _medium_risk_interventions(self, patterns: UserEmotionalPatterns) -> List[Dict[str, Any]]:
        """Generate medium-risk interventions."""
        return [
            {
                "type": "intervention",
                "priority": "medium",
                "title": "Stress Management Techniques",
                "description": "Incorporate these practices to manage stress more effectively.",
                "actions": [
                    "Practice daily mindfulness meditation",
                    "Maintain a consistent sleep schedule",
                    "Exercise for at least 30 minutes most days"
                ]
            },
            {
                "type": "intervention",
                "priority": "medium",
                "title": "Social Support Network",
                "description": "Build and maintain connections with supportive people.",
                "actions": [
                    "Schedule regular check-ins with friends/family",
                    "Join a support group or community",
                    "Consider talking to a counselor"
                ]
            }
        ]

    def _low_risk_interventions(self, patterns: UserEmotionalPatterns) -> List[Dict[str, Any]]:
        """Generate low-risk interventions."""
        return [
            {
                "type": "intervention",
                "priority": "low",
                "title": "Wellbeing Maintenance",
                "description": "Continue practices that support emotional health.",
                "actions": [
                    "Maintain healthy sleep habits",
                    "Practice regular exercise",
                    "Engage in hobbies and enjoyable activities"
                ]
            }
        ]

    def _pattern_based_interventions(self, username: str) -> List[Dict[str, Any]]:
        """Generate interventions based on detected patterns."""
        interventions = []

        # Get patterns
        patterns_data = self.pattern_service.detect_temporal_patterns(username)
        patterns = patterns_data.get("patterns", [])

        for pattern in patterns:
            if pattern.get("type") == "day_of_week":
                best_day = pattern.get("best_day", "")
                interventions.append({
                    "type": "intervention",
                    "priority": "low",
                    "title": f"Optimize {best_day} Activities",
                    "description": f"Schedule important emotional work for {best_day}s when you're typically at your best.",
                    "actions": [
                        f"Plan challenging conversations for {best_day}s",
                        f"Schedule creative or reflective activities for {best_day}s"
                    ]
                })

        return interventions

    def _personalize_prompt(self, prompt: Dict, trends: List[Dict]) -> Dict[str, Any]:
        """Personalize a prompt based on user trends."""
        # For now, return the prompt as-is
        # Could be enhanced to modify prompts based on trends
        return {
            "id": f"{prompt['theme']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "theme": prompt["theme"],
            "prompt": prompt["prompt"],
            "category": prompt["category"],
            "suggested_frequency": "daily",
            "estimated_time": "5-10 minutes"
        }