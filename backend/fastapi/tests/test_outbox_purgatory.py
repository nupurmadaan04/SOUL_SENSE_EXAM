import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from api.routers.tasks import retry_outbox_events
from api.services.outbox_relay_service import OutboxRelayService

@pytest.mark.asyncio
async def test_admin_retry_outbox_events_success():
    # Setup
    admin_user = MagicMock()
    admin_user.is_admin = True
    admin_user.username = "admin"
    
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    db.execute.return_value = mock_result
    
    # Execute
    response = await retry_outbox_events(current_user=admin_user, db=db)
    
    # Verify
    assert response["status"] == "success"
    assert response["recovered_count"] == 5
    db.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_admin_retry_outbox_events_unauthorized():
    # Setup
    normal_user = MagicMock()
    normal_user.is_admin = False
    
    db = AsyncMock()
    
    # Execute & Verify
    with pytest.raises(HTTPException) as exc:
        await retry_outbox_events(current_user=normal_user, db=db)
    
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_monitor_purgatory_volume_alert(caplog):
    # Setup
    async_session_factory = MagicMock()
    db = AsyncMock()
    async_session_factory.return_value.__aenter__.return_value = db
    
    # Simulate 12,000 events in purgatory
    mock_result = MagicMock()
    mock_result.scalar.return_value = 12000
    db.execute.return_value = mock_result
    
    # We need to mock asyncio.sleep to break the loop or just run one iteration
    with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
        try:
            await OutboxRelayService.monitor_purgatory_volume(async_session_factory)
        except asyncio.CancelledError:
            pass
            
    # Verify logging
    assert any("Outbox Purgatory Threshold Exceeded!" in record.message for record in caplog.records)
    assert any("12000" in record.message for record in caplog.records)
