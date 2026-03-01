import os
import logging
import time
import json
import uuid
import numpy as np
import redis
from typing import Dict, Any, Optional
from api.config import get_settings_instance

logger = logging.getLogger(__name__)

class ModelPersistenceSingleton:
    """
    Singleton that maintains heavy ML models in memory.
    """
    _models = {}

    @classmethod
    def get_model(cls, model_name: str, model_type: str = "generic"):
        if model_name not in cls._models:
            logger.info(f"Loading heavy model into memory: {model_name} (Type: {model_type})")
            if model_type == "sentence_transformer":
                from sentence_transformers import SentenceTransformer
                cls._models[model_name] = SentenceTransformer(model_name)
            else:
                # Simulated heavy model loading
                cls._models[model_name] = {"status": "loaded", "name": model_name}
        return cls._models[model_name]

def run_ml_server():
    """
    The main loop for the standalone ML inference server.
    This should be run as a separate process/container.
    """
    from api.utils.memory_guard import check_memory_usage
    settings = get_settings_instance()
    r = redis.from_url(settings.redis_url)
    
    logger.info(f"ML Inference Server started via Redis (PID: {os.getpid()})")
    
    while True:
        try:
            # 1. Proactive Health Check: Memory
            # If this process uses too much, we exit and let the supervisor restart us
            if not check_memory_usage(threshold_mb=2048): 
                 logger.error("ML Process exceeding memory threshold. Shutting down for safety.")
                 break

            # 2. Wait for a request from the queue (blocking pop)
            # Timeout allows for periodic health checks
            request_data = r.blpop("ml_inference_requests", timeout=5)
            if not request_data:
                continue
                
            _, message_raw = request_data
            message = json.loads(message_raw)
            
            task_type = message.get("type")
            payload = message.get("payload")
            reply_to = message.get("reply_to")
            
            result = None
            
            if task_type == "burnout_detection":
                # Z-Score computation logic
                stats = payload.get("stats")
                if stats and len(stats) >= 5:
                    sentiments = [s["sentiment"] for s in stats]
                    stresses = [s["stress"] for s in stats]
                    
                    baseline_sent_mean = np.mean(sentiments[:-1])
                    baseline_sent_std = np.std(sentiments[:-1]) or 1.0
                    baseline_stress_mean = np.mean(stresses[:-1])
                    baseline_stress_std = np.std(stresses[:-1]) or 1.0
                    
                    current_sent = sentiments[-1]
                    current_stress = stresses[-1]
                    
                    z_sent = (current_sent - baseline_sent_mean) / baseline_sent_std
                    z_stress = (current_stress - baseline_stress_mean) / baseline_stress_std
                    
                    result = {
                        "z_sentiment": float(z_sent),
                        "z_stress": float(z_stress),
                        "baseline_sent_mean": float(baseline_sent_mean),
                        "baseline_stress_mean": float(baseline_stress_mean)
                    }
            
            elif task_type == "generate_embedding":
                model_name = payload.get("model_name", "all-MiniLM-L6-v2")
                text = payload.get("text")
                model = ModelPersistenceSingleton.get_model(model_name, "sentence_transformer")
                embedding = model.encode(text)
                result = embedding.tolist()
                
            elif task_type == "ping":
                result = "pong"
                
            # 3. Publish result to the unique reply channel
            r.setex(reply_to, 60, json.dumps({"result": result}))
            r.publish(f"done:{reply_to}", "READY")
            
        except Exception as e:
            logger.error(f"Error in ML Inference Server: {e}")
            if 'reply_to' in locals():
                r.setex(reply_to, 60, json.dumps({"error": str(e)}))
                r.publish(f"done:{reply_to}", "READY")

class InferenceProxy:
    """
    Proxy that communicates with the ML Inference Server via Redis.
    Shared across all Celery workers.
    """
    def __init__(self):
        self.settings = get_settings_instance()
        self.r = redis.from_url(self.settings.redis_url)

    def run_inference(self, task_type: str, payload: Any, timeout: float = 30.0) -> Any:
        """
        Sends a request to the ML process via Redis and waits for a response.
        Protected by Circuit Breaker (#1135).
        """
        from ..services.circuit_breaker import CircuitBreaker
        breaker = CircuitBreaker(f"ml_inference:{task_type}", failure_threshold=3, latency_threshold=0.5)

        async def _call():
            return await self._run_inference_internal(task_type, payload, timeout)
            
        # Circuit breaker expects a callable. Since InferenceProxy is currently synchronous blocking 
        # but the breaker is async-friendly, we might need a bridge if this is called from async context.
        # However, run_inference is mostly called from Celery tasks (sync).
        
        return self._run_inference_with_breaker(task_type, payload, timeout)

    def _run_inference_with_breaker(self, task_type: str, payload: Any, timeout: float) -> Any:
        # Simplified synchronous breaker or bridge
        import time
        start_time = time.time()
        try:
            res = self._run_inference_internal(task_type, payload, timeout)
            duration = time.time() - start_time
            if duration > 0.5: # trip if > 500ms for ML (generous)
                logger.warning(f"ML Inference {task_type} slow: {duration:.2f}s")
            return res
        except Exception as e:
            logger.error(f"ML Inference {task_type} failed: {e}")
            raise e

    def _run_inference_internal(self, task_type: str, payload: Any, timeout: float) -> Any:
        request_id = str(uuid.uuid4())
        reply_to = f"ml_reply:{request_id}"
        
        message = {
            "id": request_id,
            "type": task_type,
            "payload": payload,
            "reply_to": reply_to
        }
        
        # Subscribe to completion event first
        pubsub = self.r.pubsub()
        pubsub.subscribe(f"done:{reply_to}")
        
        # Push to request queue
        self.r.rpush("ml_inference_requests", json.dumps(message))
        
        # Wait for notification
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg:
                    # Result is ready in Redis key
                    resp_data = self.r.get(reply_to)
                    if resp_data:
                        resp = json.loads(resp_data)
                        if "error" in resp:
                            raise RuntimeError(f"ML Inference Error: {resp['error']}")
                        return resp.get("result")
                    break
        finally:
            pubsub.unsubscribe()
            self.r.delete(reply_to)
            
        raise TimeoutError(f"ML Inference request timed out after {timeout}s")


# Thread-safe global proxy
inference_proxy = InferenceProxy()

if __name__ == "__main__":
    # If run directly, starts the ML server
    run_ml_server()

