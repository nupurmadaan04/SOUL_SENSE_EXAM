from app.db import get_session
from app.models import Question, QuestionCategory

def seed_database():
    session = get_session()
    try:
        # Check if we have questions
        if session.query(Question).count() > 0:
            print("Database already has questions. Skipping seed.")
            return

        print("Seeding database with initial questions...")
        
        # 1. Categories
        categories = [
            QuestionCategory(name="Self-Awareness", description="Understanding your own emotions."),
            QuestionCategory(name="Self-Management", description="Managing your own emotions."),
            QuestionCategory(name="Social Awareness", description="Understanding others' emotions."),
            QuestionCategory(name="Relationship Management", description="Managing interactions with others.")
        ]
        
        # Check and add categories
        existing_cats = session.query(QuestionCategory).all()
        if not existing_cats:
            session.add_all(categories)
            session.commit()
            print("Added categories.")
        
        # 2. Questions
        questions = [
            Question(question_text="I recognize my emotions as I experience them.", category_id=1),
            Question(question_text="I lose my temper when I get frustrated.", category_id=2), # Reverse scored usually, but simplified here
            Question(question_text="I know when others are feeling sad or down.", category_id=3),
            Question(question_text="I can resolve conflicts effectively.", category_id=4),
            Question(question_text="I stay calm under pressure.", category_id=2),
            Question(question_text="I understand how my behavior affects others.", category_id=1),
            Question(question_text="I listen effectively to others.", category_id=3),
            Question(question_text="I help others manage their emotions.", category_id=4),
            Question(question_text="I am aware of my strengths and weaknesses.", category_id=1),
            Question(question_text="I find it difficult to handle change.", category_id=2)
        ]
        
        session.add_all(questions)
        session.commit()
        print(f"Added {len(questions)} questions.")
        
    except Exception as e:
        session.rollback()
        print(f"Seeding failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
