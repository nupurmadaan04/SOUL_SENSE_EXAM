
import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/soulsense.db"))

def patch_db():
    if not os.path.exists(db_path):
        print(f"❌ DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("📋 Patching journal_entries table...")
    columns_to_add = [
        ("user_id", "INTEGER"),
        ("is_deleted", "BOOLEAN DEFAULT 0"),
        ("word_count", "INTEGER DEFAULT 0"),
        ("privacy_level", "VARCHAR DEFAULT 'private'"),
        ("tags", "TEXT")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE journal_entries ADD COLUMN {col_name} {col_type};")
            print(f"  ✅ Added {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"  ⚠️ {col_name} already exists")
            else:
                print(f"  ❌ Error adding {col_name}: {e}")

    # Add foreign key constraint is not supported in sqlite ALTER TABLE, 
    # but we can just use the column.

    conn.commit()
    conn.close()
    print("✨ DB Patch complete!")

if __name__ == "__main__":
    patch_db()
