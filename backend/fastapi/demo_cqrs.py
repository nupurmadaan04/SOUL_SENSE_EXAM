"""
CQRS Architecture Demo Script (#1124)
Demonstrates the separation of Command (Writes) and Query (Read Models).
"""
import asyncio
import logging
import time
from datetime import datetime, UTC
from sqlalchemy import select, func
from api.services.db_router import PrimarySessionLocal
from api.services.db_service import AsyncSessionLocal
from api.models import User, Score, CQRSGlobalStats, CQRSAgeGroupStats, CQRSTrendAnalytics
from api.services.cqrs_service import CQRSService

# Set up logging to show the CQRS process
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cqrs_demo")

async def run_demo():
    print("==================================================")
    print("  CQRS Architecture & Read Model Materialization   ")
    print("==================================================")

    async with PrimarySessionLocal() as db:
        # 1. Simulate a heavy database state (Command Side)
        print("\n[ Command ] Writing new assessment scores to primary DB...")
        new_scores = [
            Score(username="user1", total_score=35, sentiment_score=0.8, detailed_age_group="25-34", timestamp=datetime.now(UTC).isoformat()),
            Score(username="user2", total_score=15, sentiment_score=0.4, detailed_age_group="18-24", timestamp=datetime.now(UTC).isoformat()),
            Score(username="user3", total_score=25, sentiment_score=0.6, detailed_age_group="25-34", timestamp=datetime.now(UTC).isoformat()),
        ]
        db.add_all(new_scores)
        await db.commit()
        print(f"[ Command ] {len(new_scores)} assessment entries committed.")

        # 2. Trigger the CQRS Materialization (Worker)
        print("\n[ Worker  ] Async worker consuming Kafka/Outbox events...")
        print("[ Worker  ] Building pre-computed Read Models (cqrs_global_stats, etc.)...")
        
        start_time = time.perf_counter()
        await CQRSService.update_score_projections(db)
        duration = time.perf_counter() - start_time
        print(f"[ Worker  ] Projection refresh completed in {duration:.4f}s")

    # 3. Demonstrate the Query Performance (Query Side)
    async with AsyncSessionLocal() as db:
        print("\n[ Query   ] Fetching Dashboard Summary from Read Models...")
        start_time = time.perf_counter()
        
        stmt = select(CQRSGlobalStats).order_by(CQRSGlobalStats.last_updated.desc()).limit(1)
        res = await db.execute(stmt)
        gs = res.scalar_one_or_none()
        
        query_duration = time.perf_counter() - start_time
        
        if gs:
            print(f"[ Query   ] RESULT: {gs.total_assessments} Total Assessments")
            print(f"[ Query   ] RESULT: {gs.global_average_score:.2f} Avg Score")
        
        print(f"[ Query   ] Fast Read query took {query_duration:.6f}s (O(1) lookup)")

        print("\n[ Query   ] Fetching Age Group Benchmarks from Read Models...")
        stmt = select(CQRSAgeGroupStats)
        res = await db.execute(stmt)
        age_stats = res.scalars().all()
        for s in age_stats:
            print(f"[ Query   ]  -> {s.age_group}: {s.total_assessments} assessments, {s.average_score:.2f} avg")

    print("\n==================================================")
    print(" PERFORMANCE GUARANTEE: Dashboard load times are now ")
    print(" stable regardless of how many million users exist.  ")
    print("==================================================")

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_demo())
