"""
Non-Blocking gRPC NLP Integration Demo (#1126)
Demonstrates offloading sentiment analysis to an external microservice.
"""
import asyncio
import logging
import subprocess
import time
import sys
from sqlalchemy import select
from api.services.db_router import PrimarySessionLocal
from api.models import JournalEntry, User
from api.services.journal_service import JournalService
from fastapi import BackgroundTasks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nlp_demo")

async def run_demo():
    print("==================================================")
    print("      Non-Blocking gRPC NLP Integration Demo      ")
    print("==================================================")

    # 1. Start the NLP Mock Server in the background
    print("\n[ Server  ] Starting NLP Mock Microservice...")
    server_process = subprocess.Popen(
        [sys.executable, "nlp_server_mock.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2) # Wait for server to bind

    try:
        async with PrimarySessionLocal() as db:
            # 2. Setup: Ensure user exists
            user_stmt = select(User).limit(1)
            user = (await db.execute(user_stmt)).scalar_one_or_none()
            if not user:
                print("[ Error   ] No user found. Run standard setup first.")
                return

            service = JournalService(db)
            bg_tasks = BackgroundTasks()

            # Set encryption context for transparent model encryption/decryption
            from api.services.encryption_service import EncryptionService, current_dek
            dek = await EncryptionService.get_or_create_user_dek(user.id, db)
            current_dek.set(dek)

            # 3. Simulate high-traffic journal creation (Blazingly Fast)
            print("\n[ FastAPI ] Creating journal entry (Simulating POST /api/v1/journals)...")
            start_time = time.time()
            
            # This call returns 202-like immediately after saving to DB
            entry = await service.create_entry(
                current_user=user,
                content="I am having a truly magnificent and happy day! Success is everywhere.",
                background_tasks=bg_tasks
            )
            
            end_time = time.time()
            print(f"[ FastAPI ] Entry {entry.id} created in {end_time - start_time:.4f}s")
            print(f"[ Status  ] HTTP 202 ACCEPTED. Current Sentiment Score in DB: {entry.sentiment_score}")

            # 4. Process Background Tasks (normally handled by FastAPI engine)
            print("\n[ Worker  ] Executing Background Tasks (gRPC call to NLP service)...")
            for task in bg_tasks.tasks:
                await task.func(*task.args, **task.kwargs)

            # 5. Verify Async Update
            print("\n[ Database] Verifying sentiment score update...")
            # We need a new session or refresh to see changes committed by the background task
            async with PrimarySessionLocal() as db2:
                stmt = select(JournalEntry).filter(JournalEntry.id == entry.id)
                res = await db2.execute(stmt)
                updated_entry = res.scalar_one_or_none()
                
                print(f"[ Database] Final Sentiment Score: {updated_entry.sentiment_score}")
                print(f"[ Database] Emotional Patterns: {updated_entry.emotional_patterns}")
                
            print("\n[ Success ] Outcome: API responded instantly. NLP heavy lifting done via gRPC.")

    except Exception as e:
        print(f"[ Fatal   ] Demo failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[ Server  ] Shutting down NLP Mock Microservice...")
        server_process.terminate()

    print("==================================================")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_demo())
