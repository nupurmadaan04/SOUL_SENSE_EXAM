from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base

class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    risk_level = Column(String, nullable=False)
    confidence = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
