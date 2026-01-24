
import logging
import json
from app.db import get_session
from app.models import User, UserStrengths

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def verify_strengths():
    session = get_session()
    TEST_USER = "test_verification_user"
    
    try:
        logging.info("--- Starting Verification: User Strengths ---")
        
        # 1. Create/Get User
        user = session.query(User).filter_by(username=TEST_USER).first()
        if not user:
            logging.info(f"Creating test user: {TEST_USER}")
            user = User(username=TEST_USER, password_hash="dummy")
            session.add(user)
            session.commit()
            
        # 2. Add Strengths Profile
        if user.strengths:
            session.delete(user.strengths)
            session.commit()
            logging.info("Cleared existing strengths profile.")
            
        logging.info("Creating new UserStrengths profile...")
        strengths = UserStrengths(user_id=user.id)
        
        # Test Data
        top_strengths = ["Resilience", "Coding", "Empathy"]
        improvements = ["Public Speaking"]
        boundaries = ["Politics", "Religion"]
        
        strengths.top_strengths = json.dumps(top_strengths)
        strengths.areas_for_improvement = json.dumps(improvements)
        strengths.sharing_boundaries = json.dumps(boundaries)
        strengths.learning_style = "Visual"
        strengths.communication_preference = "Direct"
        strengths.goals = "Become a Senior Engineer"
        
        user.strengths = strengths
        session.commit()
        logging.info("Saved strengths profile.")
        
        # 3. Verify Persistence
        session.expire_all()
        refreshed_user = session.query(User).filter_by(username=TEST_USER).first()
        s = refreshed_user.strengths
        
        # Check Fields
        assert s is not None, "Strengths profile not found!"
        assert s.learning_style == "Visual", f"Expected Visual, got {s.learning_style}"
        assert s.goals == "Become a Senior Engineer", "Goals mismatch"
        
        # Check JSON deserialization
        loaded_strengths = json.loads(s.top_strengths)
        assert "Coding" in loaded_strengths, "Failed to load JSON tag: Coding"
        assert len(loaded_strengths) == 3, "Length mismatch in strengths"
        
        logging.info("✅ Persistence Check Passed!")
        
        # 4. Cleanup
        # session.delete(user)
        # session.commit()
        logging.info("Test Complete.")
        
    except Exception as e:
        logging.error(f"❌ Verification Failed: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    verify_strengths()
