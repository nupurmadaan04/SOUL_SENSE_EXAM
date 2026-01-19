import sqlite3
import os
import sys

# Define path to DB
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "soulsense.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Skipping migration.")
        return

    print(f"Migrating database at {DB_PATH}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(user_strengths)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "current_challenges" in columns:
            print("Column 'current_challenges' already exists. Skipping.")
        else:
            print("Adding column 'current_challenges' to 'user_strengths'...")
            cursor.execute("ALTER TABLE user_strengths ADD COLUMN current_challenges TEXT DEFAULT '[]'")
            conn.commit()
            print("Migration successful.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
