import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, MedicalProfile, PersonalProfile, UserSettings

# Use temp_db fixture from conftest.py
# (No local db_session fixture needed)

def test_user_profile_relationships(temp_db):
    # 1. Create User
    user = User(username="test_profile", password_hash="hash")
    temp_db.add(user)
    temp_db.commit()
    
    # 2. Add Profiles
    med_profile = MedicalProfile(user_id=user.id, blood_type="O+", allergies="None")
    pers_profile = PersonalProfile(user_id=user.id, occupation="Dev", hobbies="Coding")
    settings = UserSettings(user_id=user.id, theme="dark")
    
    temp_db.add_all([med_profile, pers_profile, settings])
    temp_db.commit()
    
    # 3. Verify Relationships
    reloaded_user = temp_db.query(User).filter_by(username="test_profile").first()
    assert reloaded_user is not None
    assert reloaded_user.medical_profile.blood_type == "O+"
    assert reloaded_user.personal_profile.occupation == "Dev"
    assert reloaded_user.settings.theme == "dark"

def test_cascade_delete(temp_db):
    # Create user with profile
    user = User(username="delete_me", password_hash="hash")
    temp_db.add(user)
    temp_db.commit()
    
    med = MedicalProfile(user_id=user.id)
    temp_db.add(med)
    temp_db.commit()
    
    # Verify existence
    assert temp_db.query(MedicalProfile).filter_by(user_id=user.id).count() == 1
    
    # Delete User
    temp_db.delete(user)
    temp_db.commit()
    
    # Verify Cascade
    assert temp_db.query(MedicalProfile).filter_by(user_id=user.id).count() == 0

def test_invalid_profile_data(temp_db):
    # Test handling of nullable fields
    user = User(username="null_test", password_hash="hash")
    temp_db.add(user)
    temp_db.commit()
    
    # Create empty profile
    med = MedicalProfile(user_id=user.id) # All fields nullable except ID/UserID
    temp_db.add(med)
    temp_db.commit()
    
    assert med.blood_type is None
    # Ensure it doesn't crash
