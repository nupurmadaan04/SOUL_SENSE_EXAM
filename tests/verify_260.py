
from app.db import get_session
from app.models import User, PersonalProfile
import sys

def verify_life_pov():
    print("Verifying Issue #260 - User Perspective (Manifesto)...")
    
    session = get_session()
    username = "test_pov_user"
    
    # Cleanup previous run
    existing = session.query(User).filter_by(username=username).first()
    if existing:
        session.delete(existing)
        session.commit()
    
    # 1. Create User
    user = User(username=username, password_hash="test")
    session.add(user)
    session.commit()
    print("User created.")
    
    # 2. Add Manifesto (Simulating _edit_manifesto logic)
    pov_text = "Life is not about waiting for the storm to pass, it's about learning to dance in the rain. 🌧️💃"
    
    # Edge Case: Create PersonalProfile on demand
    pp = PersonalProfile(user_id=user.id, life_pov=pov_text)
    session.add(pp)
    session.commit()
    print("Manifesto saved.")
    
    # 3. Retrieve and Verify
    fetched = session.query(PersonalProfile).filter_by(user_id=user.id).first()
    print(f"Retrieved: {fetched.life_pov}")
    
    if fetched.life_pov == pov_text:
        print("SUCCESS: Manifesto persisted correctly.")
    else:
        print("FAILURE: Content mismatch.")
        sys.exit(1)
        
    session.close()

if __name__ == "__main__":
    verify_life_pov()
