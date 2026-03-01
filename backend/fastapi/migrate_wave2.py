
import sqlite3
import os
import re

# ── Security note ────────────────────────────────────────────────────────────
# This migration script is run by developers/admins only.
# We still validate all DDL tokens against allowlists so that any accidental
# modification of the migrations list with unsafe values cannot produce
# injectable SQL.
# ─────────────────────────────────────────────────────────────────────────────

_SAFE_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

_ALLOWED_TYPES = {
    "INTEGER", "TEXT", "BOOLEAN", "VARCHAR", "REAL", "BLOB", "NUMERIC",
    "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT 1",
    "INTEGER DEFAULT 0", "INTEGER DEFAULT 1",
}


def _validate_ddl_tokens(table: str, column: str, col_type: str) -> None:
    """Raise ValueError if any DDL token fails allowlist checks."""
    if not _SAFE_IDENTIFIER_RE.match(table):
        raise ValueError(f"Unsafe table name: {table!r}")
    if not _SAFE_IDENTIFIER_RE.match(column):
        raise ValueError(f"Unsafe column name: {column!r}")
    if col_type.upper() not in _ALLOWED_TYPES:
        raise ValueError(f"Unsafe column type: {col_type!r}")


def migrate():
    db_path = "../../data/soulsense.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrations = [
        # Table: personal_profiles
        ("personal_profiles", "support_system",          "TEXT"),
        ("personal_profiles", "social_interaction_freq", "TEXT"),
        ("personal_profiles", "exercise_freq",           "TEXT"),
        ("personal_profiles", "dietary_patterns",        "TEXT"),

        # Table: user_settings
        ("user_settings", "decision_making_style",           "TEXT"),
        ("user_settings", "risk_tolerance",                  "INTEGER"),
        ("user_settings", "readiness_for_change",            "INTEGER"),
        ("user_settings", "advice_frequency",                "TEXT"),
        ("user_settings", "reminder_style",                  "TEXT"),
        ("user_settings", "advice_boundaries",               "TEXT"),
        ("user_settings", "ai_trust_level",                  "INTEGER"),
        ("user_settings", "data_usage_consent",              "BOOLEAN DEFAULT 0"),
        ("user_settings", "emergency_disclaimer_accepted",   "BOOLEAN DEFAULT 0"),
        ("user_settings", "crisis_support_preference",       "BOOLEAN DEFAULT 1"),

        # Table: user_strengths
        ("user_strengths", "short_term_goals",    "TEXT"),
        ("user_strengths", "long_term_vision",    "TEXT"),
        ("user_strengths", "primary_help_area",   "TEXT"),
        ("user_strengths", "relationship_stress", "INTEGER"),
    ]

    for table, column, col_type in migrations:
        try:
            # Security: validate all DDL tokens before interpolation
            _validate_ddl_tokens(table, column, col_type)

            # Check if column already exists
            cursor.execute("SELECT name FROM pragma_table_info(?)", (table,))
            existing_columns = [row[0] for row in cursor.fetchall()]

            if column not in existing_columns:
                print(f"Adding column {column} to {table}...")
                # Safe to interpolate — tokens were validated above
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"✅ Added {column}")
            else:
                print(f"ℹ️  Column {column} already exists in {table}")

        except ValueError as ve:
            print(f"❌ Security validation failed for {column} on {table}: {ve}")
        except Exception as e:
            print(f"❌ Error adding {column} to {table}: {e}")

    conn.commit()
    conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
