import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, UTC

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Mock environment variables
os.environ.setdefault("APP_ENV", "development")

from unittest.mock import MagicMock, AsyncMock

# Mock services before they are used
import api.services.websocket_manager
api.services.websocket_manager.manager = AsyncMock()

from api.services.encryption_service import current_dek
from api.services.db_service import AsyncSessionLocal, engine
from api.models import JournalEntry, Base, User
from api.ml.burnout_detection_service import BurnoutDetectionService
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Setup in-memory DB for pure logic testing
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def run_test():
    print("=== Testing Predictive Analytics for Emotional Burnout (#1133) ===")
    
    # Set DEK inside the async context
    DUMMY_DEK = b'\0' * 32
    current_dek.set(DUMMY_DEK)
    
    # Mock ProactiveInterventionService
    import api.ml.burnout_detection_service
    api.ml.burnout_detection_service.ProactiveInterventionService = MagicMock()
    api.ml.burnout_detection_service.ProactiveInterventionService.get_intervention_prompt = AsyncMock(return_value="Mocked Prompt")
    
    # Mock Kafka
    import api.services.kafka_producer
    api.services.kafka_producer.get_kafka_producer = MagicMock()
    api.services.kafka_producer.get_kafka_producer().queue_event = MagicMock()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSession() as db:
        # 1. Create a Test User
        user = User(username="burnout_tester", password_hash="dummy")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # 2. SEED BASELINE DATA (Last 10 days - Healthy Patterns)
        print("Seeding baseline data (10 days of healthy entries)...")
        for i in range(10):
            entry_date = (datetime.now(UTC) - timedelta(days=20-i)).strftime("%Y-%m-%d")
            # Stable mood (~75) and low stress (2-3)
            entry = JournalEntry(
                user_id=user.id,
                content=f"Day {i}: Feeling good overall.",
                sentiment_score=75.0 + (i % 3), 
                stress_level=3,
                entry_date=entry_date
            )
            db.add(entry)
        
        await db.commit()
        
        # 3. TEST SCENARIO: SUDDEN BURNOUT SPIKE
        print("Adding a 'Burnout' entry (Low sentiment, High stress)...")
        burnout_entry = JournalEntry(
            user_id=user.id,
            content="I am so exhausted. Everything is falling apart and I can't handle the pressure.",
            sentiment_score=15.0, # Huge drop from 75
            stress_level=10,      # Huge spike from 3
            entry_date=datetime.now(UTC).strftime("%Y-%m-%d")
        )
        db.add(burnout_entry)
        await db.commit()
        
        # 4. RUN ANALYTICS
        print("\n--- Running Burnout Detection Service ---")
        service = BurnoutDetectionService(db)
        alert_payload = await service.run_anomaly_detection(user.id)
        
        import json
        print(f"Result Payload:\n{json.dumps(alert_payload, indent=2)}")
        
        # Verification
        if alert_payload.get("is_crisis"):
            print("\n[SUCCESS] CRISIS_ALERT detected (Z-Score analysis working!)")
        elif alert_payload.get("is_burnout"):
            print("\n[SUCCESS] Burnout Warning detected.")
        else:
            print("\n[FAILURE] No anomaly detected despite severe data deviation.")

if __name__ == "__main__":
    asyncio.run(run_test())
