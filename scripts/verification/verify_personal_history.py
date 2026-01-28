import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.db import get_session
from app.models import User, PersonalProfile
# from app.db import init_db # Not needed, auto-inits

def verify_personal_history():
    print("--- Verifying Personal History Module ---")
    
    # 1. Setup DB
    # init_db() # Removed
    session = get_session()
    
    try:
        # 2. Get or Create Test User
        username = "history_test_user"
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print(f"Creating test user: {username}")
            user = User(username=username, password_hash="dummy")
            session.add(user)
            session.commit()
            
        # 3. Create Personal Profile
        print("Creating Personal Profile...")
        if user.personal_profile:
            session.delete(user.personal_profile)
            session.commit()
            
        profile = PersonalProfile(user_id=user.id)
        user.personal_profile = profile
        
        # 4. Set Bio and Occupation
        profile.occupation = "Software Engineer"
        profile.bio = "Coding enthusiast."
        profile.hobbies = json.dumps(["Chess", "Hiking"])
        
        # 5. Add Life Events (JSON)
        events = [
            {"date": "2020-05-15", "title": "Graduation", "description": "BS in CS"},
            {"date": "2021-08-01", "title": "First Job", "description": "Junior Dev"}
        ]
        profile.life_events = json.dumps(events)
        
        session.commit()
        print("✅ Data saved successfully.")
        
        # 6. Verify Fetch
        session.refresh(user)
        p = user.personal_profile
        
        assert p.occupation == "Software Engineer", "Occupation mismatch"
        assert "Chess" in p.hobbies, "Hobbies JSON mismatch"
        
        loaded_events = json.loads(p.life_events)
        assert len(loaded_events) == 2, "Events count mismatch"
        assert loaded_events[0]["title"] == "Graduation", "Event 1 title mismatch"
        
        print("✅ Data fetching & JSON serialization verified.")
        
        # 7. Verify Timeline Sorting Logic (Simulated)
        unsorted_events = [
            {"date": "2022-01-01", "title": "Future"},
            {"date": "2000-01-01", "title": "Past"}
        ]
        unsorted_events.sort(key=lambda x: x['date'], reverse=True)
        assert unsorted_events[0]["title"] == "Future", "Sorting logic failed"
        assert unsorted_events[1]["title"] == "Past", "Sorting logic failed"
        
        print("✅ Logic verification passed.")
        
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    verify_personal_history()
