"""Outbox stuck-message auto-remediator

Finds OutboxEvent rows that appear stuck and nudges them back into the relay window
by setting `next_retry_at` to now and adding a short diagnostic entry to `error_message`.

This tool is safe to run repeatedly and intended for cron/alert-driven remediation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
UTC = timezone.utc
import logging
from typing import List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL
from backend.fastapi.api.models.__init__ import OutboxEvent, Base

logger = logging.getLogger(__name__)


def remediate_stuck_events(session, *, older_than_minutes: int = 30, limit: int = 200) -> List[int]:
    """Remediate outbox events that look stuck.

    Criteria (heuristic):
      - status == 'pending' AND (
          next_retry_at is NULL and created_at <= now - older_than_minutes
          OR next_retry_at > now + older_than_minutes
        )

    Action:
      - set next_retry_at = now
      - append a remediation note to error_message

    Returns list of remediated event ids.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=older_than_minutes)

    # Build query to find stuck events
    stmt = select(OutboxEvent).where(
        OutboxEvent.status == 'pending'
    ).limit(limit)

    rows = session.execute(stmt).scalars().all()
    remediated = []

    for ev in rows:
        try:
            # Normalize timezone-awareness for comparisons: treat naive datetimes as UTC
            created_at = ev.created_at
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            next_retry_at = ev.next_retry_at
            if next_retry_at and next_retry_at.tzinfo is None:
                next_retry_at = next_retry_at.replace(tzinfo=UTC)
            is_stuck = False
            if next_retry_at is None and created_at and created_at <= cutoff:
                is_stuck = True
            elif next_retry_at and next_retry_at > now + timedelta(minutes=older_than_minutes):
                is_stuck = True

            if is_stuck:
                note = f"[remediated_at={now.isoformat()}] nudged next_retry_at to now; was={ev.next_retry_at}"
                if ev.error_message:
                    ev.error_message = note + " | " + (ev.error_message or "")
                else:
                    ev.error_message = note
                ev.next_retry_at = now
                session.add(ev)
                remediated.append(ev.id)
                logger.info(f"Remediated outbox event id={ev.id}")
        except Exception as e:
            logger.exception(f"Failed to remediate event {ev.id}: {e}")

    if remediated:
        session.commit()

    return remediated


def main():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    # Ensure tables exist in lightweight deployments
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    with Session() as session:
        remediated = remediate_stuck_events(session)
        if remediated:
            print(f"Remediated {len(remediated)} outbox events: {remediated}")
        else:
            print("No stuck outbox events found.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
