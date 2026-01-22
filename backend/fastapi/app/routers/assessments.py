from typing import List, Dict, Any
import json

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, desc

from ..models.schemas import (
    AssessmentSummary,
    AssessmentDetail,
    AssessmentEntry,
    QuestionSetResponse,
)
from app.db import get_session
from app.models import AssessmentResult
from app.services.question_curator import QuestionCurator

router = APIRouter(prefix="/api", tags=["assessments"])


def _parse_details(raw: str | None) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


@router.get("/assessments", response_model=List[AssessmentSummary])
def list_assessments() -> List[AssessmentSummary]:
    session = get_session()
    try:
        rows = (
            session.query(
                AssessmentResult.assessment_type,
                func.count().label("total_responses"),
                func.max(AssessmentResult.total_score).label("highest_score"),
                func.avg(AssessmentResult.total_score).label("average_score"),
                func.max(AssessmentResult.timestamp).label("latest_timestamp"),
            )
            .group_by(AssessmentResult.assessment_type)
            .all()
        )
        return [
            AssessmentSummary(
                assessment_type=row.assessment_type,
                total_responses=row.total_responses or 0,
                highest_score=row.highest_score,
                average_score=float(row.average_score) if row.average_score is not None else None,
                latest_timestamp=row.latest_timestamp,
            )
            for row in rows
        ]
    finally:
        session.close()


@router.get("/assessments/{assessment_type}", response_model=AssessmentDetail)
def assessment_detail(
    assessment_type: str,
    limit: int = Query(10, ge=1, le=50),
) -> AssessmentDetail:
    session = get_session()
    try:
        query = (
            session.query(AssessmentResult)
            .filter(AssessmentResult.assessment_type == assessment_type)
            .order_by(desc(AssessmentResult.timestamp))
            .limit(limit)
        )
        entries = query.all()
        if not entries:
            raise HTTPException(status_code=404, detail="No assessments found for this type.")
        parsed_entries = [
            AssessmentEntry(
                id=entry.id,
                total_score=entry.total_score,
                details=_parse_details(entry.details),
                timestamp=entry.timestamp,
            )
            for entry in entries
        ]
        return AssessmentDetail(assessment_type=assessment_type, entries=parsed_entries)
    finally:
        session.close()


@router.get("/questions", response_model=QuestionSetResponse)
def versioned_questions(
    assessment_type: str = Query(..., description="Assessment type for the question set"),
    version: str = Query(QuestionCurator.DEFAULT_VERSION, description="Version label", alias="version"),
    count: int = Query(10, ge=3, le=20, description="Number of questions desired"),
) -> QuestionSetResponse:
    available_versions = QuestionCurator.available_versions(assessment_type)
    if not available_versions:
        raise HTTPException(status_code=404, detail=f"Unknown assessment type '{assessment_type}'.")

    normalized_version = version.lower()
    if normalized_version not in available_versions:
        normalized_version = QuestionCurator.DEFAULT_VERSION

    questions = QuestionCurator.get_questions(assessment_type, count, normalized_version)
    if not questions:
        raise HTTPException(status_code=404, detail="Questions not available for the selected version.")

    metadata = QuestionCurator.version_metadata(assessment_type, normalized_version)
    description = metadata.get("description")
    released_on = metadata.get("released_on")

    return QuestionSetResponse(
        assessment_type=assessment_type,
        version=normalized_version,
        description=description,
        released_on=released_on,
        questions=questions,
        count=len(questions),
        available_versions=available_versions,
    )
