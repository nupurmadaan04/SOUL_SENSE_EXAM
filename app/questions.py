from app.db import get_session
from app.models import Question

def load_questions(
    age: int | str | None = None,
    db_path: str | None = None
):
    """
    Load questions from DB using ORM.
    Returns list of (id, question_text) tuples.
    """
    # Backward compat: ignore db_path as we use centralized session
    if isinstance(age, str) and db_path is None:
        age = None
        
    session = get_session()
    try:
        query = session.query(Question).filter(Question.is_active == 1)
        
        if age is not None:
            query = query.filter(Question.min_age <= age, Question.max_age >= age)
            
        questions = query.order_by(Question.id).all()
        
        # Return as list of tuples with tooltip
        # (id, question_text, tooltip)
        rows = [(q.id, q.question_text, q.tooltip) for q in questions]
        
        if not rows:
            # Fallback: if strict age filtering returns nothing, maybe return all?
            # Or keep raising error as before.
            # Original behavior raised RuntimeError
            raise RuntimeError("No questions found in database")
            
        return rows
    finally:
        session.close()
