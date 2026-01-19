from app.db import get_session
from app.models import User, UserStrengths
import json
import time

def verify():
    print("Verifying Issue #271 - Persistence Check...")
    session = get_session()
    
    unique_user = f"verify_271_{int(time.time())}"
    print(f"Creating test user: {unique_user}")
    
    try:
        # Create User
        user = User(username=unique_user, password_hash="test")
        session.add(user)
        session.commit()
        
        # Add Strengths with Challenges
        challenges = ["Burnout", "Focus"]
        strengths = UserStrengths(
            user_id=user.id,
            top_strengths=json.dumps(["Coding"]),
            current_challenges=json.dumps(challenges)
        )
        session.add(strengths)
        session.commit()
        
        # Retrieve and Verify
        session.refresh(strengths)
        saved_challenges = json.loads(strengths.current_challenges)
        
        print(f"Saved: {challenges}")
        print(f"Retrieved: {saved_challenges}")
        
        if saved_challenges == challenges:
            print("SUCCESS: Challenges saved and retrieved correctly.")
        else:
            print("FAILURE: Data mismatch.")
            exit(1)
            
        # Clean up
        session.delete(strengths)
        session.delete(user)
        session.commit()
        
    except Exception as e:
        print(f"ERROR: {e}")
        session.rollback()
        exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    verify()
