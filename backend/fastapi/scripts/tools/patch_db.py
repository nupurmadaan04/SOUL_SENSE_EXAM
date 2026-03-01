
import sqlite3
import os
import re

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/soulsense.db"))

# ── Security note ────────────────────────────────────────────────────────────
# This migration script is run by developers/admins, never by end-users.
# Nevertheless, we enforce a strict allowlist on column names and types before
# interpolating them into DDL statements so that any future modification to
# `columns_to_add` cannot accidentally introduce injectable SQL.
# ─────────────────────────────────────────────────────────────────────────────

# Only valid SQL identifier characters (alphanumeric + underscore)
_SAFE_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
# Allowed DDL type tokens (extend as needed)
_ALLOWED_TYPES = {
    "INTEGER", "TEXT", "BOOLEAN", "VARCHAR", "REAL", "BLOB", "NUMERIC",
    "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT 1",
    "INTEGER DEFAULT 0", "INTEGER DEFAULT 1",
    "VARCHAR DEFAULT 'private'",
}


def _safe_ddl(col_name: str, col_type: str) -> str:
    """
    Validate column name and type against allowlists before constructing DDL.
    Raises ValueError if any token looks suspicious.
    """
    # Column name must be a simple SQL identifier
    if not _SAFE_IDENTIFIER_RE.match(col_name):
        raise ValueError(f"Unsafe column name rejected: {col_name!r}")
    # Type must match an explicitly allowed token
    if col_type.upper() not in _ALLOWED_TYPES:
        raise ValueError(f"Unsafe column type rejected: {col_type!r}")
    return f"ALTER TABLE journal_entries ADD COLUMN {col_name} {col_type};"


def patch_db():
    if not os.path.exists(db_path):
        print(f"❌ DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("📋 Patching journal_entries table...")
    columns_to_add = [
        ("user_id",       "INTEGER"),
        ("is_deleted",    "BOOLEAN DEFAULT 0"),
        ("word_count",    "INTEGER DEFAULT 0"),
        ("privacy_level", "VARCHAR DEFAULT 'private'"),
        ("tags",          "TEXT"),
    ]

    for col_name, col_type in columns_to_add:
        try:
            ddl = _safe_ddl(col_name, col_type)
            cursor.execute(ddl)
            print(f"  ✅ Added {col_name}")
        except ValueError as ve:
            print(f"  ❌ Security check failed for {col_name}: {ve}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"  ⚠️  {col_name} already exists")
            else:
                print(f"  ❌ Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("✨ DB Patch complete!")


if __name__ == "__main__":
    patch_db()

