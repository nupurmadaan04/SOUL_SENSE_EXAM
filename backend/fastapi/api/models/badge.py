from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from .base import Base

class Badge(Base):
    """Achievement badge definitions."""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(50), nullable=False)  # emoji or icon name
    category = Column(String(50), nullable=False)  # journal, eq_test, streak, growth
    milestone_type = Column(String(50), nullable=False)  # count, score, streak, improvement
    milestone_value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    user_badges = relationship("UserBadge", back_populates="badge")


class UserBadge(Base):
    """User-earned badges."""
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=lambda: datetime.now(UTC))
    progress = Column(Integer, default=0)  # current progress toward milestone
    unlocked = Column(Boolean, default=False)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge", back_populates="user_badges")
