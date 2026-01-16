from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class StatisticsCache(Base):
    __tablename__ = "statistics_cache"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)

    updated_at = Column(DateTime(timezone=True), server_default=func.now())
