
import asyncio
import os
import sys
import time
from pathlib import Path

# Add the project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from backend.fastapi.app.services.github_service import github_service

async def debug_activity():
    print(f"Targeting: {github_service.owner}/{github_service.repo}")
    
    for i in range(5):
        print(f"Attempt {i+1} Calling get_activity...")
        activity = await github_service.get_activity()
        if activity and len(activity) > 0:
            print(f"Success! Result length: {len(activity)}")
            print("Sample activity:", activity[-2:]) # Latest weeks
            break
        else:
            print("Activity is still empty (likely 202). Waiting 3 seconds...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(debug_activity())
