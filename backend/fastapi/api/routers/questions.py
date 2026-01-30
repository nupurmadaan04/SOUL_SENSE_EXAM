"""API router for question endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Define VERSION locally since app.constants doesn't exist in backend
VERSION = "1.0.0"

from ..services.db_service import get_db, QuestionService
from ..schemas import (
    QuestionResponse,
    QuestionListResponse,
    QuestionCategoryResponse
)

router = APIRouter()


@router.get("/", response_model=QuestionListResponse)
async def get_questions(
    age: Optional[int] = Query(None, ge=10, le=120, description="Filter questions by user age"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of questions"),
    skip: int = Query(0, ge=0, description="Number of questions to skip"),
    active_only: bool = Query(True, description="Only return active questions"),
    db: Session = Depends(get_db)
):
    """
    Get a list of questions.
    
    - **age**: Optional age filter (returns questions appropriate for this age)
    - **category_id**: Optional category filter
    - **limit**: Maximum number of questions to return (max 200)
    - **skip**: Number of questions to skip for pagination
    - **active_only**: Whether to return only active questions
    
    Returns a paginated question list.
    """
    if age is not None:
        # Get age-appropriate questions
        questions = QuestionService.get_questions_by_age(
            db=db,
            age=age,
            limit=limit
        )
        total = len(questions)
    else:
        # Get questions with filters
        questions, total = QuestionService.get_questions(
            db=db,
            skip=skip,
            limit=limit,
            category_id=category_id,
            active_only=active_only
        )
    
    return QuestionListResponse(
        total=total,
        questions=[QuestionResponse.model_validate(q) for q in questions],
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/by-age/{age}", response_model=List[QuestionResponse])
async def get_questions_by_age(
    age: int,
    limit: Optional[int] = Query(None, ge=1, le=200, description="Maximum number of questions"),
    db: Session = Depends(get_db)
):
    """
    Get questions appropriate for a specific age.
    
    - **age**: User's age (10-120)
    - **limit**: Optional limit on number of questions
    
    Returns questions where min_age <= age <= max_age.
    """
    if age < 10 or age > 120:
        raise HTTPException(status_code=400, detail="Age must be between 10 and 120")
    
    questions = QuestionService.get_questions_by_age(db=db, age=age, limit=limit)
    
    return [QuestionResponse.model_validate(q) for q in questions]


@router.get("/categories", response_model=List[QuestionCategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    """
    Get all question categories.
    
    Returns a list of all available question categories.
    """
    categories = QuestionService.get_categories(db=db)
    
    return [QuestionCategoryResponse.model_validate(c) for c in categories]


@router.get("/categories/{category_id}", response_model=QuestionCategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific question category.
    
    - **category_id**: The ID of the category to retrieve
    """
    category = QuestionService.get_category_by_id(db=db, category_id=category_id)
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return QuestionCategoryResponse.model_validate(category)


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific question by ID.
    
    - **question_id**: The ID of the question to retrieve
    """
    question = QuestionService.get_question_by_id(db=db, question_id=question_id)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return QuestionResponse.model_validate(question)
