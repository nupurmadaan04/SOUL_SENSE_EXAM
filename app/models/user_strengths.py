from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base


class UserStrengths(Base):
    __tablename__ = "user_strengths"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strengths = Column(String, nullable=True)
    goals = Column(String, nullable=True)
