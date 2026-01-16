from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base


class PersonalProfile(Base):
    __tablename__ = "personal_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bio = Column(String, nullable=True)
    timeline = Column(String, nullable=True)
