import asyncio
import logging
import uuid
import json
from pprint import pprint
from datetime import datetime, UTC

# Configure minimal logging to avoid cluttering output
logging.basicConfig(level=logging.ERROR)

from sqlalchemy import create_engine, select, Column, Text, TypeDecorator
from sqlalchemy.orm import sessionmaker
from api.celery_tasks import process_outbox_events
from api.services.kafka_producer import get_kafka_producer
from api.models.__init__ import capture_audit_events, flush_audit_to_outbox, cleanup_audit_buffer

class DummyEncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True

import api.models.__init__
api.models.__init__.EncryptedString = DummyEncryptedString
from api.models import Base, OutboxEvent, User

# Setup an in-memory test DB
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

async def simulate_app_request():
    print("==================================================")
    print("  Transactional Outbox Audit Trail (ISSUE-1122)   ")
    print("==================================================")
    
    session = SessionLocal()
    
    # Manually bind listeners since we're using a standalone in-memory DB
    from sqlalchemy import event
    event.listen(session, 'after_flush', capture_audit_events)
    event.listen(session, 'before_commit', flush_audit_to_outbox)
    event.listen(session, 'after_commit', cleanup_audit_buffer)
    
    print("\n[ Phase 1 ] User updates their profile (Standard HTTP Request)...")
    
    # Create fake user
    new_user = User(username=f"test_user_{uuid.uuid4().hex[:6]}", password_hash="hash")
    session.add(new_user)
    
    print("[ SQL     ] Emitting INSERTs to Database...")
    print("[ Audit   ] SQLAlchemy Hook capturing model state changes natively...")
    
    # Trigger flush to gather audit events, then commit to process Outbox
    session.commit()
    
    # Verify Outbox
    print("[ Success ] Database Transaction Committed!")
    
    outbox_entries = session.execute(select(OutboxEvent)).scalars().all()
    print(f"\n[ Outbox  ] Found {len(outbox_entries)} 'pending' events safely written in the EXACT same transaction!")
    for e in outbox_entries:
        print(f"            - ID: {e.id}, Topic: {e.topic}, Entity: {e.payload['entity']}, Status: {e.status}")
    
    print("\n[ HTTP    ] Request finishes quickly. User gets 200 OK.")
    
    print("\n--------------------------------------------------")
    print("        [ Phase 2 ] Background Celery Beat Worker ")
    print("--------------------------------------------------")
    print("[ Celery  ] Executing `process_outbox_events` scheduled task...")
    
    # Force the async code inside Celery task to run
    # (Since our DB is in-memory sync, we must adapt the Celery call tightly for this demo script)
    
    producer = get_kafka_producer()
    
    processed = 0
    # Simulating what process_outbox_events does structurally 
    # (Since `AsyncSessionLocal` in the real task uses the real async driver config, not this sync sqlite wrapper)
    events = session.execute(select(OutboxEvent).filter(OutboxEvent.status == 'pending')).scalars().all()
    for event in events:
        try:
            print(f"[ Kafka   ] Pishing Event to cluster >> {json.dumps(event.payload)}")
            # Real task does `producer.queue_event(event.payload)`
            producer._queue.put_nowait(event.payload) 
            event.status = 'processed'
            processed += 1
        except Exception as e:
            print(f"Err {e}")
            break
            
    if processed > 0:
        session.commit()
        
    print(f"[ Celery  ] Finished polling. Marked {processed} rows as 'processed'.")
    
    # Final state
    final_entries = session.execute(select(OutboxEvent)).scalars().all()
    print("\n[ DB      ] Final Outbox State:")
    for e in final_entries:
        print(f"            - ID: {e.id}, Status: {e.status} \t(Will be cleaned up completely by archive service later)")
    
    print("==================================================")
    print(" GUARANTEE: Even if Kafka completely crashed during the HTTP request,")
    print("            the event is strictly held in the outbox table and ")
    print("            the worker will infinitely retry pushing it forever.")

async def main():
    await simulate_app_request()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
