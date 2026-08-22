"""API router for question endpoints with Gemini AI generation and fallback."""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.db_service import get_db, QuestionService
from ..services.gemini_question_service import GeminiQuestionService, LIKERT_OPTIONS
from ..schemas import (
    QuestionResponse,
    QuestionListResponse,
    QuestionCategoryResponse
)

logger = logging.getLogger("api.questions")
router = APIRouter(tags=["Questions"])


@router.get("")
@router.get("/")
async def get_questions(
    age: Optional[int] = Query(None, ge=10, le=120, description="Filter questions by user age"),
    category: Optional[str] = Query(None, description="Category name filter (e.g. Self-Awareness)"),
    category_id: Optional[int] = Query(None, description="Category ID filter"),
    count: Optional[int] = Query(None, ge=1, le=100, description="Number of questions to return"),
    limit: Optional[int] = Query(20, ge=1, le=200, description="Maximum number of questions"),
    skip: int = Query(0, ge=0, description="Number of questions to skip"),
    active_only: bool = Query(True, description="Only return active questions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of assessment questions with Gemini AI dynamic generation and reliable database fallback.
    Returns format compatible with both questionsApi and legacy paginated consumers.
    """
    effective_count = count or limit or 20

    questions = await GeminiQuestionService.generate_questions(
        db=db,
        count=effective_count,
        category=category,
        age=age
    )

    return {
        "total": len(questions),
        "questions": questions,
        "page": skip // effective_count + 1 if effective_count > 0 else 1,
        "page_size": effective_count
    }


@router.get("/by-age/{age}")
async def get_questions_by_age(
    age: int,
    limit: Optional[int] = Query(20, ge=1, le=200, description="Maximum number of questions"),
    db: AsyncSession = Depends(get_db)
):
    """Get questions appropriate for a specific age."""
    if age < 10 or age > 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age must be between 10 and 120"
        )
    
    questions = await GeminiQuestionService.generate_questions(
        db=db,
        count=limit or 20,
        age=age
    )
    return questions


@router.get("/categories", response_model=List[QuestionCategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all question categories."""
    categories = await QuestionService.get_categories(db=db)
    return [QuestionCategoryResponse.model_validate(c) for c in categories]


@router.get("/categories/{category_id}", response_model=QuestionCategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific question category."""
    category = await QuestionService.get_category_by_id(db=db, category_id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return QuestionCategoryResponse.model_validate(category)


@router.get("/{question_id}")
async def get_question(
    question_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific question by ID."""
    question = await QuestionService.get_question_by_id(db=db, question_id=question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    
    return {
        "id": question.id,
        "text": question.question_text,
        "category_id": question.category_id,
        "difficulty": question.difficulty,
        "options": LIKERT_OPTIONS
    }


@router.post("/generate-personalized")
async def generate_personalized_assessment_questions(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Generate personalized assessment questions tailored to the user's mental & emotional health profile.
    
    Payload accepts:
    - user_context: Dict containing health, medications, daily tasks, tone, location, incidents, etc.
    - assessment_type: 'holistic_eq' | 'stress_resilience' | 'relationships_empathy' | 'reflection_triggers' | 'personalized_custom'
    - count: number of questions (default: 10)
    - tone: conversation tone preference (default: 'empathetic')
    """
    user_context = payload.get("user_context", {})
    assessment_type = payload.get("assessment_type", "holistic_eq")
    count = payload.get("count", 10)
    tone = payload.get("tone", user_context.get("preferred_tone", "empathetic"))

    questions = await GeminiQuestionService.generate_personalized_questions(
        db=db,
        user_context=user_context,
        assessment_type=assessment_type,
        count=count,
        tone=tone
    )

    return {
        "assessment_type": assessment_type,
        "total": len(questions),
        "questions": questions
    }

