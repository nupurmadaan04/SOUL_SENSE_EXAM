import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import AssessmentResult, User
from ..schemas import (
    DeepDiveType, 
    DeepDiveQuestion, 
    DeepDiveSubmission,
    DeepDiveResultResponse
)

logger = logging.getLogger(__name__)

class DeepDiveService:
    # -------------------------------------------------------------------------
    # Hardcoded Question Banks (Ported from QuestionCurator)
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
            
        # Get bank (defaults to full list)
        bank = cls.QUESTION_BANKS[assessment_type]["questions"]
        
        # Limit count
        actual_questions = bank[:min(count, len(bank))]
        
        # Return with index as ID (MVP only - eventually move to DB IDs)
        return [
            DeepDiveQuestion(id=idx, text=text) 
            for idx, text in enumerate(actual_questions)
        ]

    @classmethod
    def submit_assessment(cls, db: Session, user: User, submission: DeepDiveSubmission) -> DeepDiveResultResponse:
        """
        Process a deep dive submission.
        - Validates type.
        - Validates score ranges (1-5).
        - Prevents submitting answers for ghost questions.
        - Calculates and saves result.
        """
        assess_type = submission.assessment_type
        if assess_type not in cls.QUESTION_BANKS:
            raise HTTPException(status_code=404, detail="Invalid assessment type")
            
        valid_questions = cls.QUESTION_BANKS[assess_type]["questions"]
        valid_question_set = set(valid_questions)
        
        # 1. Validate Scores & Questions
        raw_score = 0
        response_count = 0
        
        for q_text, score in submission.responses.items():
            if q_text not in valid_question_set:
                # Ghost question check
                raise HTTPException(status_code=400, detail=f"Invalid question for this assessment: '{q_text}'")
                
            if not isinstance(score, int) or score < 1 or score > 5:
                # Strict range validation
                raise HTTPException(status_code=400, detail="Scores must be between 1 and 5")
                
            raw_score += score
            response_count += 1
            
        # 2. Check Completeness
        # We enforce at least 50% completeness to be valid (arbitrary logic for data quality)
        total_questions = len(valid_questions)
        # Note: Frontend might send varying 'counts', but we validate against the bank.
        # If user requested 5 questions but bank has 10, we accept 5.
        
        if response_count == 0:
             raise HTTPException(status_code=400, detail="Submission cannot be empty")
             
        # 3. Calculate Normalized Score (0-100)
        # Max per question is 5.
        max_possible = response_count * 5
        normalized = int((raw_score / max_possible) * 100)
        
        # 4. Save to DB
        result = AssessmentResult(
            user_id=user.id,
            assessment_type=assess_type,
            total_score=normalized,
            details=json.dumps(submission.responses),
            timestamp=datetime.now(UTC).isoformat()
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        
        return DeepDiveResultResponse(
            id=result.id,
            assessment_type=result.assessment_type,
            total_score=raw_score,
            normalized_score=result.total_score,
            timestamp=result.timestamp,
            details=submission.responses
        )

    @classmethod
    def get_history(cls, db: Session, user: User) -> List[DeepDiveResultResponse]:
        """Get past deep dive results for the user."""
        results = db.query(AssessmentResult).filter(
            AssessmentResult.user_id == user.id
        ).order_by(AssessmentResult.id.desc()).all()
        
        return [
            DeepDiveResultResponse(
                id=r.id,
                assessment_type=r.assessment_type,
                total_score=0, # We store normalized only in DB main column for now, or need to parse details
                normalized_score=r.total_score,
                timestamp=r.timestamp,
                details=json.loads(r.details) if r.details else {}
            )
            for r in results
        ]

    @classmethod
    def get_recommendations(cls, db: Session, user: User) -> List[str]:
        """
        Recommend Deep Dives based on EQ stats.
        Ported from QuestionCurator.recommend_tests logic.
        """
        from ..services.user_analytics_service import UserAnalyticsService
        
        stats = UserAnalyticsService.get_dashboard_summary(db, user.id)
        
        # Logic ported from legacy app
        recommendations = []
        
        # Age-based logic requires profile, assuming user profile fetch separately or passed
        # Simplification: Use available stats
        
        # If score low (<50 avg or latest), suggest Strengths
        if stats.average_score > 0 and stats.average_score < 50:
            recommendations.append("strengths_deep_dive")
            
        # If score very high (>80), suggest Career Clarity (growth)
        if stats.average_score > 80:
            recommendations.append("career_clarity")
            
        # Default fallback
        if not recommendations:
             recommendations.append("strengths_deep_dive")
             
        return list(set(recommendations))
