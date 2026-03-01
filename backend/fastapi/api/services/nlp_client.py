import grpc
import logging
from typing import Optional, Dict, Any
from protos import sentiment_pb2, sentiment_pb2_grpc
from api.config import get_settings_instance

logger = logging.getLogger("api.nlp_client")
settings = get_settings_instance()

class NLPClient:
    """
    Asynchronous gRPC client for AI Sentiment Analysis microservice (#1126).
    """
    def __init__(self, target: str = None):
        # Default to localhost if not specified in settings
        self.target = target or getattr(settings, "nlp_service_url", "localhost:50051")
        self._channel = None
        self._stub = None

    async def __aenter__(self):
        self._channel = grpc.aio.insecure_channel(self.target)
        self._stub = sentiment_pb2_grpc.SentimentAnalysisStub(self._channel)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._channel:
            await self._channel.close()

    async def analyze_sentiment(self, text: str, journal_id: int, user_id: int) -> Dict[str, Any]:
        """
        Calls the gRPC microservice to analyze sentiment.
        """
        try:
            async with grpc.aio.insecure_channel(self.target) as channel:
                stub = sentiment_pb2_grpc.SentimentAnalysisStub(channel)
                request = sentiment_pb2.AnalyzeSentimentRequest(
                    text=text,
                    journal_id=str(journal_id),
                    user_id=str(user_id)
                )
                
                logger.info(f"Sending gRPC request to {self.target} for journal {journal_id}")
                response = await stub.AnalyzeSentiment(request, timeout=5.0)
                
                return {
                    "score": response.score,
                    "label": response.label,
                    "patterns": list(response.patterns)
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC call failed: {e.code()} - {e.details()}")
            return {"score": 50.0, "label": "neutral", "patterns": ["fallback"]}
        except Exception as e:
            logger.error(f"Unexpected error in NLP gRPC client: {e}")
            return {"score": 50.0, "label": "neutral", "patterns": ["error"]}

    async def stream_sentiment(self, text: str, journal_id: int, user_id: int) -> Dict[str, Any]:
        """
        Streams text parts to the gRPC service for analysis (#1126).
        """
        try:
            async with grpc.aio.insecure_channel(self.target) as channel:
                stub = sentiment_pb2_grpc.SentimentAnalysisStub(channel)
                
                async def request_iterator():
                    # Split text into chunks to demonstrate streaming
                    chunk_size = 500
                    for i in range(0, len(text), chunk_size):
                        yield sentiment_pb2.AnalyzeSentimentRequest(
                            text=text[i:i+chunk_size],
                            journal_id=str(journal_id),
                            user_id=str(user_id)
                        )
                
                logger.info(f"Streaming text chunks to {self.target} for journal {journal_id}")
                responses = stub.StreamSentiment(request_iterator())
                
                final_score = 0
                patterns = set()
                count = 0
                
                async for resp in responses:
                    final_score += resp.score
                    patterns.update(resp.patterns)
                    count += 1
                
                return {
                    "score": round(final_score / max(count, 1), 2),
                    "label": "processed_via_stream",
                    "patterns": list(patterns)
                }
        except Exception as e:
            logger.error(f"gRPC streaming failed: {e}")
            return await self.analyze_sentiment(text, journal_id, user_id) # Fallback to single call

_nlp_client = None

def get_nlp_client():
    global _nlp_client
    if _nlp_client is None:
        _nlp_client = NLPClient()
    return _nlp_client
