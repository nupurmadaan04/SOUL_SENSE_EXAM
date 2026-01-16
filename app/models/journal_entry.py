
from sqlalchemy.sql import func
#from app.models.base import Base
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, String, Float

from sqlalchemy.orm import relationship
from app.models.base import Base

from .user import User  # <-- import User here only if needed for back_populates

class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    timestamp = Column(DateTime)

    sentiment_score = Column(Float)
    emotional_patterns = Column(String)

    entry_date = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="journal_entries")
