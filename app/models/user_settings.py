from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    theme = Column(String, default="light")
    question_count = Column(Integer, default=10)
    sound_enabled = Column(Boolean, default=True)
    notifications_enabled = Column(Boolean, default=True)
    language = Column(String, default="en")

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
