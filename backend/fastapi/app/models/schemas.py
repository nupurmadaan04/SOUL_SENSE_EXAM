from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AssessmentSummary(BaseModel):
    assessment_type: str
    total_responses: int
    highest_score: Optional[int]
    average_score: Optional[float]
    latest_timestamp: Optional[str]


class AssessmentEntry(BaseModel):
    id: int
    total_score: int
    details: Dict[str, Any]
    timestamp: str


class AssessmentDetail(BaseModel):
    assessment_type: str
    entries: List[AssessmentEntry]


class QuestionSetResponse(BaseModel):
    assessment_type: str
    version: str
    description: Optional[str]
    released_on: Optional[str]
    questions: List[str]
    count: int
    available_versions: List[str]
