from sqlalchemy import Column, Integer, String, ForeignKey
from app.models.base import Base


class MedicalProfile(Base):
    __tablename__ = "medical_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    allergies = Column(String, nullable=True)
    conditions = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
