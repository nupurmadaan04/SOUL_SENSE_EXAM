import json
import asyncio
import logging
from typing import Optional
from aiokafka import AIOKafkaProducer
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self):
        self.settings = get_settings_instance()
        self.producer: Optional[AIOKafkaProducer] = None
        self.live_events = asyncio.Queue() # For SSE streaming
        self.loop = asyncio.get_event_loop()

    async def start(self):
        # We try to connect to Kafka if KAFKA_BOOTSTRAP_SERVERS is provided
        bootstrap_servers = getattr(self.settings, 'kafka_bootstrap_servers', None)
        if bootstrap_servers:
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await self.producer.start()
                logger.info(f"Kafka producer started on {bootstrap_servers}")
            except Exception as e:
                logger.error(f"Failed to start Kafka producer: {e}. Falling back to local events.")
                self.producer = None
        else:
             logger.info("Kafka not configured. Using local event queue for audit trail.")

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    def queue_event(self, event_data: dict):
        """Called by SQLAlchemy listeners. Non-blocking."""
        asyncio.create_task(self.send_event(event_data))

    async def send_event(self, event_data: dict):
        # 1. Put into live stream for SSE
        await self.live_events.put(event_data)
        
        # 2. Push to Kafka if available
        if self.producer:
            try:
                from .circuit_breaker import CircuitBreaker
                cb = CircuitBreaker("kafka_producer", failure_threshold=3, recovery_timeout=60)
                await cb.call(self.producer.send_and_wait, "audit_trail", event_data)
            except Exception as e:
                logger.error(f"Kafka circuit breaker blocked/caught failure: {e}")

_producer_instance: Optional[KafkaProducerService] = None

def get_kafka_producer() -> KafkaProducerService:
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaProducerService()
    return _producer_instance
