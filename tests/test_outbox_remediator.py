import os
import sys
from datetime import datetime, timedelta, timezone

# Python 3.10 compatibility
UTC = timezone.utc

sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from backend.fastapi.api.models.__init__ import Base, OutboxEvent
from scripts.outbox_remediator import remediate_stuck_events


def setup_inmemory_db():
    engine = create_engine("sqlite:///:memory:")
    # Create only the OutboxEvent table to avoid creating unrelated indexes
    OutboxEvent.__table__.create(bind=engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    return Session()


def test_remediate_old_pending_event():
    session = setup_inmemory_db()
    now = datetime.now(UTC)
    old = now - timedelta(hours=2)

    ev = OutboxEvent(topic="search_indexing", payload={"x": 1}, created_at=old, status="pending", retry_count=0)
    session.add(ev)
    session.commit()

    remediated = remediate_stuck_events(session, older_than_minutes=30)
    assert ev.id in remediated


def test_no_remediate_recent_event():
    session = setup_inmemory_db()
    now = datetime.now(UTC)
    recent = now - timedelta(minutes=5)

    ev = OutboxEvent(topic="search_indexing", payload={"x": 2}, created_at=recent, status="pending", retry_count=0)
    session.add(ev)
    session.commit()

    remediated = remediate_stuck_events(session, older_than_minutes=30)
    assert ev.id not in remediated
