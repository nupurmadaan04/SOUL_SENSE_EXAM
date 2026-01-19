import sqlite3
import random
from datetime import datetime, timedelta
import os
import sys

# Add the parent directory to sys.path to allow imports from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.auth import AuthManager
from app.config import DB_PATH

# Initialize AuthManager
auth_manager = AuthManager()

def get_db():
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    return sqlite3.connect(DB_PATH)

def init_db():
    # Helper to ensure tables exist if not running via main app first
    # For now, we assume schema exists via alembic
    pass

def seed_data():
    conn = get_db()
    cursor = conn.cursor()
    
    print("Seeding database with synthetic users...")
    
    # Create 110 users to be safe (>100)
    for i in range(1, 111):
        username = f"user_{i}"
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            continue
            
        # Create User
        pwd_hash = auth_manager.hash_password("password123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, pwd_hash, datetime.utcnow().isoformat())
        )
        user_id = cursor.lastrowid
        
        # Simulate different personas for realistic data
        # Persona A: High Risk (Low Score, Negative Sentiment)
        # Persona B: Low Risk (High Score, Positive Sentiment)
        # Persona C: Medium (Average)
        
        persona = random.choice(['A', 'B', 'B', 'C', 'C', 'C']) 
        
        if persona == 'A':
            score = random.randint(10, 24)
            sentiment = random.uniform(-0.9, -0.3)
            age = random.randint(18, 25)
        elif persona == 'B':
            score = random.randint(36, 50)
            sentiment = random.uniform(0.3, 0.9)
            age = random.randint(25, 40)
        else:
            score = random.randint(25, 35)
            sentiment = random.uniform(-0.3, 0.3)
            age = random.randint(20, 60)
            
        # Insert Score
        cursor.execute(
            """INSERT INTO scores 
               (username, total_score, age, detailed_age_group, user_id, timestamp) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, score, age, "Adult", user_id, datetime.utcnow().isoformat())
        )
        
        # Insert Journal Entry (Simulated)
        cursor.execute(
            """INSERT INTO journal_entries 
               (username, entry_date, content, sentiment_score, user_id) 
               VALUES (?, ?, ?, ?, ?)""",
            (username, datetime.utcnow().isoformat(), "Synthetic Content", sentiment, user_id)
        )
        
    conn.commit()
    print("Successfully seeded 110 records.")
    conn.close()

if __name__ == "__main__":
    seed_data()
