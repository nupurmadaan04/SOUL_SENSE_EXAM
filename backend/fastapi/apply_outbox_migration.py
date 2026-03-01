import asyncio
import sys
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.join(os.getcwd(), 'backend', 'fastapi'))

from api.config import get_settings_instance

async def migrate():
    settings = get_settings_instance()
    engine = create_async_engine(settings.async_database_url)
    
    async with engine.begin() as conn:
        print("Checking for missing columns...")
        
        # Add columns to outbox_events
        try:
            await conn.execute(text("ALTER TABLE outbox_events ADD COLUMN processed_at DATETIME"))
            print("Added processed_at to outbox_events")
        except Exception:
            print("processed_at already exists or error adding")

        try:
            await conn.execute(text("ALTER TABLE outbox_events ADD COLUMN retry_count INTEGER DEFAULT 0"))
            print("Added retry_count to outbox_events")
        except Exception:
            print("retry_count already exists or error adding")

        try:
            await conn.execute(text("ALTER TABLE outbox_events ADD COLUMN error_message TEXT"))
            print("Added error_message to outbox_events")
        except Exception:
            print("error_message already exists")

        try:
            await conn.execute(text("ALTER TABLE outbox_events ADD COLUMN next_retry_at DATETIME"))
            print("Added next_retry_at to outbox_events")
        except Exception:
            print("next_retry_at already exists")

        # Add columns to journal_entries
        try:
            await conn.execute(text("ALTER TABLE journal_entries ADD COLUMN stress_triggers TEXT"))
            print("Added stress_triggers to journal_entries")
        except Exception:
            print("stress_triggers already exists or error adding")

    await engine.dispose()
    print("Migration check complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
