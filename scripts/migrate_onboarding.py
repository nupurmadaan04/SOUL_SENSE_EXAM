import sqlite3
import os

def migrate():
    db_path = 'data/soulsense.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if column exists first
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'onboarding_completed' not in columns:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0")
            conn.commit()
            print("Successfully added onboarding_completed column to user_settings table.")
        else:
            print("Column onboarding_completed already exists.")
            
    except sqlite3.OperationalError as e:
        print(f"Error migrating database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
