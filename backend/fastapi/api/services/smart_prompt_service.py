"""
Smart Prompt Service

Provides AI-personalized journal prompts based on:
- User's EQ assessment results
- Recent journal sentiment trends
- Detected emotional patterns
- Time of day/week patterns
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models import Score, JournalEntry, UserEmotionalPatterns


# ============================================================================
# Extended Prompt Database (50+ prompts organized by emotional context)
# ============================================================================

SMART_PROMPTS = {
    "anxiety": [
        {"id": 101, "prompt": "What's one thing you can control right now, and one thing you need to let go of?", "description": "Focus on actionable vs. uncontrollable"},
        {"id": 102, "prompt": "Describe a time you worried about something that turned out fine. What can you learn from that?", "description": "Perspective from past experiences"},
        {"id": 103, "prompt": "Write about 3 things you can see, 3 you can hear, and 3 you can feel right now.", "description": "Grounding exercise"},
        {"id": 104, "prompt": "What would you tell a friend who was feeling anxious about the same thing?", "description": "Self-compassion through perspective"},
        {"id": 105, "prompt": "What's the worst that could realistically happen, and how would you cope?", "description": "Rational examination of fears"},
        {"id": 106, "prompt": "What small action could you take right now to reduce your anxiety by even 10%?", "description": "Micro-action for relief"},
    ],
    "stress": [
        {"id": 201, "prompt": "What's causing you the most stress today? Break it down into smaller pieces.", "description": "Decompose overwhelming problems"},
        {"id": 202, "prompt": "What's one boundary you could set to protect your energy this week?", "description": "Healthy boundary setting"},
        {"id": 203, "prompt": "Describe your ideal stress-free day. What elements could you incorporate now?", "description": "Vision and small steps"},
        {"id": 204, "prompt": "What task have you been avoiding? What's the smallest step you could take?", "description": "Combat procrastination"},
        {"id": 205, "prompt": "Who could you ask for help with something on your plate?", "description": "Encourage support seeking"},
        {"id": 206, "prompt": "If you could remove one stressor from your life permanently, which would it be and why?", "description": "Identify primary stressor"},
    ],
    "sadness": [
        {"id": 301, "prompt": "What emotion are you feeling beneath the sadness? (loneliness, disappointment, grief?)", "description": "Explore layers of emotion"},
        {"id": 302, "prompt": "Write about a memory that brings you comfort, even if small.", "description": "Access positive memories"},
        {"id": 303, "prompt": "What's one kind thing you could do for yourself today?", "description": "Self-care action"},
        {"id": 304, "prompt": "If your sadness could speak, what would it say it needs?", "description": "Personify and understand"},
        {"id": 305, "prompt": "Who in your life truly cares about you? How do you know?", "description": "Counter isolation"},
        {"id": 306, "prompt": "What activity used to make you happy that you haven't done in a while?", "description": "Reconnect with joy"},
    ],
    "low_energy": [
        {"id": 401, "prompt": "What's draining your energy lately? What's one thing you could reduce or delegate?", "description": "Identify energy drains"},
        {"id": 402, "prompt": "When was the last time you felt truly energized? What were you doing?", "description": "Reconnect with energizers"},
        {"id": 403, "prompt": "What's one small thing that usually lifts your mood that you could do today?", "description": "Low-effort mood boost"},
        {"id": 404, "prompt": "How are your sleep, water intake, and movement levels? Which could use attention?", "description": "Physical wellness check"},
        {"id": 405, "prompt": "What's something you're looking forward to, even if it's small?", "description": "Future positivity"},
        {"id": 406, "prompt": "What would give you energy right now - rest, movement, connection, or creativity?", "description": "Identify energy need"},
    ],
    "gratitude": [
        {"id": 501, "prompt": "What's a small thing that went well today that you might normally overlook?", "description": "Notice the small wins"},
        {"id": 502, "prompt": "Who made a positive difference in your life recently? What would you tell them?", "description": "Appreciation of others"},
        {"id": 503, "prompt": "What's a skill or quality you have that you're grateful for?", "description": "Self-appreciation"},
        {"id": 504, "prompt": "What's something in your daily routine that you'd miss if it was gone?", "description": "Appreciate the ordinary"},
        {"id": 505, "prompt": "What's a challenge you've overcome that made you stronger?", "description": "Growth from difficulty"},
        {"id": 506, "prompt": "Name 3 simple pleasures in your life that cost nothing.", "description": "Free joys"},
    ],
    "positivity": [
        {"id": 601, "prompt": "What's exciting you about life right now? Dive into why.", "description": "Amplify positive feelings"},
        {"id": 602, "prompt": "What recent accomplishment are you proud of, big or small?", "description": "Celebrate wins"},
        {"id": 603, "prompt": "Who inspires you and why? What can you learn from them?", "description": "Draw from role models"},
        {"id": 604, "prompt": "What's a dream you're working toward? What's the next step?", "description": "Goal momentum"},
        {"id": 605, "prompt": "How could you share your positive energy with someone else today?", "description": "Pay it forward"},
        {"id": 606, "prompt": "What positive change have you noticed in yourself recently?", "description": "Self-growth recognition"},
    ],
    "reflection": [
        {"id": 701, "prompt": "What lesson did this week teach you that you want to remember?", "description": "Extract weekly wisdom"},
        {"id": 702, "prompt": "How have you changed in the past year? What sparked that growth?", "description": "Track personal evolution"},
        {"id": 703, "prompt": "What's a belief you used to hold that you've since changed your mind about?", "description": "Intellectual growth"},
        {"id": 704, "prompt": "What patterns do you notice in your emotions over the past few days?", "description": "Self-awareness building"},
        {"id": 705, "prompt": "If you could give advice to yourself from a year ago, what would it be?", "description": "Acknowledge growth"},
        {"id": 706, "prompt": "What values are most important to you, and are you living by them?", "description": "Values alignment"},
    ],
    "relationships": [
        {"id": 801, "prompt": "How are your closest relationships doing? Which one could use some attention?", "description": "Relationship check-in"},
        {"id": 802, "prompt": "Describe a meaningful conversation you had recently. What made it special?", "description": "Value connection"},
        {"id": 803, "prompt": "Is there something you've been wanting to say to someone but haven't? What's holding you back?", "description": "Unspoken words"},
        {"id": 804, "prompt": "Who do you feel most yourself around? What is it about them?", "description": "Identify safe connections"},
        {"id": 805, "prompt": "What's one way you could show appreciation to someone important to you?", "description": "Active appreciation"},
        {"id": 806, "prompt": "What kind of friend/partner/family member do you want to be?", "description": "Relationship intention"},
    ],
    "creativity": [
        {"id": 901, "prompt": "If you had a completely free day with no obligations, how would you spend it?", "description": "Fantasy exploration"},
        {"id": 902, "prompt": "What creative project or hobby have you been wanting to try?", "description": "Uncover latent interests"},
        {"id": 903, "prompt": "Write about a place—real or imagined—where you feel completely at peace.", "description": "Imaginative escape"},
        {"id": 904, "prompt": "What would your ideal life look like in 5 years? Be specific.", "description": "Vision building"},
        {"id": 905, "prompt": "If you could master any skill instantly, what would it be and why?", "description": "Explore desires"},
        {"id": 906, "prompt": "Design your perfect morning routine. What would it include?", "description": "Ideal routine planning"},
    ],
    "general": [
        {"id": 1001, "prompt": "How are you really feeling right now? Take a moment to check in.", "description": "Emotional check-in"},
        {"id": 1002, "prompt": "What's on your mind that you haven't had a chance to process yet?", "description": "Mental declutter"},
        {"id": 1003, "prompt": "What do you need more of in your life right now? Less of?", "description": "Life balance assessment"},
        {"id": 1004, "prompt": "What truth have you been avoiding that needs acknowledgment?", "description": "Honest self-reflection"},
        {"id": 1005, "prompt": "What's one thing you're curious about exploring or learning?", "description": "Spark curiosity"},
        {"id": 1006, "prompt": "If today was your last day, what would you do differently?", "description": "Perspective shift"},
    ],
}


# ============================================================================
# Smart Prompt Service Class
# ============================================================================

class SmartPromptService:
    """Service for generating AI-personalized journal prompts."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_context(self, user_id: int) -> Dict[str, Any]:
        """
        Gather user's emotional context from multiple data sources.
        
        Returns:
            Dict containing:
            - latest_eq_score: Most recent EQ assessment score
            - avg_sentiment_7d: Average journal sentiment over last 7 days
            - sentiment_trend: "improving", "declining", or "stable"
            - recent_stress_avg: Average stress level from recent journals
            - detected_patterns: List of emotional patterns
            - entry_count_7d: Number of journal entries in last 7 days
        """
        context = {
            "latest_eq_score": None,
            "avg_sentiment_7d": 50.0,
            "sentiment_trend": "stable",
            "recent_stress_avg": None,
            "detected_patterns": [],
            "entry_count_7d": 0,
            "current_time_category": self._get_time_category(),
        }
        
        # 1. Get latest EQ score
        latest_score = self.db.query(Score).filter(
            Score.user_id == user_id
        ).order_by(desc(Score.timestamp)).first()
        
        if latest_score:
            context["latest_eq_score"] = latest_score.total_score
        
        # 2. Get journal sentiment trends (last 7 days)
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        recent_entries = self.db.query(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= week_ago,
            JournalEntry.is_deleted == False
        ).order_by(desc(JournalEntry.entry_date)).all()
        
        context["entry_count_7d"] = len(recent_entries)
        
        if recent_entries:
            sentiments = [e.sentiment_score or 50.0 for e in recent_entries]
            context["avg_sentiment_7d"] = sum(sentiments) / len(sentiments)
            
            # Calculate trend (first half vs second half)
            if len(sentiments) >= 4:
                mid = len(sentiments) // 2
                older_avg = sum(sentiments[mid:]) / len(sentiments[mid:])
                recent_avg = sum(sentiments[:mid]) / mid
                
                if recent_avg > older_avg + 5:
                    context["sentiment_trend"] = "improving"
                elif recent_avg < older_avg - 5:
                    context["sentiment_trend"] = "declining"
            
            # Get stress levels
            stress_levels = [e.stress_level for e in recent_entries if e.stress_level]
            if stress_levels:
                context["recent_stress_avg"] = sum(stress_levels) / len(stress_levels)
            
            # Extract detected patterns from recent entries
            for entry in recent_entries[:5]:
                if entry.emotional_patterns:
                    try:
                        patterns = json.loads(entry.emotional_patterns)
                        context["detected_patterns"].extend(patterns)
                    except (json.JSONDecodeError, TypeError):
                        # Handle non-JSON patterns (legacy format)
                        if entry.emotional_patterns:
                            context["detected_patterns"].append(entry.emotional_patterns)
        
        # 3. Get user's stored emotional patterns if available
        user_patterns = self.db.query(UserEmotionalPatterns).filter(
            UserEmotionalPatterns.user_id == user_id
        ).first()
        
        if user_patterns and user_patterns.common_emotions:
            try:
                common = json.loads(user_patterns.common_emotions)
                context["detected_patterns"].extend(common)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Deduplicate patterns
        context["detected_patterns"] = list(set(context["detected_patterns"]))
        
        return context
    
    def _get_time_category(self) -> str:
        """Determine time category for context-aware prompts."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def _determine_prompt_categories(self, context: Dict[str, Any]) -> List[str]:
        """
        Determine which prompt categories are most relevant based on user context.
        
        Returns prioritized list of categories.
        """
        categories = []
        patterns = [p.lower() for p in context.get("detected_patterns", [])]
        
        # Check stress levels
        stress_avg = context.get("recent_stress_avg")
        if stress_avg and stress_avg >= 7:
            categories.append("stress")
        
        # Check sentiment
        avg_sentiment = context.get("avg_sentiment_7d", 50)
        if avg_sentiment < 35:
            categories.append("sadness")
        elif avg_sentiment > 70:
            categories.append("positivity")
            categories.append("gratitude")
        
        # Check detected patterns
        if any(p in patterns for p in ["anxiety", "worried", "nervous", "anxious"]):
            categories.append("anxiety")
        if any(p in patterns for p in ["fatigue", "tired", "exhausted", "low_energy"]):
            categories.append("low_energy")
        if any(p in patterns for p in ["hope", "hopeful", "optimistic"]):
            categories.append("positivity")
        
        # Check EQ score
        eq_score = context.get("latest_eq_score")
        if eq_score and eq_score < 40:
            categories.append("reflection")
        
        # Add general prompts if low engagement
        if context.get("entry_count_7d", 0) < 2:
            categories.append("general")
        
        # Always include some positives
        if "gratitude" not in categories and "positivity" not in categories:
            categories.append("gratitude")
        
        # Ensure we have categories
        if not categories:
            categories = ["general", "reflection", "gratitude"]
        
        return list(dict.fromkeys(categories))  # Dedupe while preserving order
    
    def get_smart_prompts(
        self, 
        user_id: int, 
        count: int = 3
    ) -> Dict[str, Any]:
        """
        Get personalized journal prompts for a user.
        
        Args:
            user_id: The user's ID
            count: Number of prompts to return (default 3)
            
        Returns:
            Dict containing:
            - prompts: List of prompt objects with context reasons
            - user_mood: Detected mood category
            - detected_patterns: List of patterns found
        """
        context = self.get_user_context(user_id)
        categories = self._determine_prompt_categories(context)
        
        # Determine overall mood label
        avg_sentiment = context.get("avg_sentiment_7d", 50)
        if avg_sentiment >= 65:
            mood = "positive"
        elif avg_sentiment <= 35:
            mood = "low"
        else:
            mood = "neutral"
        
        # Collect prompts from relevant categories
        selected_prompts = []
        used_ids = set()
        
        for category in categories:
            if len(selected_prompts) >= count:
                break
                
            category_prompts = SMART_PROMPTS.get(category, [])
            available = [p for p in category_prompts if p["id"] not in used_ids]
            
            if available:
                prompt = random.choice(available)
                used_ids.add(prompt["id"])
                selected_prompts.append({
                    "id": prompt["id"],
                    "prompt": prompt["prompt"],
                    "category": category,
                    "context_reason": self._get_context_reason(category, context),
                    "description": prompt.get("description", "")
                })
        
        # Fill remaining slots from general if needed
        while len(selected_prompts) < count:
            general_prompts = SMART_PROMPTS.get("general", [])
            available = [p for p in general_prompts if p["id"] not in used_ids]
            if not available:
                break
            prompt = random.choice(available)
            used_ids.add(prompt["id"])
            selected_prompts.append({
                "id": prompt["id"],
                "prompt": prompt["prompt"],
                "category": "general",
                "context_reason": "A good prompt for self-reflection",
                "description": prompt.get("description", "")
            })
        
        return {
            "prompts": selected_prompts,
            "user_mood": mood,
            "detected_patterns": context.get("detected_patterns", [])[:5],
            "sentiment_avg": round(avg_sentiment, 1),
        }
    
    def _get_context_reason(self, category: str, context: Dict[str, Any]) -> str:
        """Generate a human-readable reason for why this category was selected."""
        stress_avg = context.get('recent_stress_avg')
        stress_display = f"{stress_avg:.1f}/10" if stress_avg is not None else "elevated"
        
        reasons = {
            "anxiety": "We noticed some anxious patterns in your recent entries",
            "stress": f"Your stress levels have been {stress_display}",
            "sadness": "Your recent sentiment has been lower than usual",
            "low_energy": "You've mentioned feeling tired or low energy",
            "gratitude": "Gratitude journaling can boost your mood",
            "positivity": "You've been feeling good – let's build on that!",
            "reflection": "A moment for self-reflection based on your EQ insights",
            "relationships": "Connection with others is important for wellbeing",
            "creativity": "Creative thinking can boost mental flexibility",
            "general": "A thoughtful prompt for today's reflection",
        }
        return reasons.get(category, "Selected to support your journaling practice")


def get_smart_prompt_service(db: Session) -> SmartPromptService:
    """Dependency injection helper for FastAPI."""
    return SmartPromptService(db)
