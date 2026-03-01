import asyncio
import logging
import grpc
from protos import sentiment_pb2, sentiment_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nlp_mock_server")

class SentimentAnalysisServicer(sentiment_pb2_grpc.SentimentAnalysisServicer):
    """
    Mock implementation of the Sentiment Analysis microservice (#1126).
    """
    async def AnalyzeSentiment(self, request, context):
        logger.info(f"Received sentiment request for journal {request.journal_id} from user {request.user_id}")
        logger.info(f"Analyzing text (len={len(request.text)})...")
        
        # Simulate heavy processing delay
        await asyncio.sleep(1.0)
        
        # Mock logic
        text_lower = request.text.lower()
        score = 50.0
        label = "neutral"
        patterns = []
        
        if "happy" in text_lower or "great" in text_lower:
            score = 85.0
            label = "positive"
            patterns = ["joy", "optimism"]
        elif "sad" in text_lower or "bad" in text_lower or "angry" in text_lower:
            score = 20.0
            label = "negative"
            patterns = ["distress", "negativity"]
        else:
            patterns = ["neutral_observation"]

        return sentiment_pb2.AnalyzeSentimentResponse(
            score=score,
            label=label,
            patterns=patterns,
            journal_id=request.journal_id
        )

    async def StreamSentiment(self, request_iterator, context):
        async for request in request_iterator:
            logger.info(f"Received stream chunk for journal {request.journal_id}")
            # Process chunk
            score = 50.0 + (len(request.text) % 50)
            yield sentiment_pb2.AnalyzeSentimentResponse(
                score=score,
                label="streaming_chunk",
                patterns=["chunk_processed"],
                journal_id=request.journal_id
            )

async def serve():
    server = grpc.aio.server()
    sentiment_pb2_grpc.add_SentimentAnalysisServicer_to_server(SentimentAnalysisServicer(), server)
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logger.info(f"NLP Mock Server starting on {listen_addr}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
