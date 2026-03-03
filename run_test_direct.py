import sys
import os
import asyncio

# Setup paths
root = os.path.abspath(os.getcwd())
fastapi_root = os.path.join(root, "backend", "fastapi")
sys.path.insert(0, fastapi_root)

print(f"PYTHONPATH: {sys.path[:3]}")

try:
    from api.routers.tasks import retry_outbox_events
    from api.services.outbox_relay_service import OutboxRelayService
    print("Imports OK")
except Exception as e:
    print(f"Imports FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

async def run_one():
    print("Testing retry_outbox_events success...")
    from unittest.mock import MagicMock, AsyncMock
    admin_user = MagicMock()
    admin_user.is_admin = True
    admin_user.username = "admin"
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    db.execute.return_value = mock_result
    
    response = await retry_outbox_events(current_user=admin_user, db=db)
    print(f"Response: {response}")
    assert response["status"] == "success"

if __name__ == "__main__":
    asyncio.run(run_one())
