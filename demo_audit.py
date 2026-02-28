import asyncio
import os
import sys
import json
from datetime import datetime, UTC

# Set PYTHONPATH
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(test_dir, "backend", "fastapi")
sys.path.insert(0, project_root)

async def demo_audit_kafka():
    from api.services.kafka_producer import get_kafka_producer
    from api.services.audit_consumer import run_audit_consumer
    
    producer = get_kafka_producer()
    # We won't start the real Kafka for this demo, it will fallback to local queue.
    
    print(f"\n{'='*70}")
    print(f"EVENT-SOURCED AUDIT TRAIL DEMO: KAFKA & SSE (#1085)")
    print(f"{'='*70}")

    # 1. Start a mock SSE listener
    sse_q = producer.subscribe()
    print("[SSE] Admin subscribed to live audit stream.")

    # 2. Simulate a SQLAlchemy event (e.g. User Created)
    event_data = {
        "type": "CREATED",
        "entity": "User",
        "entity_id": "123",
        "payload": {"username": "new_user_99", "email": "new@example.com"},
        "user_id": 1,
        "timestamp": datetime.now(UTC).isoformat()
    }
    
    print(f"\n[DB] Model change detected (User #123 CREATED).")
    producer.queue_event(event_data)
    
    # 3. Check if SSE listener receives it
    try:
        received_sse = await asyncio.wait_for(sse_q.get(), timeout=2.0)
        print(f"[SSE] Received Live Event: {received_sse['entity']} {received_sse['type']}")
    except asyncio.TimeoutError:
        print("[FAIL] SSE listener timed out.")

    print("\n[Audit Trail] System ready for compliance playback.")
    
    producer.unsubscribe(sse_q)
    print("\nDemo finished.")

if __name__ == "__main__":
    asyncio.run(demo_audit_kafka())
