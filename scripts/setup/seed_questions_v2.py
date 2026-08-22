import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.fastapi.api.models import Base, Question, QuestionCategory

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/soulsense.db"))
TXT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/question_bank.txt"))

CATEGORIES = [
    (1, "Self-Awareness"),
    (2, "Self-Regulation"),
    (3, "Motivation"),
    (4, "Empathy"),
    (5, "Social Skills"),
]

def seed():
    engine = create_engine(f"sqlite:///{DB_PATH}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # 1. Seed Categories
        for cat_id, cat_name in CATEGORIES:
            existing_cat = session.query(QuestionCategory).filter_by(id=cat_id).first()
            if not existing_cat:
                category = QuestionCategory(id=cat_id, name=cat_name)
                session.add(category)
        session.commit()
        print("Categories seeded successfully.")

        # 2. Seed Questions
        if not os.path.exists(TXT_PATH):
            print(f"Error: {TXT_PATH} not found.")
            return

        with open(TXT_PATH, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        existing_count = session.query(Question).count()
        if existing_count > 0:
            print(f"Questions already exist ({existing_count}). Checking category linkage.")
            # Update any missing category_ids
            all_qs = session.query(Question).all()
            for idx, q in enumerate(all_qs):
                if not q.category_id:
                    q.category_id = (idx % 5) + 1
                    q.is_active = 1
            session.commit()
            print("Question category linkages verified.")
            return

        questions = []
        for idx, line in enumerate(lines):
            category_id = (idx % 5) + 1
            q = Question(
                question_text=line,
                category_id=category_id,
                difficulty=1,
                is_active=1,
                min_age=0,
                max_age=120,
                weight=1.0
            )
            questions.append(q)

        session.add_all(questions)
        session.commit()
        print(f"Successfully seeded {len(questions)} questions into question_bank.")

    except Exception as e:
        print(f"Error seeding questions: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed()
