import asyncio
import sys
import os
from pathlib import Path

# Fix sys.path to point to the root of the project
current_path = Path(__file__).resolve().parent
project_root = current_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

async def run_debug():
    print("🚀 Starting GitHub Service Debug...")
    from backend.fastapi.app.services.github_service import github_service
    
    print(f"📡 Targeting: {github_service.owner}/{github_service.repo}")
    
    # 1. Simple Stats
    print("\n[1] Fetching Stats...")
    stats = await github_service.get_repo_stats()
    print(f"✅ Stats: {stats}")
    
    # 2. Graph Data
    print("\n[2] Fetching Graph...")
    graph = await github_service.get_community_graph()
    print(f"✅ Graph Nodes: {len(graph['nodes'])}")
    print(f"✅ Graph Links: {len(graph['links'])}")

if __name__ == "__main__":
    asyncio.run(run_debug())
