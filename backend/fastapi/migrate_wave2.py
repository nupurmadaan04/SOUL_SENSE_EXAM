
import sqlite3
import os

def migrate():
    db_path = "../../data/soulsense.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrations = [
        # Table: personal_profiles
        ("personal_profiles", "support_system", "TEXT"),
        ("personal_profiles", "social_interaction_freq", "TEXT"),
        ("personal_profiles", "exercise_freq", "TEXT"),
        ("personal_profiles", "dietary_patterns", "TEXT"),
        
        # Table: user_settings
        ("user_settings", "decision_making_style", "TEXT"),
        ("user_settings", "risk_tolerance", "INTEGER"),
        ("user_settings", "readiness_for_change", "INTEGER"),
        ("user_settings", "advice_frequency", "TEXT"),
        ("user_settings", "reminder_style", "TEXT"),
        ("user_settings", "advice_boundaries", "TEXT"),
        ("user_settings", "ai_trust_level", "INTEGER"),
        ("user_settings", "data_usage_consent", "BOOLEAN DEFAULT 0"),
        ("user_settings", "emergency_disclaimer_accepted", "BOOLEAN DEFAULT 0"),
        ("user_settings", "crisis_support_preference", "BOOLEAN DEFAULT 1"),
        
        # Table: user_strengths
        ("user_strengths", "short_term_goals", "TEXT"),
        ("user_strengths", "long_term_vision", "TEXT"),
        ("user_strengths", "primary_help_area", "TEXT"),
        ("user_strengths", "relationship_stress", "INTEGER"),
    ]

    for table, column, col_type in migrations:
        try:
            # Check if column exists
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            
            if column not in columns:
                print(f"Adding column {column} to {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"✅ Added {column}")
            else:
                print(f"ℹ️ Column {column} already exists in {table}")
        except Exception as e:
            print(f"❌ Error adding {column} to {table}: {e}")

    conn.commit()
    conn.close()
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate()
