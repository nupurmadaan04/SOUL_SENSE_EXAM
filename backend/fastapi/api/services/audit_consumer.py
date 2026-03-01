import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer
from ..models import AuditSnapshot
from ..services.db_router import PrimarySessionLocal
from ..services.kafka_producer import get_kafka_producer
from sqlalchemy import insert, select, update

logger = logging.getLogger(__name__)

async def run_audit_consumer():
    """Background task to process audit events into Postgres snapshots."""
    producer = get_kafka_producer()
    logger.info("Audit consumer started.")
    
    # We use the producer's local Queue as the immediate source for snapshots & SSE
    # In a real distributed system, we would use a separate Kafka Consumer (aiokafka.AIOKafkaConsumer)
    while True:
        try:
            event_data = await producer.live_events.get()
            
            # Persist to audit_snapshot table (Compacted log)
            async with PrimarySessionLocal() as db:
                snapshot = AuditSnapshot(
                    event_type=event_data.get('type'),
                    entity=event_data.get('entity'),
                    entity_id=str(event_data.get('entity_id') or event_data.get('payload', {}).get('id', '')),
                    payload=event_data.get('payload'),
                    user_id=event_data.get('user_id'),
                    timestamp=None # Default uses datetime.utcnow()
                )
                db.add(snapshot)
                await db.commit()
                # logger.debug(f"Audit event persisted: {event_data['entity']} {event_data['type']}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in audit consumer: {e}")
            await asyncio.sleep(1)

def start_audit_loop():
    """Starts the producer and the background consumer loop."""
    loop = asyncio.get_event_loop()
    loop.create_task(run_audit_consumer())
