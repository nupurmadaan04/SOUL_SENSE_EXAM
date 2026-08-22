"""Gemini AI Dynamic Question Generation Service with curating fallback."""
import os
import json
import logging
import random
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models import Question, QuestionCategory

logger = logging.getLogger("api.gemini_questions")

LIKERT_OPTIONS = [
    {"value": 1, "label": "Strongly Disagree"},
    {"value": 2, "label": "Disagree"},
    {"value": 3, "label": "Agree"},
    {"value": 4, "label": "Strongly Agree"}
]

CATEGORY_MAP = {
    1: "Self-Awareness",
    2: "Self-Regulation",
    3: "Motivation",
    4: "Empathy",
    5: "Social Skills"
}

REVERSE_CATEGORY_MAP = {v.lower(): k for k, v in CATEGORY_MAP.items()}


class GeneratedQuestionSchema(BaseModel):
    id: int
    text: str
    category: str
    category_id: int
    difficulty: int = 1
    options: List[Dict[str, Any]] = Field(default_factory=lambda: LIKERT_OPTIONS)


class GeminiQuestionService:
    """Service to generate psychometrically sound emotional intelligence assessment questions."""

    @classmethod
    async def generate_questions(
        cls,
        db: AsyncSession,
        count: int = 20,
        category: Optional[str] = None,
        age: Optional[int] = None,
        tone: Optional[str] = "empathetic"
    ) -> List[Dict[str, Any]]:
        """
        Generate questions using Gemini 2.5 Flash if available, otherwise safely fallback to curated bank.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and api_key.strip():
            try:
                ai_questions = await cls._generate_with_gemini(
                    api_key=api_key.strip(),
                    count=count,
                    category=category,
                    age=age,
                    tone=tone
                )
                if ai_questions and len(ai_questions) >= count:
                    logger.info(f"Successfully generated {len(ai_questions)} questions via Gemini API")
                    return ai_questions[:count]
            except Exception as e:
                logger.warning(f"Gemini dynamic generation failed, switching to curated database fallback: {e}")

        # Fallback to database question_bank
        return await cls._fallback_from_db(db, count=count, category=category, age=age)

    @classmethod
    async def generate_personalized_questions(
        cls,
        db: AsyncSession,
        user_context: Dict[str, Any],
        assessment_type: str = "holistic_eq",
        count: int = 10,
        tone: Optional[str] = "empathetic"
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized assessment questions tailored to the user's health, medications,
        daily routine, stressors, journal tone, living environment, and life incidents.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and api_key.strip():
            try:
                ai_questions = await cls._generate_personalized_with_gemini(
                    api_key=api_key.strip(),
                    user_context=user_context,
                    assessment_type=assessment_type,
                    count=count,
                    tone=tone
                )
                if ai_questions and len(ai_questions) >= count:
                    logger.info(f"Successfully generated {len(ai_questions)} personalized questions for type '{assessment_type}'")
                    return ai_questions[:count]
            except Exception as e:
                logger.warning(f"Gemini personalized generation failed, using tailored fallback: {e}")

        return await cls._tailored_fallback(db, user_context=user_context, assessment_type=assessment_type, count=count)

    @classmethod
    async def _generate_with_gemini(
        cls,
        api_key: str,
        count: int,
        category: Optional[str] = None,
        age: Optional[int] = None,
        tone: Optional[str] = "empathetic"
    ) -> List[Dict[str, Any]]:
        """Call Gemini API via modern google-genai SDK with structured output."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        category_prompt = f"Focus on category '{category}'." if category else "Distribute evenly across Self-Awareness, Self-Regulation, Motivation, Empathy, and Social Skills."
        age_prompt = f"Target audience age: {age} years old." if age else "Target general adult population."

        prompt = f"""
You are an expert psychometrician in emotional intelligence (EQ / Daniel Goleman framework).
Generate exactly {count} distinct, high-quality self-reflection assessment statements.
{category_prompt}
{age_prompt}
Tone: {tone or 'thoughtful'}.

Requirements:
- Each statement must be a 1st or 2nd-person statement that can be rated on a 1-5 Likert scale (Strongly Disagree to Strongly Agree).
- Ensure realistic, relatable scenarios that test emotional clarity, stress response, social awareness, or internal motivation.
- Assign an integer id starting from 1 to {count}.
- Map category to one of: 'Self-Awareness', 'Self-Regulation', 'Motivation', 'Empathy', 'Social Skills'.
- Assign difficulty from 1 (fundamental) to 3 (complex scenario).
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[GeneratedQuestionSchema],
                temperature=0.7,
            ),
        )

        if not response.text:
            return []

        raw_data = json.loads(response.text)
        results = []
        for idx, item in enumerate(raw_data):
            cat_name = item.get("category", "Self-Awareness")
            cat_id = REVERSE_CATEGORY_MAP.get(cat_name.lower(), ((idx % 5) + 1))
            
            results.append({
                "id": item.get("id", idx + 1),
                "text": item.get("text", item.get("question_text", "")),
                "category": cat_name,
                "category_id": cat_id,
                "difficulty": item.get("difficulty", 1),
                "options": LIKERT_OPTIONS
            })

        return results

    @classmethod
    async def _generate_personalized_with_gemini(
        cls,
        api_key: str,
        user_context: Dict[str, Any],
        assessment_type: str,
        count: int,
        tone: Optional[str] = "empathetic"
    ) -> List[Dict[str, Any]]:
        """Call Gemini API with complete user mental & emotional health profile context."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Contextual summary strings
        health_summary = f"Sleep: {user_context.get('sleep_hours', 'N/A')} hrs, Exercise: {user_context.get('exercise_freq', 'N/A')}, Diet: {user_context.get('dietary_patterns', 'N/A')}"
        meds_summary = f"Medications: {user_context.get('medications', 'None')}, Conditions: {user_context.get('conditions', 'None')}, In Therapy: {user_context.get('has_therapist', False)}"
        routine_summary = f"Daily task load: {user_context.get('daily_task_load', 5)}/10, Occupation: {user_context.get('occupation', 'General')}, Stressors: {user_context.get('primary_stressors', 'General workload')}, Routine habits: {user_context.get('routine_habits', 'Standard')}"
        tone_emotions = f"Preferred Tone: {user_context.get('preferred_tone', tone)}, Common emotions: {user_context.get('common_emotions', 'N/A')}, Triggers: {user_context.get('emotional_triggers', 'N/A')}, Coping: {user_context.get('coping_strategies', 'N/A')}"
        env_summary = f"Location/Environment: {user_context.get('environment_type', 'Urban')}, Support network: {user_context.get('support_network_size', 3)} people ({user_context.get('primary_support_type', 'Friends/Family')})"
        incidents_summary = f"Recent incidents/factors: {user_context.get('recent_incidents', 'Standard life flow')}, Goals: {user_context.get('primary_goal', 'Emotional growth')}, Focus areas: {user_context.get('focus_areas', 'General EQ')}"

        type_instructions = {
            "holistic_eq": "Create a comprehensive Emotional Intelligence assessment evenly balancing Self-Awareness, Self-Regulation, Motivation, Empathy, and Social Skills.",
            "stress_resilience": "Focus intensely on stress resilience, cognitive fatigue, daily task overload, burnout symptoms, and emotional pacing under pressure.",
            "relationships_empathy": "Focus on interpersonal resonance, active listening, boundary-setting, dealing with conflict, and leveraging social support networks.",
            "reflection_triggers": "Focus on deep introspection, recognizing subtle emotional triggers, navigating past difficult incidents, and self-compassion.",
            "personalized_custom": "Synthesize all aspects of the user's profile to create a fully tailored, bespoke evaluation designed specifically for their current life phase."
        }.get(assessment_type, "Create a personalized emotional intelligence assessment.")

        prompt = f"""
You are a world-class psychometrician and clinical emotional intelligence expert.
Generate exactly {count} distinct, relatable, and insightful self-reflection statements for a personalized assessment.

ASSESSMENT TYPE: {assessment_type.upper()}
MISSION: {type_instructions}

USER CONTEXT & HEALTH PROFILE:
- Physical Health & Lifestyle: {health_summary}
- Medical & Mental Health Background: {meds_summary}
- Daily Workload & Stressors: {routine_summary}
- Emotional Patterns & Tone: {tone_emotions}
- Environment & Support System: {env_summary}
- Life Events & Growth Goals: {incidents_summary}

REQUIREMENTS:
1. Craft statements that directly resonate with the user's specific lifestyle, workload stressors, relationships, and emotional triggers.
2. Tone must be {user_context.get('preferred_tone', tone or 'empathetic')}, non-judgmental, constructive, and empowering.
3. Each question must be a statement that the user can rate on a 4-point forced-choice Likert scale (1: Strongly Disagree, 2: Disagree, 3: Agree, 4: Strongly Agree — with no neutral midpoint to encourage clear self-alignment).
4. Assign category to one of: 'Self-Awareness', 'Self-Regulation', 'Motivation', 'Empathy', 'Social Skills'.
5. Assign difficulty 1 (foundational) to 3 (nuanced life scenario).
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[GeneratedQuestionSchema],
                temperature=0.75,
            ),
        )

        if not response.text:
            return []

        raw_data = json.loads(response.text)
        results = []
        for idx, item in enumerate(raw_data):
            cat_name = item.get("category", "Self-Awareness")
            cat_id = REVERSE_CATEGORY_MAP.get(cat_name.lower(), ((idx % 5) + 1))
            
            results.append({
                "id": item.get("id", idx + 1),
                "text": item.get("text", item.get("question_text", "")),
                "category": cat_name,
                "category_id": cat_id,
                "difficulty": item.get("difficulty", 1),
                "options": LIKERT_OPTIONS
            })

        return results

    @classmethod
    async def _tailored_fallback(
        cls,
        db: AsyncSession,
        user_context: Dict[str, Any],
        assessment_type: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Smart contextual fallback tailored to user factors when Gemini API key is offline."""
        stressors = str(user_context.get("primary_stressors", "")).lower()
        goal = str(user_context.get("primary_goal", "")).lower()
        support = str(user_context.get("primary_support_type", "")).lower()
        daily_load = user_context.get("daily_task_load", 5)

        base_templates = {
            "stress_resilience": [
                ("When my daily task load feels overwhelming, I can pause and prioritize calmly.", "Self-Regulation", 2),
                ("I notice early physical signs of mental fatigue (like tension or lack of focus) before burnout occurs.", "Self-Awareness", 1),
                ("I maintain regular self-care routines even when deadlines and external pressures mount.", "Motivation", 2),
                ("I feel comfortable stepping back and taking short breathers to recalibrate my thoughts.", "Self-Regulation", 2),
                ("I can separate my self-worth from whether I complete every single task on my list today.", "Self-Regulation", 3),
                ("When unexpected disruptions occur, I adjust my expectations without self-criticism.", "Self-Regulation", 2),
                ("I reach out for assistance before feeling completely depleted.", "Social Skills", 1),
                ("I can unwind and truly disconnect from work/study responsibilities at the end of the day.", "Self-Regulation", 2),
                ("I recognize how my sleep patterns and physical vitality impact my mood and patience.", "Self-Awareness", 1),
                ("I proactively protect my energy from non-essential stressors.", "Motivation", 2),
            ],
            "relationships_empathy": [
                ("I can sense when people in my support circle are experiencing unspoken distress.", "Empathy", 1),
                ("I am able to express my emotional needs clearly to friends, family, or partners.", "Social Skills", 2),
                ("When someone expresses a differing viewpoint, I stay curious rather than defensive.", "Empathy", 2),
                ("I maintain healthy boundaries without feeling guilty or withdrawing.", "Social Skills", 3),
                ("I offer genuine presence and active listening when others confide in me.", "Empathy", 1),
                ("I can navigate interpersonal conflicts by focusing on mutual understanding.", "Social Skills", 2),
                ("I feel comfortable leaning on my support network when facing challenging moments.", "Social Skills", 1),
                ("I celebrate the achievements and growth of those around me with sincere joy.", "Empathy", 1),
                ("I can acknowledge when my words may have caused unintentional harm and apologize sincerely.", "Self-Awareness", 2),
                ("I build deeper bonds by sharing my authentic self rather than putting up a facade.", "Social Skills", 3),
            ],
            "reflection_triggers": [
                ("I understand the specific situations and comments that trigger intense emotional reactions in me.", "Self-Awareness", 1),
                ("When past difficult incidents resurface in my mind, I practice self-compassion.", "Self-Regulation", 2),
                ("I can observe my emotional waves without immediately reacting impulsively.", "Self-Regulation", 2),
                ("I reflect regularly on what my emotional patterns are trying to teach me about my values.", "Self-Awareness", 2),
                ("I use healthy coping strategies rather than avoidance when difficult feelings arise.", "Self-Regulation", 2),
                ("I can differentiate between what is in my control and what I must learn to accept.", "Self-Awareness", 3),
                ("I give myself permission to feel grief, frustration, or fear without judging myself as weak.", "Self-Awareness", 2),
                ("I actively cultivate gratitude even during challenging life chapters.", "Motivation", 2),
                ("I can articulate my internal emotional state using precise emotional vocabulary.", "Self-Awareness", 1),
                ("I feel resilient knowing that difficult emotional states are temporary and manageable.", "Motivation", 2),
            ],
            "holistic_eq": [
                ("I can accurately pinpoint what emotion I am experiencing in the moment.", "Self-Awareness", 1),
                ("I manage my stress responses constructively when facing difficult challenges.", "Self-Regulation", 2),
                ("I remain internally driven by long-term purpose rather than fleeting external rewards.", "Motivation", 2),
                ("I quickly pick up on nonverbal emotional cues and shifts in group dynamics.", "Empathy", 2),
                ("I communicate persuasively and resolve friction collaboratively with others.", "Social Skills", 2),
                ("I understand how my thoughts directly shape my emotional state and physical energy.", "Self-Awareness", 1),
                ("I bounce back with optimism after experiencing setbacks or constructive criticism.", "Motivation", 2),
                ("I validate other people's emotional experiences even when I see things differently.", "Empathy", 2),
                ("I remain composed and thoughtful during high-stakes or emotionally charged conversations.", "Self-Regulation", 3),
                ("I inspire and support others in reaching their potential and feeling valued.", "Social Skills", 2),
            ],
            "personalized_custom": [
                (f"I actively align my daily efforts with my primary vision: '{user_context.get('primary_goal', 'personal growth')}'.", "Motivation", 2),
                (f"I notice how my routine and energy levels affect my emotional balance throughout the day.", "Self-Awareness", 1),
                (f"I navigate everyday stressors ({user_context.get('primary_stressors', 'responsibilities')}) with practical coping tools.", "Self-Regulation", 2),
                ("I communicate with an empathetic, clear mindset when coordinating tasks or sharing feelings.", "Social Skills", 2),
                ("I honor my mental health needs and adjust my pace when life demands it.", "Self-Awareness", 2),
                ("I seek feedback openly and view personal development as a continuous journey.", "Motivation", 1),
                ("I can hold space for difficult emotions while still taking meaningful constructive action.", "Self-Regulation", 3),
                (f"I leverage my support network of {user_context.get('support_network_size', 3)} contacts effectively when I need encouragement.", "Social Skills", 1),
                ("I maintain emotional clarity even when navigating complex life events.", "Self-Regulation", 2),
                ("I feel confident in my ability to cultivate deeper emotional intelligence over time.", "Motivation", 1),
            ]
        }

        selected_list = base_templates.get(assessment_type, base_templates["holistic_eq"])
        results = []
        for idx, (text_content, cat_name, diff) in enumerate(selected_list[:count]):
            cat_id = REVERSE_CATEGORY_MAP.get(cat_name.lower(), ((idx % 5) + 1))
            results.append({
                "id": idx + 1,
                "text": text_content,
                "category": cat_name,
                "category_id": cat_id,
                "difficulty": diff,
                "options": LIKERT_OPTIONS
            })
        return results

    @classmethod
    async def _fallback_from_db(
        cls,
        db: AsyncSession,
        count: int = 20,
        category: Optional[str] = None,
        age: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Reliable fallback pulling curated questions from question_bank table."""
        stmt = select(Question).filter(Question.is_active == 1)

        if category:
            cat_id = REVERSE_CATEGORY_MAP.get(category.lower())
            if cat_id:
                stmt = stmt.filter(Question.category_id == cat_id)

        if age is not None:
            stmt = stmt.filter(Question.min_age <= age, Question.max_age >= age)

        result = await db.execute(stmt)
        questions = result.scalars().all()

        if not questions:
            fallback_stmt = select(Question).filter(Question.is_active == 1).limit(count)
            res = await db.execute(fallback_stmt)
            questions = res.scalars().all()

        q_list = list(questions)
        random.shuffle(q_list)
        selected = q_list[:count] if len(q_list) >= count else q_list

        output = []
        for idx, q in enumerate(selected):
            cat_name = CATEGORY_MAP.get(q.category_id, "Self-Awareness")
            output.append({
                "id": q.id,
                "text": q.question_text,
                "category": cat_name,
                "category_id": q.category_id or ((idx % 5) + 1),
                "difficulty": q.difficulty or 1,
                "options": LIKERT_OPTIONS
            })

        return output

