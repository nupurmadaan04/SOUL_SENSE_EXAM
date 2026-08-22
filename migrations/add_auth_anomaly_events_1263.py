"""
Add auth_anomaly_events table for #1263.
Creates auth_anomaly_events table to track authentication anomalies.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text


def run_migration():
    """Create the auth_anomaly_events table and necessary columns."""
    from app.db import engine
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS auth_anomaly_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        anomaly_type VARCHAR NOT NULL,
        risk_level VARCHAR NOT NULL,
        risk_score FLOAT NOT NULL,
        ip_address VARCHAR NOT NULL,
        user_agent VARCHAR,
        triggered_rules TEXT,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS ix_auth_anomaly_events_user_id ON auth_anomaly_events (user_id);",
        "CREATE INDEX IF NOT EXISTS ix_auth_anomaly_events_anomaly_type ON auth_anomaly_events (anomaly_type);",
        "CREATE INDEX IF NOT EXISTS ix_auth_anomaly_events_created_at ON auth_anomaly_events (created_at);",
        "CREATE INDEX IF NOT EXISTS ix_auth_anomaly_events_risk_level ON auth_anomaly_events (risk_level);"
    ]
    
    with engine.connect() as conn:
        print("Creating auth_anomaly_events table...")
        conn.execute(text(create_table_sql))
        conn.commit()
        
        # Check login_attempts table columns
        try:
            res = conn.execute(text("PRAGMA table_info(login_attempts);")).fetchall()
            col_names = [r[1] for r in res]
            if "user_id" not in col_names:
                conn.execute(text("ALTER TABLE login_attempts ADD COLUMN user_id INTEGER REFERENCES users(id);"))
                conn.commit()
        except Exception as e:
            print(f"Note on login_attempts: {e}")
            
        for index_sql in create_indexes_sql:
            try:
                conn.execute(text(index_sql))
                conn.commit()
            except Exception:
                pass
        print("✓ auth_anomaly_events migration completed.")


if __name__ == "__main__":
    run_migration()