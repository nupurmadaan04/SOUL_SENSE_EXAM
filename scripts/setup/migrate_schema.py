import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/soulsense.db"))
if not os.path.exists(DB_PATH):
    print(f"Database {DB_PATH} not found. Skipped.")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def add_column_if_not_exists(table, column, definition):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding {column} to {table}: {e}")

# Columns to add to journal_entries
columns = [
    ("tags", "TEXT"),
    ("sleep_hours", "REAL"),
    ("sleep_quality", "INTEGER"),
    ("energy_level", "INTEGER"),
    ("work_hours", "REAL"),
    ("screen_time_mins", "INTEGER"),
    ("stress_level", "INTEGER"),
    ("stress_triggers", "TEXT"),
    ("daily_schedule", "TEXT")
]

print("Starting migration...")
for col, defn in columns:
    add_column_if_not_exists("journal_entries", col, defn)

conn.commit()
conn.close()
print("Migration completed.")
