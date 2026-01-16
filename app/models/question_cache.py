from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class QuestionCache(Base):
    __tablename__ = "question_cache"

    id = Column(Integer, primary_key=True)
    data_hash = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
