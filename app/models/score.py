from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    age = Column(Integer)
    total_score = Column(Integer)

    sentiment_score = Column(Float, default=0.0)
    reflection_text = Column(String)

    is_rushed = Column(Boolean, default=False)
    is_inconsistent = Column(Boolean, default=False)

    detailed_age_group = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="scores")
