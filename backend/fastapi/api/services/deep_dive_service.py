import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
UTC = timezone.utc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException

from ..models import AssessmentResult, User
from ..schemas import (
    DeepDiveType, 
    DeepDiveQuestion, 
    DeepDiveSubmission,
    DeepDiveResultResponse
)

logger = logging.getLogger(__name__)

class DeepDiveService:
    # -------------------------------------------------------------------------
    # Hardcoded Question Banks
    # -------------------------------------------------------------------------
    QUESTION_BANKS = {
        "career_clarity": {
            "label": "Career Clarity Check 🚀",
            "description": "Assess your career path, goals, and professional growth.",
            "icon": "🚀",
            "questions": [
                "I have a clear 5-year career plan.",
                "I feel my current role utilizes my best skills.",
                "I know exactly what skills I need to learn for my next promotion.",
                "I have a mentor who guides my professional growth.",
                "I am confident in my industry knowledge.",
                "I regularly network with people in my field.",
                "I can clearly articulate my professional value proposition.",
                "I feel secure in my current employment.",
                "I am excited about the future of my career path.",
                "My personal values align with my career choice."
            ]
        },
        "work_satisfaction": {
            "label": "Work Satisfaction Audit 💼",
            "description": "Evaluate your happiness, stress, and fulfillment at work.",
            "icon": "💼",
            "questions": [
                "I look forward to starting my work day.",
                "I feel appreciated by my manager/supervisor.",
                "I have good relationships with my colleagues.",
                "My workload is manageable.",
                "I have the tools and resources to do my job well.",
                "I feel my compensation is fair.",
                "The company culture aligns with my personality.",
                "I have autonomy in how I do my work.",
                "I feel my opinions are valued at work.",
                "I rarely think about quitting."
            ]
        },
        "strengths_deep_dive": {
            "label": "Strengths Finder 💪",
            "description": "Identify and leverage your core personal strengths.",
            "icon": "💪",
            "questions": [
                "I am aware of my top 3 personal strengths.",
                "I use my strengths every day.",
                "When faced with a challenge, I rely on my natural talents.",
                "I actively seek opportunities to use my strengths.",
                "I can easily describe what I'm best at to others.",
                "I focus more on building strengths than fixing weaknesses.",
                "My strengths have helped me overcome past failures.",
                "Others often compliment me on the same specific traits.",
                "I feel 'in flow' when using my core strengths.",
                "I seek feedback to refine my talents."
            ]
        }
    }

    @classmethod
    def get_available_types(cls) -> List[DeepDiveType]:
        """Return metadata for all available deep dives."""
        return [
            DeepDiveType(
                id=key, 
                label=data["label"], 
                description=data["description"],
                icon=data["icon"]
            )
            for key, data in cls.QUESTION_BANKS.items()
        ]

    @classmethod
    def get_questions(cls, assessment_type: str, count: int = 10) -> List[DeepDiveQuestion]:
        """Fetch questions for a specific deep dive."""
        if assessment_type not in cls.QUESTION_BANKS:
            raise HTTPException(status_code=404, detail="Assessment type not found")
            
        bank = cls.QUESTION_BANKS[assessment_type]["questions"]
        actual_questions = bank[:min(count, len(bank))]
        
        return [
            DeepDiveQuestion(id=idx, text=text) 
            for idx, text in enumerate(actual_questions)
        ]

    @classmethod
    async def submit_assessment(cls, db: AsyncSession, user: User, submission: DeepDiveSubmission) -> DeepDiveResultResponse:
        """
        Process a deep dive submission (Async).
        """
        """Process a deep dive submission."""
        assess_type = submission.assessment_type
        if assess_type not in cls.QUESTION_BANKS:
            raise HTTPException(status_code=404, detail="Invalid assessment type")
            
        valid_questions = cls.QUESTION_BANKS[assess_type]["questions"]
        valid_question_set = set(valid_questions)
        
        raw_score = 0
        response_count = 0
        
        for q_text, score in submission.responses.items():
            if q_text not in valid_question_set:
                raise HTTPException(status_code=400, detail=f"Invalid question for this assessment: '{q_text}'")
                
            if not isinstance(score, int) or score < 1 or score > 5:
                raise HTTPException(status_code=400, detail="Scores must be between 1 and 5")
                
            raw_score += score
            response_count += 1
            
        if response_count == 0:
             raise HTTPException(status_code=400, detail="Submission cannot be empty")
             
        max_possible = response_count * 5
        normalized = int((raw_score / max_possible) * 100)
        
        result = AssessmentResult(
            user_id=user.id,
            assessment_type=assess_type,
            total_score=normalized,
            details=json.dumps(submission.responses),
            timestamp=datetime.now(UTC).isoformat()
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)
        
        return DeepDiveResultResponse(
            id=result.id,
            assessment_type=result.assessment_type,
            total_score=raw_score,
            normalized_score=result.total_score,
            timestamp=result.timestamp,
            details=submission.responses
        )

    @classmethod
    async def get_history(cls, db: AsyncSession, user: User) -> List[DeepDiveResultResponse]:
        """Get past deep dive results for the user (Async)."""
        stmt = select(AssessmentResult).filter(
            AssessmentResult.user_id == user.id
        ).order_by(AssessmentResult.id.desc())
        
        result = await db.execute(stmt)
        results = result.scalars().all()
        """Get past deep dive results for the user."""
        stmt = select(AssessmentResult).filter(
            AssessmentResult.user_id == user.id,
            AssessmentResult.is_deleted == False
        ).order_by(desc(AssessmentResult.id))
        
        res = await db.execute(stmt)
        results = res.scalars().all()
        
        return [
            DeepDiveResultResponse(
                id=r.id,
                assessment_type=r.assessment_type,
                total_score=0,
                total_score=0, 
                normalized_score=r.total_score,
                timestamp=r.timestamp,
                details=json.loads(r.details) if r.details else {}
            )
            for r in results
        ]

    @classmethod
    async def get_recommendations(cls, db: AsyncSession, user: User) -> List[str]:
        """
        Recommend Deep Dives based on EQ stats (Async).
        """
        """Recommend Deep Dives based on EQ stats."""
        from ..services.user_analytics_service import UserAnalyticsService
        
        stats = await UserAnalyticsService.get_dashboard_summary(db, user.id)
        
        recommendations = []
        
        if stats.average_score > 0 and stats.average_score < 50:
            recommendations.append("strengths_deep_dive")
            
        if stats.average_score > 80:
            recommendations.append("career_clarity")
            
        if not recommendations:
             recommendations.append("strengths_deep_dive")
             
        return list(set(recommendations))
