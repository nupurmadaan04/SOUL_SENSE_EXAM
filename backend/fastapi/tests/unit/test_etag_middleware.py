"""
Unit tests for ETag Middleware

Tests:
- ETag header is added to configured paths
- 304 Not Modified returned when If-None-Match matches
- ETag skipped for streaming responses
- ETag skipped for non-GET requests
- ETag skipped for non-configured paths
"""

import pytest
import hashlib
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.testclient import TestClient

import sys
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from api.middleware.etag_middleware import (
    ETagMiddleware,
    ConditionalETagMiddleware,
    create_etag_middleware
)


# Test fixtures
@pytest.fixture
def sample_app():
    """Create a test FastAPI app with ETag middleware."""
    app = FastAPI()
    
    @app.get("/api/v1/questions")
    async def get_questions():
        return {"questions": [{"id": 1, "text": "Test question"}]}
    
    @app.get("/api/v1/questions/categories")
    async def get_categories():
        return {"categories": [{"id": 1, "name": "Test"}]}
    
    @app.get("/api/v1/questions/{question_id}")
    async def get_question(question_id: int):
        return {"id": question_id, "text": "Test question"}
    
    @app.get("/api/v1/users/me")
    async def get_user():
        return {"id": 1, "name": "Test User"}
    
    @app.post("/api/v1/questions")
    async def create_question():
        return {"id": 2, "text": "New question"}
    
    @app.get("/api/v1/stream")
    async def stream_data():
        async def generate():
            yield b"data: chunk1\n\n"
            yield b"data: chunk2\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    # Add ETag middleware
    app.add_middleware(ETagMiddleware)
    
    return app


@pytest.fixture
def client(sample_app):
    """Create a test client."""
    return TestClient(sample_app)


# Test cases
class TestETagMiddleware:
    """Test suite for ETag middleware."""
    
    def test_etag_header_added_to_questions(self, client):
        """ETag header should be added to /api/v1/questions response."""
        response = client.get("/api/v1/questions")
        
        assert response.status_code == 200
        assert "etag" in response.headers
        # ETag should be wrapped in quotes
        etag = response.headers["etag"]
        assert etag.startswith('"') and etag.endswith('"')
    
    def test_etag_header_added_to_categories(self, client):
        """ETag header should be added to /api/v1/questions/categories."""
        response = client.get("/api/v1/questions/categories")
        
        assert response.status_code == 200
        assert "etag" in response.headers
    
    def test_etag_header_added_to_specific_question(self, client):
        """ETag header should be added to /api/v1/questions/{id}."""
        response = client.get("/api/v1/questions/123")
        
        assert response.status_code == 200
        assert "etag" in response.headers
    
    def test_etag_not_added_to_unconfigured_path(self, client):
        """ETag should not be added to paths not in ETAG_ENABLED_PATHS."""
        response = client.get("/api/v1/users/me")
        
        assert response.status_code == 200
        # ETag should not be present for unconfigured paths
        assert "etag" not in response.headers
    
    def test_etag_not_added_to_post_request(self, client):
        """ETag should not be added to POST requests."""
        response = client.post("/api/v1/questions")
        
        assert response.status_code == 200
        # ETag should not be present for POST requests
        assert "etag" not in response.headers
    
    def test_304_returned_when_etag_matches(self, client):
        """304 Not Modified should be returned when If-None-Match matches ETag."""
        # First request - get the ETag
        response1 = client.get("/api/v1/questions")
        assert response1.status_code == 200
        etag = response1.headers["etag"]
        
        # Second request with If-None-Match header
        response2 = client.get(
            "/api/v1/questions",
            headers={"If-None-Match": etag}
        )
        
        # Should return 304 Not Modified
        assert response2.status_code == 304
        assert response2.headers["etag"] == etag
        # Body should be empty
        assert response2.content == b""
    
    def test_200_returned_when_etag_mismatches(self, client):
        """200 OK should be returned when If-None-Match doesn't match."""
        # Request with wrong ETag
        response = client.get(
            "/api/v1/questions",
            headers={"If-None-Match": '"wrongetag"'}
        )
        
        # Should return 200 with full response
        assert response.status_code == 200
        assert "etag" in response.headers
        assert response.json() == {"questions": [{"id": 1, "text": "Test question"}]}
    
    def test_etag_not_added_to_streaming_response(self, client):
        """ETag should not be added to streaming responses."""
        response = client.get("/api/v1/stream")
        
        assert response.status_code == 200
        # ETag should not be present for streaming responses
        assert "etag" not in response.headers


