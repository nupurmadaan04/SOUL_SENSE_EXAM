
import asyncio
import os
import sys
import datetime
from pathlib import Path

# Add the project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from backend.fastapi.app.services.github_service import github_service

async def debug_activity():
    activity = await github_service.get_activity()
    if not activity:
        print("Activity is still empty.")
        return

    print(f"Total weeks: {len(activity)}")
    first = activity[0]
    last = activity[-1]
    
    first_date = datetime.datetime.fromtimestamp(first['week'])
    last_date = datetime.datetime.fromtimestamp(last['week'])
    
    print(f"First week: {first['week']} ({first_date})")
    print(f"Last week: {last['week']} ({last_date})")
    
    active_weeks = [w for w in activity if w['total'] > 0]
    print(f"Active weeks: {len(active_weeks)}")
    if active_weeks:
        last_active = active_weeks[-1]
        last_active_date = datetime.datetime.fromtimestamp(last_active['week'])
        print(f"Last active week: {last_active['week']} ({last_active_date}), total commits: {last_active['total']}")

if __name__ == "__main__":
    asyncio.run(debug_activity())
