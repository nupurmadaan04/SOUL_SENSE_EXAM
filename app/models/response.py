from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    question_id = Column(Integer, nullable=False)
    answer = Column(Integer, nullable=False)
