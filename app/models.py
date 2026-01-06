import logging

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


def ensure_journal_entries_schema(cursor):
    """Ensure journal_entries table exists"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        entry_date TEXT NOT NULL,
        content TEXT NOT NULL,
        sentiment_score REAL,
        emotional_patterns TEXT
    )
    """)
