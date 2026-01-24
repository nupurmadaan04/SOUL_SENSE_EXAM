import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from app.db import safe_db_context
from app.models import Score
from sqlalchemy import func

with safe_db_context() as session:
    count = session.query(func.count(Score.id)).scalar()
    print(f"Total scores in database: {count}")
    if count > 0:
        sample = session.query(Score).limit(3).all()
        print("\nSample scores:")
        for s in sample:
            print(f"  - {s.username}: {s.total_score} (timestamp: {s.timestamp})")
