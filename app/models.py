import logging
import hashlib

def ensure_users_schema(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    return hash_password(password) == password_hash

def ensure_scores_schema(cursor):
    cursor.execute("PRAGMA table_info(scores)")
    cols = [c[1] for c in cursor.fetchall()]
    if cols and "age" not in cols:
        logging.info("Migrating scores table: adding age column")
        cursor.execute("ALTER TABLE scores ADD COLUMN age INTEGER")


def ensure_responses_schema(cursor):
    cursor.execute("PRAGMA table_info(responses)")
    cols = [c[1] for c in cursor.fetchall()]

    if not cols:
        cursor.execute("""
        CREATE TABLE responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            question_id INTEGER,
            response_value INTEGER,
            age_group TEXT,
            timestamp TEXT
        )
        """)
    else:
        required = {
            "username": "TEXT",
            "question_id": "INTEGER",
            "response_value": "INTEGER",
            "age_group": "TEXT",
            "timestamp": "TEXT"
        }
        for col, t in required.items():
            if col not in cols:
                cursor.execute(f"ALTER TABLE responses ADD COLUMN {col} {t}")


def ensure_question_bank_schema(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_bank (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)
