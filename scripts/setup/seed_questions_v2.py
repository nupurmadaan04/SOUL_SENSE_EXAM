import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.db import get_session
from app.models import Question
import os

TXT_PATH = os.path.join("data", "question_bank.txt")

def seed():
    session = get_session()
    try:
        if not os.path.exists(TXT_PATH):
            print(f"Error: {TXT_PATH} not found.")
            return

        with open(TXT_PATH, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        
        # Check if empty
        count = session.query(Question).count()
        if count > 0:
            print(f"Questions already exist ({count}). Skipping.")
            return

        questions = []
        for line in lines:
            # Set default age range suitable for the app
            q = Question(question_text=line, min_age=16, max_age=100) 
            questions.append(q)
        
        session.add_all(questions)
        session.commit()
        print(f"Successfully seeded {len(questions)} questions.")
    except Exception as e:
        print(f"Error seeding questions: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed()
