"""
Tests for Transactional Outbox Purgatory Risk Mitigation.

Validates:
1. Exponential backoff retry logic
2. Dead-letter transition after 3 failures
3. Purgatory monitor alerting
4. Admin recovery API functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select, func

from backend.fastapi.api.models import OutboxEvent, User
from backend.fastapi.api.services.outbox_relay_service import OutboxRelayService


@pytest.mark.asyncio
async def test_exponential_backoff_schedule(async_db):
    """Test that retry delays follow exponential backoff: 30s, 60s, 120s."""
    # Create a pending event
    event = OutboxEvent(
        topic="search_indexing",
        payload={"journal_id": 1, "action": "upsert", "event_id": "test-123"},
        status="pending",
        retry_count=0
    )
    async_db.add(event)
    await async_db.commit()
    await async_db.refresh(event)

    # Mock ES service to always fail
    with patch('backend.fastapi.api.services.outbox_relay_service.get_es_service') as mock_es:
        mock_es_instance = AsyncMock()
        mock_es_instance.index_document.side_effect = Exception("ES connection failed")
        mock_es.return_value = mock_es_instance

        # Mock journal lookup to return a valid journal
        with patch.object(async_db, 'execute') as mock_execute:
            # First call: fetch events
            # Second call: fetch journal
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [event]
            mock_result.scalar_one_or_none.return_value = MagicMock(
                id=1, user_id=1, tenant_id=None, content="test", timestamp="2024-01-01", is_deleted=False
            )
            mock_execute.return_value = mock_result

            # Process event - should fail and schedule retry
            await OutboxRelayService.process_pending_indexing_events(async_db)

    # Refresh event from DB
    await async_db.refresh(event)

    # Verify first retry scheduled for 30 seconds
    assert event.retry_count == 1
    assert event.status == "pending"
    assert event.last_error == "ES connection failed"
    assert event.next_retry_at is not None
    
    # Check delay is approximately 30 seconds
    delay = (event.next_retry_at - event.created_at).total_seconds()
    assert 28 <= delay <= 32, f"Expected ~30s delay, got {delay}s"


@pytest.mark.asyncio
async def test_dead_letter_after_three_retries(async_db):
    """Test that events move to dead_letter status after 3 failed attempts."""
    # Create event that has already failed twice
    event = OutboxEvent(
        topic="search_indexing",
        payload={"journal_id": 1, "action": "upsert", "event_id": "test-456"},
        status="pending",
        retry_count=2,
        next_retry_at=datetime.now(UTC) - timedelta(seconds=1)  # Past retry time
    )
    async_db.add(event)
    await async_db.commit()
    await async_db.refresh(event)

    # Mock ES service to fail
    with patch('backend.fastapi.api.services.outbox_relay_service.get_es_service') as mock_es:
        mock_es_instance = AsyncMock()
        mock_es_instance.index_document.side_effect = Exception("Persistent failure")
        mock_es.return_value = mock_es_instance

        # Mock journal lookup
        with patch.object(async_db, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [event]
            mock_result.scalar_one_or_none.return_value = MagicMock(
                id=1, user_id=1, tenant_id=None, content="test", timestamp="2024-01-01", is_deleted=False
            )
            mock_execute.return_value = mock_result

            # Process event - should move to dead_letter
            await OutboxRelayService.process_pending_indexing_events(async_db)

    # Refresh and verify dead_letter status
    await async_db.refresh(event)
    
    assert event.retry_count == 3
    assert event.status == "dead_letter"
    assert event.last_error == "Persistent failure"
    assert event.next_retry_at is None  # No more retries scheduled


@pytest.mark.asyncio
async def test_purgatory_monitor_critical_alert(async_db, caplog):
    """Test that purgatory monitor logs critical alert when threshold exceeded."""
    import logging
    caplog.set_level(logging.CRITICAL)

    # Create 10,001 pending events to exceed threshold
    events = [
        OutboxEvent(
            topic="search_indexing",
            payload={"journal_id": i, "action": "upsert"},
            status="pending" if i % 2 == 0 else "dead_letter"
        )
        for i in range(10001)
    ]
    async_db.add_all(events)
    await async_db.commit()

    # Mock the session factory
    async def mock_session_factory():
        yield async_db

    # Run monitor once
    with patch('asyncio.sleep', side_effect=asyncio.CancelledError):
        try:
            await OutboxRelayService.monitor_purgatory_volume(mock_session_factory)
        except asyncio.CancelledError:
            pass

    # Verify critical alert was logged
    assert any(
        "CRITICAL ALERT" in record.message and "Purgatory Threshold Exceeded" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_purgatory_monitor_warning_level(async_db, caplog):
    """Test that purgatory monitor logs warning at 5,000 events."""
    import logging
    caplog.set_level(logging.WARNING)

    # Create 5,500 events (warning level)
    events = [
        OutboxEvent(
            topic="search_indexing",
            payload={"journal_id": i, "action": "upsert"},
            status="pending"
        )
        for i in range(5500)
    ]
    async_db.add_all(events)
    await async_db.commit()

    # Mock the session factory
    async def mock_session_factory():
        yield async_db

    # Run monitor once
    with patch('asyncio.sleep', side_effect=asyncio.CancelledError):
        try:
            await OutboxRelayService.monitor_purgatory_volume(mock_session_factory)
        except asyncio.CancelledError:
            pass

    # Verify warning was logged
    assert any(
        "Volume warning" in record.message and "5500 events in purgatory" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_admin_recovery_api_resets_failed_events(async_db, admin_user):
    """Test that admin recovery API resets failed and dead_letter events to pending."""
    from backend.fastapi.api.routers.tasks import retry_outbox_events
    from sqlalchemy import update

    # Create mix of events in different states
    events = [
        OutboxEvent(topic="search_indexing", payload={"id": 1}, status="pending", retry_count=0),
        OutboxEvent(topic="search_indexing", payload={"id": 2}, status="failed", retry_count=2),
        OutboxEvent(topic="search_indexing", payload={"id": 3}, status="dead_letter", retry_count=3),
        OutboxEvent(topic="search_indexing", payload={"id": 4}, status="processed", retry_count=0),
    ]
    async_db.add_all(events)
    await async_db.commit()

    # Call recovery API
    result = await retry_outbox_events(current_user=admin_user, db=async_db)

    # Verify response
    assert result["status"] == "success"
    assert result["recovered_count"] == 2  # Only failed and dead_letter

    # Verify events were reset
    stmt = select(OutboxEvent).where(OutboxEvent.payload["id"].astext.in_(["2", "3"]))
    recovered_events = (await async_db.execute(stmt)).scalars().all()

    for event in recovered_events:
        assert event.status == "pending"
        assert event.retry_count == 0
        assert event.next_retry_at is None
        assert event.processed_at is None


@pytest.mark.asyncio
async def test_admin_recovery_api_requires_admin(async_db, regular_user):
    """Test that non-admin users cannot access recovery API."""
    from backend.fastapi.api.routers.tasks import retry_outbox_events
    from fastapi import HTTPException

    # Attempt to call recovery API as regular user
    with pytest.raises(HTTPException) as exc_info:
        await retry_outbox_events(current_user=regular_user, db=async_db)

    assert exc_info.value.status_code == 403
    assert "Admin credentials required" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_admin_stats_endpoint(async_db, admin_user):
    """Test that admin stats endpoint returns accurate queue health metrics."""
    from backend.fastapi.api.routers.tasks import get_outbox_stats

    # Create events in various states
    events = [
        OutboxEvent(topic="search_indexing", payload={"id": i}, status="pending")
        for i in range(100)
    ] + [
        OutboxEvent(topic="search_indexing", payload={"id": i}, status="failed")
        for i in range(200, 250)
    ] + [
        OutboxEvent(topic="search_indexing", payload={"id": i}, status="dead_letter")
        for i in range(300, 320)
    ] + [
        OutboxEvent(topic="search_indexing", payload={"id": i}, status="processed")
        for i in range(400, 600)
    ]
    async_db.add_all(events)
    await async_db.commit()

    # Call stats endpoint
    result = await get_outbox_stats(current_user=admin_user, db=async_db)

    # Verify counts
    assert result["status_counts"]["pending"] == 100
    assert result["status_counts"]["failed"] == 50
    assert result["status_counts"]["dead_letter"] == 20
    assert result["status_counts"]["processed"] == 200
    assert result["total_unresolved"] == 170  # pending + failed + dead_letter
    assert result["purgatory_risk"] == "NORMAL"  # < 1000


@pytest.mark.asyncio
async def test_admin_dead_letters_endpoint(async_db, admin_user):
    """Test that admin can list dead-letter events for investigation."""
    from backend.fastapi.api.routers.tasks import list_dead_letter_events

    # Create dead-letter events with errors
    events = [
        OutboxEvent(
            topic="search_indexing",
            payload={"journal_id": i, "action": "upsert"},
            status="dead_letter",
            retry_count=3,
            last_error=f"Error {i}: Connection timeout"
        )
        for i in range(10)
    ]
    async_db.add_all(events)
    await async_db.commit()

    # Call dead-letters endpoint
    result = await list_dead_letter_events(limit=5, current_user=admin_user, db=async_db)

    # Verify response
    assert result["total"] == 5  # Limited to 5
    assert len(result["events"]) == 5
    
    for event_data in result["events"]:
        assert event_data["topic"] == "search_indexing"
        assert event_data["retry_count"] == 3
        assert "Connection timeout" in event_data["last_error"]


@pytest.mark.asyncio
async def test_successful_relay_marks_processed(async_db):
    """Test that successfully relayed events are marked as processed."""
    # Create pending event
    event = OutboxEvent(
        topic="search_indexing",
        payload={"journal_id": 1, "action": "upsert", "event_id": "test-789"},
        status="pending",
        retry_count=0
    )
    async_db.add(event)
    await async_db.commit()
    await async_db.refresh(event)

    # Mock ES service to succeed
    with patch('backend.fastapi.api.services.outbox_relay_service.get_es_service') as mock_es:
        mock_es_instance = AsyncMock()
        mock_es_instance.index_document.return_value = None  # Success
        mock_es.return_value = mock_es_instance

        # Mock journal lookup
        with patch.object(async_db, 'execute') as mock_execute:
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [event]
            mock_result.scalar_one_or_none.return_value = MagicMock(
                id=1, user_id=1, tenant_id=None, content="test", timestamp="2024-01-01", is_deleted=False
            )
            mock_execute.return_value = mock_result

            # Process event
            count = await OutboxRelayService.process_pending_indexing_events(async_db)

    # Verify event marked as processed
    await async_db.refresh(event)
    assert event.status == "processed"
    assert event.processed_at is not None
    assert count == 1


# Fixtures

@pytest.fixture
async def admin_user(async_db):
    """Create an admin user for testing."""
    user = User(
        username="admin_test",
        password_hash="hashed_password",
        is_admin=True,
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest.fixture
async def regular_user(async_db):
    """Create a regular (non-admin) user for testing."""
    user = User(
        username="regular_test",
        password_hash="hashed_password",
        is_admin=False,
        is_active=True
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user
