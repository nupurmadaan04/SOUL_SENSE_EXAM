from sqlalchemy import Column, Integer, Text, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.models import Base


class UserReflection(Base):
    __tablename__ = "user_reflections"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Issue #260: User's perspective on life (POV)
    pov_text = Column(Text, nullable=True)
    pov_sentiment = Column(Float, nullable=True)

    # Issue #271: User challenges / weaknesses
    challenges_text = Column(Text, nullable=True)
    challenges_sentiment = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
