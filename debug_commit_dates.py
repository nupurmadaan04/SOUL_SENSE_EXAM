
import asyncio
import os
import sys
import datetime
from pathlib import Path

# Add the project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from backend.fastapi.app.services.github_service import github_service

async def debug_commits():
    endpoint = f"/repos/{github_service.owner}/{github_service.repo}/commits"
    print(f"Fetching latest commits from {endpoint}...")
    commits = await github_service._get(endpoint, params={"per_page": 5})
    
    if commits:
        for c in commits:
            date_str = c['commit']['author']['date']
            print(f"SHA: {c['sha'][:7]}, Date: {date_str}, Author: {c['commit']['author']['name']}")
    else:
        print("No commits found.")

if __name__ == "__main__":
    asyncio.run(debug_commits())
