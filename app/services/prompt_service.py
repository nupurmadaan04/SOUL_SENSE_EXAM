import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
import random
from sqlalchemy import desc, func
from app.db import safe_db_context
from app.models import JournalPrompt, PromptUsage, User, UserEmotionalPatterns, UserStrengths, Score, JournalEntry
from app.exceptions import DatabaseError

logger = logging.getLogger(__name__)

class PromptService:
    """
    Service layer for managing AI-generated journal prompts and user interactions.
    """

    @staticmethod
    def seed_default_prompts() -> None:
        """
        Seed the database with default journal prompts if none exist.
        """
        try:
            with safe_db_context() as session:
                # Check if prompts already exist
                existing_count = session.query(func.count(JournalPrompt.id)).scalar()
                if existing_count > 0:
                    logger.info(f"Prompts already seeded ({existing_count} prompts exist)")
                    return

                # Default prompts organized by category
                default_prompts = [
                    # Reflection prompts
                    {
                        "prompt_text": "What emotions did you experience today that surprised you, and why?",
                        "category": "reflection",
                        "emotional_context": "neutral",
                        "difficulty_level": "medium",
                        "target_emotions": json.dumps(["surprise", "curiosity"])
                    },
                    {
                        "prompt_text": "Looking back on your week, what patterns do you notice in your emotional responses?",
                        "category": "reflection",
                        "emotional_context": "neutral",
                        "difficulty_level": "advanced",
                        "target_emotions": json.dumps(["awareness", "insight"])
                    },
                    {
                        "prompt_text": "What is one thing you learned about yourself this week?",
                        "category": "reflection",
                        "emotional_context": "positive",
                        "difficulty_level": "easy",
                        "target_emotions": json.dumps(["growth", "learning"])
                    },

                    # Gratitude prompts
                    {
                        "prompt_text": "What are three things you're grateful for today, and why?",
                        "category": "gratitude",
                        "emotional_context": "positive",
                        "difficulty_level": "easy",
                        "target_emotions": json.dumps(["gratitude", "appreciation"])
                    },
                    {
                        "prompt_text": "Who in your life made you smile today, and what did they do?",
                        "category": "gratitude",
                        "emotional_context": "positive",
                        "difficulty_level": "easy",
                        "target_emotions": json.dumps(["gratitude", "connection"])
                    },
                    {
                        "prompt_text": "What challenge from today are you grateful for overcoming?",
                        "category": "gratitude",
                        "emotional_context": "positive",
                        "difficulty_level": "medium",
                        "target_emotions": json.dumps(["resilience", "gratitude"])
                    },

                    # Stress/Emotional prompts
                    {
                        "prompt_text": "What triggered your stress today, and how did you respond to it?",
                        "category": "stress",
                        "emotional_context": "negative",
                        "difficulty_level": "medium",
                        "target_emotions": json.dumps(["stress", "anxiety"])
                    },
                    {
                        "prompt_text": "When did you feel most at peace today, and what were you doing?",
                        "category": "stress",
                        "emotional_context": "positive",
                        "difficulty_level": "easy",
                        "target_emotions": json.dumps(["calm", "peace"])
                    },
                    {
                        "prompt_text": "What is one small thing you can do tomorrow to reduce your stress?",
                        "category": "stress",
                        "emotional_context": "neutral",
                        "difficulty_level": "easy",
                        "target_emotions": json.dumps(["planning", "hope"])
                    },

                    # Growth/Mindfulness prompts
                    {
                        "prompt_text": "What is one habit you'd like to cultivate, and why?",
                        "category": "growth",
                        "emotional_context": "neutral",
                        "difficulty_level": "medium",
                        "target_emotions": json.dumps(["aspiration", "motivation"])
                    },
                    {
                        "prompt_text": "How did you show kindness to yourself today?",
                        "category": "growth",
                        "emotional_context": "positive",
                        "difficulty_level": "easy",
                        "target_emotions": json.dumps(["self-compassion", "kindness"])
                    },
                    {
                        "prompt_text": "What boundaries do you need to set to protect your emotional well-being?",
                        "category": "growth",
                        "emotional_context": "neutral",
                        "difficulty_level": "advanced",
                        "target_emotions": json.dumps(["boundaries", "self-care"])
                    }
                ]

                # Create prompt objects
                for prompt_data in default_prompts:
                    prompt = JournalPrompt(**prompt_data)
                    session.add(prompt)

                session.commit()
                logger.info(f"Seeded {len(default_prompts)} default journal prompts")

        except Exception as e:
            logger.error(f"Failed to seed default prompts: {e}")
            raise DatabaseError("Failed to seed default prompts", original_exception=e)

    @staticmethod
    def get_personalized_prompts(user_id: int, count: int = 3, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get personalized prompts based on user's EQ assessment, emotional patterns, and recent journal entries.

        Args:
            user_id: User ID
            count: Number of prompts to return
            context: Optional context dict with 'current_mood', 'recent_stress', etc.

        Returns:
            List of prompt dictionaries with metadata
        """
        try:
            with safe_db_context() as session:
                # Get user profile data
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    return PromptService._get_fallback_prompts(count)

                # Get user's emotional patterns
                emotional_patterns = session.query(UserEmotionalPatterns).filter(
                    UserEmotionalPatterns.user_id == user_id
                ).first()

                # Get user's recent EQ scores
                recent_scores = session.query(Score).filter(
                    Score.user_id == user_id
                ).order_by(desc(Score.timestamp)).limit(3).all()

                # Get recent journal entries for context
                recent_entries = session.query(JournalEntry).filter(
                    JournalEntry.user_id == user_id,
                    JournalEntry.entry_date >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                ).order_by(desc(JournalEntry.entry_date)).limit(5).all()

                # Analyze user context
                user_context = PromptService._analyze_user_context(
                    user, emotional_patterns, recent_scores, recent_entries, context
                )

                # Get suitable prompts
                prompts = PromptService._select_prompts(session, user_context, count)

                # Track prompt usage
                for prompt in prompts:
                    usage = PromptUsage(
                        user_id=user_id,
                        prompt_id=prompt['id']
                    )
                    session.add(usage)

                session.commit()

                return prompts

        except Exception as e:
            logger.error(f"Failed to get personalized prompts for user {user_id}: {e}")
            return PromptService._get_fallback_prompts(count)

    @staticmethod
    def _analyze_user_context(user: User, emotional_patterns: Optional[UserEmotionalPatterns],
                            recent_scores: List[Score], recent_entries: List[JournalEntry],
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze user context to determine appropriate prompt categories and characteristics.
        """
        context_analysis = {
            'eq_score_range': {'min': 0, 'max': 25},  # Default range
            'common_emotions': [],
            'emotional_context': 'neutral',
            'difficulty_preference': 'medium',
            'categories': ['reflection', 'gratitude', 'growth'],
            'recent_mood': 'neutral',
            'stress_level': 5
        }

        # Analyze EQ scores
        if recent_scores:
            avg_score = sum(score.total_score for score in recent_scores) / len(recent_scores)
            context_analysis['eq_score_range'] = {
                'min': max(0, int(avg_score) - 5),
                'max': min(25, int(avg_score) + 5)
            }

            # Adjust difficulty based on EQ score
            if avg_score < 15:
                context_analysis['difficulty_preference'] = 'easy'
            elif avg_score > 20:
                context_analysis['difficulty_preference'] = 'advanced'

        # Analyze emotional patterns
        if emotional_patterns and emotional_patterns.common_emotions:
            try:
                common_emotions = json.loads(emotional_patterns.common_emotions)
                context_analysis['common_emotions'] = common_emotions

                # Adjust categories based on emotional patterns
                if 'anxiety' in common_emotions or 'stress' in common_emotions:
                    context_analysis['categories'].insert(0, 'stress')
                    context_analysis['emotional_context'] = 'negative'
                elif 'gratitude' in common_emotions or 'joy' in common_emotions:
                    context_analysis['emotional_context'] = 'positive'

            except json.JSONDecodeError:
                pass

        # Analyze recent journal entries
        if recent_entries:
            avg_sentiment = sum(entry.sentiment_score or 0 for entry in recent_entries) / len(recent_entries)
            avg_stress = sum(entry.stress_level or 5 for entry in recent_entries) / len(recent_entries)

            context_analysis['recent_mood'] = 'positive' if avg_sentiment > 20 else 'negative' if avg_sentiment < -20 else 'neutral'
            context_analysis['stress_level'] = avg_stress

            # Adjust categories based on recent patterns
            if avg_stress > 7:
                context_analysis['categories'].insert(0, 'stress')
            elif avg_sentiment > 30:
                context_analysis['categories'].insert(0, 'gratitude')

        # Override with provided context
        if context:
            context_analysis.update(context)

        return context_analysis

    @staticmethod
    def _select_prompts(session, user_context: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        Select appropriate prompts based on user context analysis.
        """
        try:
            # Build query based on user context
            query = session.query(JournalPrompt).filter(JournalPrompt.is_active == True)

            # Filter by categories (prioritize first category)
            preferred_categories = user_context.get('categories', [])
            if preferred_categories:
                query = query.filter(JournalPrompt.category.in_(preferred_categories))

            # Filter by emotional context
            emotional_context = user_context.get('emotional_context')
            if emotional_context:
                query = query.filter(JournalPrompt.emotional_context == emotional_context)

            # Filter by difficulty
            difficulty = user_context.get('difficulty_preference', 'medium')
            query = query.filter(JournalPrompt.difficulty_level == difficulty)

            # Filter by target emotions if user has common emotions
            common_emotions = user_context.get('common_emotions', [])
            if common_emotions:
                # This is a simplified approach - in production, you'd want more sophisticated matching
                emotion_filters = []
                for emotion in common_emotions:
                    emotion_filters.append(JournalPrompt.target_emotions.like(f'%{emotion}%'))
                if emotion_filters:
                    query = query.filter(func.coalesce(JournalPrompt.target_emotions, '').regexp('|'.join(common_emotions)))

            # Order by success rate and usage (prefer successful, less-used prompts)
            query = query.order_by(
                desc(JournalPrompt.success_rate),
                JournalPrompt.usage_count
            )

            # Get more than needed for randomization
            candidates = query.limit(count * 3).all()

            if not candidates:
                # Fallback to any active prompts
                candidates = session.query(JournalPrompt).filter(
                    JournalPrompt.is_active == True
                ).order_by(func.random()).limit(count * 2).all()

            # Randomly select from candidates
            selected = random.sample(candidates, min(count, len(candidates)))

            # Convert to dict format
            result = []
            for prompt in selected:
                result.append({
                    'id': prompt.id,
                    'prompt_text': prompt.prompt_text,
                    'category': prompt.category,
                    'emotional_context': prompt.emotional_context,
                    'difficulty_level': prompt.difficulty_level,
                    'target_emotions': prompt.target_emotions
                })

                # Increment usage count
                prompt.usage_count += 1
                session.add(prompt)

            return result

        except Exception as e:
            logger.error(f"Failed to select prompts: {e}")
            return PromptService._get_fallback_prompts(count)

    @staticmethod
    def _get_fallback_prompts(count: int) -> List[Dict[str, Any]]:
        """
        Get fallback prompts when personalized selection fails.
        """
        fallback_prompts = [
            {
                'id': 0,
                'prompt_text': "What are you feeling right now, and why?",
                'category': 'reflection',
                'emotional_context': 'neutral',
                'difficulty_level': 'easy',
                'target_emotions': '["awareness"]'
            },
            {
                'id': 0,
                'prompt_text': "What is one thing you're grateful for today?",
                'category': 'gratitude',
                'emotional_context': 'positive',
                'difficulty_level': 'easy',
                'target_emotions': '["gratitude"]'
            },
            {
                'id': 0,
                'prompt_text': "What challenged you today, and what did you learn from it?",
                'category': 'growth',
                'emotional_context': 'neutral',
                'difficulty_level': 'medium',
                'target_emotions': '["resilience", "learning"]'
            }
        ]

        return fallback_prompts[:count]

    @staticmethod
    def record_prompt_feedback(user_id: int, prompt_id: int, journal_entry_id: Optional[int] = None,
                             feedback_rating: Optional[int] = None, was_helpful: Optional[bool] = None,
                             time_spent: Optional[int] = None, emotional_impact: Optional[str] = None) -> None:
        """
        Record user feedback on prompt effectiveness.
        """
        try:
            with safe_db_context() as session:
                # Find the usage record
                usage = session.query(PromptUsage).filter(
                    PromptUsage.user_id == user_id,
                    PromptUsage.prompt_id == prompt_id,
                    PromptUsage.journal_entry_id == journal_entry_id
                ).order_by(desc(PromptUsage.used_at)).first()

                if usage:
                    # Update feedback
                    if feedback_rating is not None:
                        usage.feedback_rating = feedback_rating
                    if was_helpful is not None:
                        usage.was_helpful = was_helpful
                    if time_spent is not None:
                        usage.time_spent = time_spent
                    if emotional_impact is not None:
                        usage.emotional_impact = emotional_impact

                    session.add(usage)

                    # Update prompt success rate
                    PromptService._update_prompt_success_rate(session, prompt_id)

                    session.commit()
                    logger.info(f"Recorded feedback for prompt {prompt_id} from user {user_id}")

        except Exception as e:
            logger.error(f"Failed to record prompt feedback: {e}")

    @staticmethod
    def _update_prompt_success_rate(session, prompt_id: int) -> None:
        """
        Update the success rate of a prompt based on user feedback.
        """
        try:
            # Get all feedback for this prompt
            feedback_records = session.query(PromptUsage).filter(
                PromptUsage.prompt_id == prompt_id,
                PromptUsage.feedback_rating.isnot(None)
            ).all()

            if feedback_records:
                total_ratings = len(feedback_records)
                avg_rating = sum(record.feedback_rating for record in feedback_records) / total_ratings

                # Calculate success rate (rating 4-5 = successful)
                successful_ratings = sum(1 for record in feedback_records if record.feedback_rating >= 4)
                success_rate = successful_ratings / total_ratings

                # Update prompt
                prompt = session.query(JournalPrompt).filter(JournalPrompt.id == prompt_id).first()
                if prompt:
                    prompt.success_rate = success_rate
                    session.add(prompt)

        except Exception as e:
            logger.error(f"Failed to update prompt success rate: {e}")

    @staticmethod
    def get_prompt_stats() -> Dict[str, Any]:
        """
        Get statistics about prompt usage and effectiveness.
        """
        try:
            with safe_db_context() as session:
                # Total prompts
                total_prompts = session.query(func.count(JournalPrompt.id)).scalar()

                # Active prompts
                active_prompts = session.query(func.count(JournalPrompt.id)).filter(
                    JournalPrompt.is_active == True
                ).scalar()

                # Usage statistics
                total_usage = session.query(func.count(PromptUsage.id)).scalar()
                avg_rating = session.query(func.avg(PromptUsage.feedback_rating)).scalar()

                # Category breakdown
                category_stats = session.query(
                    JournalPrompt.category,
                    func.count(JournalPrompt.id),
                    func.avg(JournalPrompt.success_rate)
                ).group_by(JournalPrompt.category).all()

                return {
                    'total_prompts': total_prompts,
                    'active_prompts': active_prompts,
                    'total_usage': total_usage,
                    'average_rating': float(avg_rating) if avg_rating else 0.0,
                    'category_breakdown': [
                        {
                            'category': cat,
                            'count': count,
                            'avg_success_rate': float(rate) if rate else 0.0
                        } for cat, count, rate in category_stats
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to get prompt stats: {e}")
            return {}
