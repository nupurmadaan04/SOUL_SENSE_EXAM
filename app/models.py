from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    last_login = Column(String, nullable=True)

    # Relationships
    scores = relationship("Score", back_populates="user")
    responses = relationship("Response", back_populates="user")

class Score(Base):
    __tablename__ = 'scores'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    total_score = Column(Integer)
    age = Column(Integer)
    detailed_age_group = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    user = relationship("User", back_populates="scores")

class Response(Base):
    __tablename__ = 'responses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    question_id = Column(Integer)
    response_value = Column(Integer)
    age_group = Column(String)
    detailed_age_group = Column(String)
    timestamp = Column(String, default=lambda: datetime.utcnow().isoformat())
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    user = relationship("User", back_populates="responses")

class QuestionCategory(Base):
    __tablename__ = 'question_category'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)

class Question(Base):
    __tablename__ = 'question_bank'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    category_id = Column(Integer, default=0)
    difficulty = Column(Integer, default=1)
    min_age = Column(Integer, default=0)
    max_age = Column(Integer, default=120)
    weight = Column(Float, default=1.0)
    is_active = Column(Integer, default=1)
    tooltip = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

class QuestionMetadata(Base):
    __tablename__ = 'question_metadata'
    
    question_id = Column(Integer, primary_key=True) # Assuming 1:1 map or just metadata
    source = Column(String)
    version = Column(String)
    tags = Column(String)

class JournalEntry(Base):
    __tablename__ = 'journal_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    entry_date = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    content = Column(Text)
    sentiment_score = Column(Float)
    emotional_patterns = Column(Text)
