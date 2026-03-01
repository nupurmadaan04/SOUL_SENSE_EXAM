"""
CQRS Async Worker (#1124)
Consumes audit_trail events and updates read-optimized projections.
"""
import asyncio
import json
import logging
from datetime import datetime
from aiokafka import AIOKafkaConsumer
from ..services.db_router import PrimarySessionLocal
from ..services.kafka_producer import get_kafka_producer
from ..config import get_settings_instance
from .cqrs_service import CQRSService

logger = logging.getLogger(__name__)

async def run_cqrs_worker():
    """Consumes Kafka events to build pre-computed Read Models."""
    settings = get_settings_instance()
    producer = get_kafka_producer()
    bootstrap_servers = getattr(settings, 'kafka_bootstrap_servers', None)
    
    consumer = None
    if bootstrap_servers:
        try:
            consumer = AIOKafkaConsumer(
                "audit_trail",
                bootstrap_servers=bootstrap_servers,
                group_id="cqrs_analytics_workers",
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset="earliest"
            )
            await consumer.start()
            logger.info(f"CQRS Worker started on {bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to start CQRS Kafka consumer: {e}")
            consumer = None

    # Failover to local queue if Kafka is missing
    q = None
    if not consumer:
        logger.info("CQRS Worker falling back to local producer queue")
        q = producer.subscribe()

    while True:
        try:
            event_data = None
            if consumer:
                msg = await consumer.getone()
                event_data = msg.value
            elif q:
                event_data = await q.get()
            
            if not event_data:
                continue

            # Process the event to update read models
            # We filter for 'Score' entity as it's the primary driver of analytics
            entity = event_data.get('entity')
            event_type = event_data.get('type')
            
            if entity == 'Score':
                async with PrimarySessionLocal() as db:
                    await CQRSService.process_event(db, event_type, entity, event_data.get('payload', {}))
                    # logger.info(f"[CQRS] Updated projections for {entity} {event_type}")
            
            # Yield control to prevent CPU starvation during high-frequency events
            await asyncio.sleep(0)

        except asyncio.CancelledError:
            if consumer: await consumer.stop()
            if q: producer.unsubscribe(q)
            break
        except Exception as e:
            logger.error(f"Error in CQRS worker: {e}")
            await asyncio.sleep(2)

def start_cqrs_worker():
    """Starts the CQRS background worker."""
    loop = asyncio.get_event_loop()
    loop.create_task(run_cqrs_worker())
