import logging
import asyncio
import json
from datetime import datetime, UTC
from typing import Any
from sqlalchemy import event, inspect
from .kafka_producer import get_kafka_producer

logger = logging.getLogger(__name__)

def get_entity_data(target: Any) -> dict:
    """Extract serializable data from a SQLAlchemy model instance."""
    insp = inspect(target)
    data = {}
    for col in insp.mapper.column_attrs:
        val = getattr(target, col.key)
        if isinstance(val, (datetime,)):
            val = val.isoformat()
        elif hasattr(val, 'hex'): # UUID
            val = val.hex
        data[col.key] = val
    return data

def audit_listener(mapper, connection, target):
    """Generic SQLAlchemy listener to push audit events to Kafka ($1085)."""
    try:
        insp = inspect(target)
        entity_name = target.__class__.__name__
        doc_id = getattr(target, 'id', 'unknown')
        
        if insp.deleted:
            event_type = "DELETED"
            payload = {"id": doc_id} # Minimal payload for delete
        elif insp.persistent:
            event_type = "UPDATED"
            # In a production app, we might want to only send the diff
            payload = get_entity_data(target)
        else:
            event_type = "CREATED"
            payload = get_entity_data(target)

        # Attempt to find user_id on the object
        user_id = getattr(target, 'user_id', None)
        if not user_id and entity_name == 'User':
            user_id = target.id

        event_data = {
            "type": event_type,
            "entity": entity_name,
            "entity_id": str(doc_id),
            "payload": payload,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat()
        }

        # Push to Kafka via Producer (non-blocking)
        producer = get_kafka_producer()
        producer.queue_event(event_data)

    except Exception as e:
        logger.error(f"Audit listener failed for {target}: {e}")

def register_audit_listeners():
    """Attach audit logic to all security-critical models."""
    from ..models import (
        User, JournalEntry, Assessment, Score, 
        UserAchievement, MedicalProfile, PersonalProfile
    )
    
    models_to_audit = [
        User, JournalEntry, Assessment, Score, 
        UserAchievement, MedicalProfile, PersonalProfile
    ]
    
    for model in models_to_audit:
        event.listen(model, 'after_insert', audit_listener)
        event.listen(model, 'after_update', audit_listener)
        event.listen(model, 'after_delete', audit_listener)
    
    logger.info(f"Event-Sourced Audit listeners registered for {len(models_to_audit)} models.")
