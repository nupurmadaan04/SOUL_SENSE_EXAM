import sqlite3
import os
import sys

# Add backend/fastapi to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend/fastapi")))

from api.models import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text

def sync_schema(db_path="data/soulsense.db"):
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for table_name, table in Base.metadata.tables.items():
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"Table {table_name} does not exist, creating...")
            continue

        # Get existing columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_cols = {row[1]: row for row in cursor.fetchall()}

        for col in table.columns:
            if col.name not in existing_cols:
                # Determine SQLite column type
                col_type = "TEXT"
                python_type = getattr(col.type, "python_type", None)
                if isinstance(col.type, Integer) or python_type is int:
                    col_type = "INTEGER"
                elif isinstance(col.type, Boolean) or python_type is bool:
                    col_type = "BOOLEAN"
                elif isinstance(col.type, Float) or python_type is float:
                    col_type = "REAL"
                
                default_clause = ""
                if col.default is not None and hasattr(col.default, 'arg') and not callable(col.default.arg):
                    val = col.default.arg
                    if isinstance(val, bool):
                        default_clause = f" DEFAULT {1 if val else 0}"
                    elif isinstance(val, (int, float)):
                        default_clause = f" DEFAULT {val}"
                    elif isinstance(val, str):
                        default_clause = f" DEFAULT '{val}'"

                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}"
                print(f"  Adding column {table_name}.{col.name} ({col_type})...")
                try:
                    cursor.execute(alter_sql)
                except Exception as e:
                    print(f"    Error adding {table_name}.{col.name}: {e}")

    conn.commit()
    conn.close()
    print("Schema synchronization complete!")

if __name__ == "__main__":
    sync_schema()
