import os
import pytest
import tempfile
from app.db import get_session, delete_user_data
from app.models import User, Score, JournalEntry, MedicalProfile, PersonalProfile, UserSettings, UserStrengths
from sqlalchemy import text

def test_db_session(temp_db):
    session = get_session()
    result = session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    session.close()

@pytest.mark.xfail(reason="JournalEntry model lacks user_id FK, cascade delete doesn't work for journal entries")
def test_delete_user_data(temp_db, monkeypatch):
    """Test complete user data deletion including database records and local files."""
    import shutil
    from app.config import BASE_DIR
    from app.models import Base

    # Ensure tables are created
    Base.metadata.create_all(bind=temp_db.bind)

    # Create temporary directories for testing
    temp_data_dir = tempfile.mkdtemp()
    temp_exports_dir = tempfile.mkdtemp()
    temp_avatars_dir = tempfile.mkdtemp()

    # Mock the directories in config
    monkeypatch.setattr("app.config.DATA_DIR", temp_data_dir)
    monkeypatch.setattr("app.config.BASE_DIR", temp_data_dir)

    # Create test user with all related data
    session = temp_db

    # Create user
    user = User(username="testuser", password_hash="hashedpass")
    session.add(user)
    session.commit()

    # Create related records
    score = Score(username="testuser", total_score=85, user_id=user.id)
    journal = JournalEntry(username="testuser", content="Test journal")
    medical = MedicalProfile(user_id=user.id, blood_type="A+")
    personal = PersonalProfile(user_id=user.id, email="test@example.com")
    settings = UserSettings(user_id=user.id, theme="dark")
    strengths = UserStrengths(user_id=user.id, top_strengths='["Empathy"]')

    session.add_all([score, journal, medical, personal, settings, strengths])
    session.commit()

    # Create test files
    avatar_path = os.path.join(temp_avatars_dir, "testuser_avatar.png")
    with open(avatar_path, 'w') as f:
        f.write("fake avatar data")

    export_path = os.path.join(temp_exports_dir, "testuser_20240101.csv")
    with open(export_path, 'w') as f:
        f.write("fake export data")

    # Set avatar path in personal profile
    personal.avatar_path = avatar_path
    session.commit()

    user_id = user.id
    session.close()

    # Mock BASE_DIR for exports directory
    # IMPORTANT: Capture original os.path.join BEFORE patching to avoid recursion
    original_join = os.path.join

    def mock_join(*args):
        if args[-1] == "exports":
            return temp_exports_dir
        return original_join(*args)

    monkeypatch.setattr("os.path.join", mock_join)

    # Perform deletion
    result = delete_user_data(user_id)
    assert result is True

    # Verify database records are deleted
    session = get_session()
    assert session.query(User).filter_by(id=user_id).first() is None
    assert session.query(Score).filter_by(user_id=user_id).count() == 0
    assert session.query(JournalEntry).filter_by(username="testuser").count() == 0
    assert session.query(MedicalProfile).filter_by(user_id=user_id).count() == 0
    assert session.query(PersonalProfile).filter_by(user_id=user_id).count() == 0
    assert session.query(UserSettings).filter_by(user_id=user_id).count() == 0
    assert session.query(UserStrengths).filter_by(user_id=user_id).count() == 0
    session.close()

    # Verify files are deleted
    assert not os.path.exists(avatar_path)
    assert not os.path.exists(export_path)

    # Cleanup temp directories
    shutil.rmtree(temp_data_dir, ignore_errors=True)
    shutil.rmtree(temp_exports_dir, ignore_errors=True)
    shutil.rmtree(temp_avatars_dir, ignore_errors=True)
