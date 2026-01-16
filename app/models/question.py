from sqlalchemy import Column, Integer, String, Float
from app.models.base import Base

class Question(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    category = Column(String)
    min_age = Column(Integer)
    max_age = Column(Integer)
    weight = Column(Float, default=1.0)
