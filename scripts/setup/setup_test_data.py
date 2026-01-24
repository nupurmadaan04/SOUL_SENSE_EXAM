"""Create tables and sample data"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from app.db import check_db_state
from app.db import safe_db_context
from app.models import Score
from datetime import datetime, timedelta

# Create tables first
print("Creating database tables...")
check_db_state()

# Sample users and scores
sample_data = [
    {
        'username': 'test_user1',
        'scores': [
            {'total_score': 15, 'age': 25, 'days_ago': 1},
            {'total_score': 18, 'age': 25, 'days_ago': 3},
            {'total_score': 22, 'age': 25, 'days_ago': 7},
        ]
    },
    {
        'username': 'test_user2',
        'scores': [
            {'total_score': 12, 'age': 30, 'days_ago': 2},
            {'total_score': 16, 'age': 30, 'days_ago': 5},
        ]
    },
    {
        'username': 'alice',
        'scores': [
            {'total_score': 20, 'age': 28, 'days_ago': 0},
            {'total_score': 19, 'age': 28, 'days_ago': 4},
            {'total_score': 21, 'age': 28, 'days_ago': 10},
        ]
    }
]

with safe_db_context() as session:
    # Create sample scores
    for user_data in sample_data:
        username = user_data['username']
        
        for score_data in user_data['scores']:
            timestamp = (datetime.now() - timedelta(days=score_data['days_ago'])).isoformat()
            
            score = Score(
                username=username,
                total_score=score_data['total_score'],
                age=score_data['age'],
                sentiment_score=0.5,
                detailed_age_group='25-29' if score_data['age'] < 30 else '30-34',
                is_rushed=False,
                is_inconsistent=False,
                timestamp=timestamp
            )
            session.add(score)
    
    session.commit()
    
    # Verify
    total = session.query(Score).count()
    print(f"✓ Created {total} sample scores for testing")
    
    # Show sample
    print("\nSample scores:")
    for score in session.query(Score).limit(5).all():
        print(f"  - {score.username}: {score.total_score} (age: {score.age}, timestamp: {score.timestamp})")
