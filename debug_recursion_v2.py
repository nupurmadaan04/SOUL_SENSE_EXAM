import sys
import os
import shutil
import tempfile
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock environment
from app.models import Base, User
import app.db

def run():
    print("Starting debug run...")
    try:
        # Setup in-memory DB
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        TestSession = sessionmaker(bind=engine)
        
        # Monkeypatch app.db
        app.db.SessionLocal = TestSession
        app.db.engine = engine
        
        # NOTE: app.db.get_session is NOT monkeypatched here, testing if safe_db_context uses SessionLocal
        
        # Create user
        session = TestSession()
        user = User(username="debuguser", password_hash="pass")
        session.add(user)
        session.commit()
        user_id = user.id
        session.close()
        
        print(f"User created with ID {user_id}")
        
        # Call delete_user_data
        print("Calling delete_user_data...")
        app.db.delete_user_data(user_id)
        print("delete_user_data finished successfully.")
        
    except RecursionError:
        print("RecursionError CAUGHT!")
        traceback.print_exc()
    except Exception as e:
        print(f"Other error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run()
