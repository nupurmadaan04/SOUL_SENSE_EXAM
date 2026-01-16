from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class SatisfactionRecord(Base):
    __tablename__ = "satisfaction_records"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    score = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
