
import pytest
from fastapi.testclient import TestClient
from ...api.main import app

@pytest.fixture
def client():
    return TestClient(app)


def test_security_headers_present(client):
    """Verify security headers are added to responses."""
    response = client.get("/api/v1/health")
    # Health endpoint returns 200 when healthy, 503 when dependencies unavailable
    assert response.status_code in [200, 503]

    headers = response.headers
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    # Check Content Security Policy header
    csp = headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'none'" in csp
    assert "style-src 'none'" in csp
    assert "img-src 'self' data:" in csp
    assert "font-src 'none'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp

def test_cors_allowed_origin(client):
    """Verify CORS headers for allowed origin."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "GET" in response.headers["Access-Control-Allow-Methods"]

def test_cors_disallowed_origin(client):
    """Verify disallowed origin does not receive CORS headers."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    # By default, FastAPI CORSMiddleware returns 400 for disallowed origins on preflight
    # or just doesn't send the allow-origin header for simple requests.
    # For OPTIONS (preflight), it usually returns 200 but without Access-Control-Allow-Origin
    # or 400 depending on implementation. 
    # Let's check that the Allow-Origin header strictly matches the request origin if allowed,
    # or is missing if disallowed.
    
    assert "Access-Control-Allow-Origin" not in response.headers

def test_cors_credentials(client):
    """Verify credentials support."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
