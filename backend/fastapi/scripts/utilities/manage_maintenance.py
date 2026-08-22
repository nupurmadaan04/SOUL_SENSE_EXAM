
import asyncio
import os
import sys
import json
import argparse

# Set PYTHONPATH to root and backend/fastapi
project_root = os.getcwd()
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "backend", "fastapi"))

from api.services.cache_service import cache_service

MAINTENANCE_KEY = "soulsense:maintenance_state"

async def manage_maintenance():
    parser = argparse.ArgumentParser(description="Manage SoulSense Maintenance Mode (#1112)")
    parser.add_argument("action", choices=["on", "off", "status"], help="Action to perform")
    parser.add_argument("--mode", choices=["NORMAL", "READ_ONLY", "MAINTENANCE"], default="MAINTENANCE", help="Target mode")
    parser.add_argument("--retry", type=int, default=60, help="Retry-After value in seconds")
    parser.add_argument("--reason", type=str, default="System is down for scheduled maintenance.", help="Reason for maintenance")

    args = parser.parse_args()

    if args.action == "status":
        state = await cache_service.get(MAINTENANCE_KEY)
        if not state:
            print("Maintenance Mode: OFF (NORMAL)")
        else:
            print(f"Maintenance Mode: ON")
            print(json.dumps(state, indent=2))
        return

    if args.action == "off":
        await cache_service.delete(MAINTENANCE_KEY)
        print("Maintenance Mode: OFF (NORMAL). System is now fully functional.")
        return

    if args.action == "on":
        state = {
            "mode": args.mode,
            "retry_after": args.retry,
            "reason": args.reason
        }
        # TTL should be long so it doesn't expire prematurely, or indefinite
        # For our set method, default is 3600. Let's make it 24h by default if 'on'
        await cache_service.set(MAINTENANCE_KEY, state, ttl_seconds=86400)
        print(f"Maintenance Mode: ON (Mode: {args.mode})")
        print(f"Reason: {args.reason}")
        print(f"Retry-After: {args.retry}s")

if __name__ == "__main__":
    asyncio.run(manage_maintenance())
