import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os
from datetime import datetime, timezone
UTC = timezone.utc

# Ensure both backend/fastapi and the project root are in sys.path
backend_fastapi_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_dir = os.path.abspath(os.path.join(backend_fastapi_dir, "..", ".."))

if backend_fastapi_dir not in sys.path:
    sys.path.insert(0, backend_fastapi_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from api.main import create_app
from api.services.db_service import get_db, Base
from api.root_models import Question, QuestionCategory, Score

@pytest.fixture(scope="session")
def test_engine():
    """Create a session-wide engine for the in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a new database session for a test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create a TestClient that uses the overridden db_session."""
    app = create_app()
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def seed_data(db_session):
    """Seed data for testing."""
    # Add a category
    cat = QuestionCategory(id=1, name="Emotional Intelligence")
    db_session.add(cat)
    
    # Add some questions
    q1 = Question(
        id=1,
        question_text="How do you feel today?",
        category_id=1,
        min_age=10,
        max_age=100,
        is_active=1,
        weight=1.0,
        created_at=datetime.now(UTC).isoformat()
    )
    q2 = Question(
        id=2,
        question_text="Do you like testing?",
        category_id=1,
        min_age=18,
        max_age=100,
        is_active=1,
        weight=1.0,
        created_at=datetime.now(UTC).isoformat()
    )
    db_session.add(q1)
    db_session.add(q2)
    
    # Add a sample score for stats
    s1 = Score(
        id=1,
        username="testuser",
        total_score=85,
        sentiment_score=0.75,
        age=25,
        detailed_age_group="Young Adult",
        timestamp=datetime.now(UTC).isoformat()
    )
    db_session.add(s1)
    
    db_session.commit()
import sys
import os
# Add the directory that contains the `api` package to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