class TestConditionalETagMiddleware:
    """Test suite for ConditionalETagMiddleware."""
    
    @pytest.fixture
    def conditional_app(self):
        """Create app with conditional ETag middleware."""
        app = FastAPI()
        
        @app.get("/api/v1/questions")
        async def get_questions():
            return {"questions": [{"id": 1, "text": "Test"}]}
        
        @app.get("/api/v1/auth/login")
        async def login():
            return {"token": "test"}
        
        @app.get("/api/v1/analytics/summary")
        async def analytics():
            return {"total": 100}
        
        # Add conditional ETag middleware
        app.add_middleware(ConditionalETagMiddleware)
        
        return app
    
    @pytest.fixture
    def conditional_client(self, conditional_app):
        """Create test client for conditional app."""
        return TestClient(conditional_app)
    
    def test_etag_added_to_non_excluded_path(self, conditional_client):
        """ETag should be added to paths not in exclusion list."""
        response = conditional_client.get("/api/v1/questions")
        
        assert response.status_code == 200
        assert "etag" in response.headers
    
    def test_etag_not_added_to_auth_path(self, conditional_client):
        """ETag should not be added to auth paths."""
        response = conditional_client.get("/api/v1/auth/login")
        
        assert response.status_code == 200
        assert "etag" not in response.headers
    
    def test_etag_not_added_to_analytics_path(self, conditional_client):
        """ETag should not be added to analytics paths."""
        response = conditional_client.get("/api/v1/analytics/summary")
        
        assert response.status_code == 200
        assert "etag" not in response.headers


class TestETagFactory:
    """Test suite for ETag middleware factory."""
    
    def test_create_etag_middleware_with_custom_paths(self):
        """Factory should create middleware with custom enabled paths."""
        CustomETagMiddleware = create_etag_middleware(
            enabled_paths={"/custom/path"},
            enabled_prefixes={"/custom/"}
        )
        
        app = FastAPI()
        
        @app.get("/custom/path")
        async def custom_path():
            return {"data": "test"}
        
        @app.get("/custom/resource")
        async def custom_resource():
            return {"data": "test"}
        
        app.add_middleware(CustomETagMiddleware)
        
        client = TestClient(app)
        
        # Both paths should have ETag
        response1 = client.get("/custom/path")
        assert "etag" in response1.headers
        
        response2 = client.get("/custom/resource")
        assert "etag" in response2.headers


class TestETagComputation:
    """Test ETag computation logic."""
    
    def test_etag_is_md5_hash(self):
        """ETag should be MD5 hash wrapped in quotes."""
        from api.middleware.etag_middleware import create_etag_middleware
        
        # Create middleware with /test path enabled
        CustomETagMiddleware = create_etag_middleware(
            enabled_paths={"/test"}
        )
        
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"test": "data"}
        
        app.add_middleware(CustomETagMiddleware)
        client = TestClient(app)
        
        response = client.get("/test")
        etag = response.headers.get("etag", "")
        
        # ETag should be wrapped in quotes
        assert etag.startswith('"') and etag.endswith('"')
        
        # Inner value should be valid MD5 (32 hex characters)
        hash_value = etag[1:-1]  # Remove quotes
        assert len(hash_value) == 32
        assert all(c in '0123456789abcdef' for c in hash_value)
    
    def test_same_content_same_etag(self):
        """Same content should produce same ETag."""
        app = FastAPI()
        
        @app.get("/api/v1/questions")
        async def questions():
            return {"data": "static"}
        
        app.add_middleware(ETagMiddleware)
        client = TestClient(app)
        
        response1 = client.get("/api/v1/questions")
        response2 = client.get("/api/v1/questions")
        
        assert response1.headers["etag"] == response2.headers["etag"]
    
    def test_different_content_different_etag(self):
        """Different content should produce different ETag."""
        counter = {"value": 0}
        
        app = FastAPI()
        
        @app.get("/api/v1/questions")
        async def questions():
            counter["value"] += 1
            return {"data": counter["value"]}
        
        app.add_middleware(ETagMiddleware)
        client = TestClient(app)
        
        response1 = client.get("/api/v1/questions")
        response2 = client.get("/api/v1/questions")
        
        assert response1.headers["etag"] != response2.headers["etag"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
