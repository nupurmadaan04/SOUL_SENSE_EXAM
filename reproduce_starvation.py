
import asyncio
import time
import threading
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from contextlib import contextmanager

# Mocking the current situation
app = FastAPI()

def get_db_sync():
    # Simulate a DB session
    print(f"[{threading.current_thread().name}] Opening DB session")
    try:
        yield "session"
    finally:
        print(f"[{threading.current_thread().name}] Closing DB session")

@app.get("/sync-blocking")
async def sync_blocking(db: str = Depends(get_db_sync)):
    # This is an async route that does a blocking operation
    print(f"[{threading.current_thread().name}] Starting blocking DB call")
    time.sleep(1) # Simulate slow DB query
    print(f"[{threading.current_thread().name}] Finished blocking DB call")
    return {"message": "done"}

@app.get("/heartbeat")
async def heartbeat():
    # This should be fast, but will be blocked if the event loop is starved
    return {"status": "ok"}

async def run_reproduction():
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as ac:
        print("Starting concurrent requests to /sync-blocking...")
        # Start several blocking requests
        tasks = [ac.get("/sync-blocking") for _ in range(5)]
        
        # Start a heartbeat request slightly later
        await asyncio.sleep(0.1)
        hb_start = time.time()
        hb_task = asyncio.create_task(ac.get("/heartbeat"))
        
        responses = await asyncio.gather(*tasks, hb_task)
        hb_duration = time.time() - hb_start
        
        print(f"Heartbeat took {hb_duration:.2f} seconds")
        if hb_duration > 0.5:
            print("FAILURE: Event loop was STARVED!")
        else:
            print("SUCCESS: Event loop stayed responsive (unlikely with current code)")

if __name__ == "__main__":
    asyncio.run(run_reproduction())
