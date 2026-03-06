import numpy as np
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from ..models import JournalEntry, User
from ..services.kafka_producer import get_kafka_producer
from ..services.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

class BurnoutDetectionService:
    """
    ML Analytics Service for Emotional Burnout Prediction.
    Analyzes Z-Scores across sentiment and stress baseline.
    """
    def __init__(self, db):
        self.db = db

    async def run_anomaly_detection(self, user_id: int) -> Dict[str, Any]:
        """
        Analyzes a sliding 30-day window of sentiment_score and stress_level.
        Implements Z-Score based trend analysis via a dedicated Inference Proxy.
        """
        from .inference_server import inference_proxy

        # 1. Fetch historical data (Personal Baseline)
        thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Get last 30 entries for this user
        stmt = select(JournalEntry).filter(
            JournalEntry.user_id == user_id,
            JournalEntry.entry_date >= thirty_days_ago,
            JournalEntry.is_deleted == False
        ).order_by(JournalEntry.entry_date.asc())
        
        result = await self.db.execute(stmt)
        entries = result.scalars().all()
        
        if len(entries) < 5:
            # Need at least 5 points for a statistical baseline
            return {"status": "insufficient_data", "count": len(entries)}

        # 2. Extract metrics (Baseline Prep)
        stats = []
        for e in entries:
             if e.sentiment_score is not None and e.stress_level is not None:
                 stats.append({
                     "sentiment": float(e.sentiment_score),
                     "stress": float(e.stress_level)
                 })
        
        if len(stats) < 5:
             return {"status": "insufficient_metrics", "count": len(stats)}

        # 3. Offload Inference to Dedicated Process
        # This isolates the main memory from heavy ML libs if they were used
        try:
            inference_result = inference_proxy.run_inference(
                "burnout_detection", 
                {"stats": stats}
            )
            
            z_sent = inference_result["z_sentiment"]
            z_stress = inference_result["z_stress"]
            baseline_sent_mean = inference_result["baseline_sent_mean"]
            baseline_stress_mean = inference_result["baseline_stress_mean"]
            
        except Exception as e:
            logger.error(f"Inference Proxy failed: {e}. Falling back to local calculation.")
            # Fallback to local calculation if proxy fails
            sentiments = [s["sentiment"] for s in stats]
            stresses = [s["stress"] for s in stats]
            baseline_sent_mean = np.mean(sentiments[:-1])
            baseline_sent_std = np.std(sentiments[:-1]) or 1.0
            baseline_stress_mean = np.mean(stresses[:-1])
            baseline_stress_std = np.std(stresses[:-1]) or 1.0
            z_sent = (sentiments[-1] - baseline_sent_mean) / baseline_sent_std
            z_stress = (stresses[-1] - baseline_stress_mean) / baseline_stress_std

        # 4. Burnout Decision Matrix
        is_burnout = z_sent < -1.5 and z_stress > 1.5
        is_crisis = z_sent < -2.5 or z_stress > 2.5 
        
        alert_payload = {
            "user_id": user_id,
            "z_sentiment": float(z_sent),
            "z_stress": float(z_stress),
            "baseline_sent_mean": float(baseline_sent_mean),
            "baseline_stress_mean": float(baseline_stress_mean),
            "is_burnout": bool(is_burnout),
            "is_crisis": bool(is_crisis),
            "timestamp": datetime.now(UTC).isoformat()
        }

        # 5. Kafka/Redis CRISIS_ALERT Integration
        if is_crisis:
            await self._dispatch_crisis_alert(alert_payload)
        elif is_burnout:
            await self._dispatch_burnout_warning(alert_payload)
            
        return alert_payload

    async def _dispatch_crisis_alert(self, payload: Dict):
        """Dispatches a critical event via Kafka and WebSocket."""
        logger.warning(f"!!! CRISIS ALERT for User {payload['user_id']} !!!")
        
        # Topic: wellbeing_alerts
        # Used for auditing, clinical dashboard, or emergency intervention
        try:
             producer = get_kafka_producer()
             producer.queue_event({
                 "type": "CRISIS_ALERT",
                 "severity": "CRITICAL",
                 "user_id": payload["user_id"],
                 "details": payload,
                 "timestamp": datetime.now(UTC).isoformat()
             })
        except Exception as e:
            logger.error(f"Failed to push CRISIS_ALERT to Kafka: {e}")

        # Instant feedback via WebSocketmanager
        try:
            await ws_manager.send_personal_message(payload["user_id"], {
                "type": "CRITICAL_SYSTEM_ALERT",
                "title": "Emotional Health Warning",
                "message": "We've noticed a significant shift in your wellbeing patterns. Please consider taking a break or reaching out to a professional.",
                "action_url": "/help/crisis",
                "urgency": "high"
            })
        except Exception as e:
             logger.error(f"Failed to push CRISIS_ALERT to WebSocket: {e}")

    async def _dispatch_burnout_warning(self, payload: Dict):
        """Moderate warning for burnout risk."""
        try:
            # Trigger Proactive Intervention via gRPC stub
            prompt = await ProactiveInterventionService.get_intervention_prompt(
                payload["user_id"], payload
            )
            
            await ws_manager.send_personal_message(payload["user_id"], {
                "type": "WELLBEING_INSIGHT",
                "title": "Burnout Pattern Detected",
                "message": prompt,
                "z_scores": {"stress": payload["z_stress"], "sentiment": payload["z_sentiment"]},
                "suggestion": "How about a 5-minute deep breathing exercise?"
            })
        except Exception as e:
            logger.error(f"Burnout warning dispatch failed: {e}")

class ProactiveInterventionService:
    """
    Simulates a gRPC client that calls an external AI service to generate
    personalized intervention prompts based on the detected burnout trend.
    """
    @staticmethod
    async def get_intervention_prompt(user_id: int, burnout_data: Dict) -> str:
        # This is where the gRPC call would go in production:
        # channel = grpc.aio.insecure_channel('nlp-service:50051')
        # stub = NLPInterventionStub(channel)
        # response = await stub.GeneratePrompt(PromptRequest(user_id=user_id, z_stress=burnout_data['z_stress']))
        
        # Local logic for now (Personalized AI Prompts integration)
        if burnout_data["z_stress"] > 2.0:
            return "Your stress levels have spiked significantly above your personal baseline. What's one boundary you can set today to protect your peace?"
        elif burnout_data["z_sentiment"] < -2.0:
            return "You've been feeling significantly heavier than usual. Writing can help – what's the smallest step you can take toward self-care today?"
        
        return "You seem to be under consistent pressure. Remember that it's okay to ask for help or delegate one task today."

# Singleton instance
burnout_service = None

def get_burnout_service(db) -> BurnoutDetectionService:
    global burnout_service
    if burnout_service is None or burnout_service.db != db:
        burnout_service = BurnoutDetectionService(db)
    return burnout_service
