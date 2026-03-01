import asyncio
import httpx
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn
import threading
import time
import sys

# Mock imports
class MockAsyncSession:
    async def execute(self, *args, **kwargs):
        pass
    async def close(self):
        print("MockAsyncSession.close() called")

class SyncTracker:
    closed_count = 0

async def mock_get_db():
    db = MockAsyncSession()
    try:
        yield db
    finally:
        SyncTracker.closed_count += 1
        await db.close()

app = FastAPI()

@app.middleware("http")
async def crash_middleware(request: Request, call_next):
    if request.url.path == "/test":
        # Simulate a 401 throw before route finishes
        return JSONResponse(status_code=401, content={"detail": "Unauthorized throw from middleware"})
    response = await call_next(request)
    return response

@app.get("/test")
async def test_endpoint(db: AsyncSession = Depends(mock_get_db)):
    return {"message": "success"}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8099, log_level="critical")

async def test_requests():
    # Warmup / wait for server
    await asyncio.sleep(1)
    
    print("Sending request to /test that should hit middleware 401")
    async with httpx.AsyncClient() as client:
        res = await client.get("http://127.0.0.1:8099/test")
        print(f"Response: {res.status_code} {res.json()}")
    
    print(f"Total sessions closed: {SyncTracker.closed_count}")

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    asyncio.run(test_requests())
    sys.exit(0)
