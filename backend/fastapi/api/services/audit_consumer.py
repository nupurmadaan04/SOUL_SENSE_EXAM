import asyncio
import json
import logging
from datetime import datetime, UTC
from typing import Optional
from aiokafka import AIOKafkaConsumer
from ..models import AuditSnapshot
from ..services.db_router import PrimarySessionLocal
from ..services.kafka_producer import get_kafka_producer
from ..config import get_settings_instance
from sqlalchemy import insert, select, update

logger = logging.getLogger(__name__)

async def run_audit_consumer():
    """Background task to process audit events into Postgres snapshots (#1085)."""
    settings = get_settings_instance()
    producer = get_kafka_producer()
    bootstrap_servers = getattr(settings, 'kafka_bootstrap_servers', None)
    
    consumer: Optional[AIOKafkaConsumer] = None
    if bootstrap_servers:
        try:
            consumer = AIOKafkaConsumer(
                "audit_trail",
                bootstrap_servers=bootstrap_servers,
                group_id="audit_consumers",
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset="earliest"
            )
            await consumer.start()
            logger.info(f"Kafka Audit Consumer started on {bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}. Falling back to local queue.")
            consumer = None

    q: Optional[asyncio.Queue] = None
    if not consumer:
        q = producer.subscribe()

    while True:
        try:
            event_data = None
            if consumer:
                # Read from Kafka topic
                # Using wait_muted or similar? No, just iterate
                msg = await consumer.getone()
                event_data = msg.value
            elif q:
                # Fallback: Read from local producer queue
                event_data = await q.get()
            
            if not event_data:
                continue

            # Persist to audit_snapshot table (Compacted log)
            async with PrimarySessionLocal() as db:
                snapshot = AuditSnapshot(
                    event_type=event_data.get('type'),
                    entity=event_data.get('entity'),
                    entity_id=str(event_data.get('entity_id') or event_data.get('payload', {}).get('id', '')),
                    payload=event_data.get('payload'),
                    user_id=event_data.get('user_id'),
                    timestamp=datetime.now(UTC)
                )
                db.add(snapshot)
                await db.commit()
                # logger.debug(f"Audit event persisted: {event_data['entity']} {event_data['type']}")

        except asyncio.CancelledError:
            if consumer: await consumer.stop()
            if q: producer.unsubscribe(q) # Unsubscribe if local queue was used
            break
        except Exception as e:
            logger.error(f"Error in audit consumer: {e}")
            await asyncio.sleep(1)

def start_audit_loop():
    """Starts the background consumer loop."""
    loop = asyncio.get_event_loop()
    loop.create_task(run_audit_consumer())
