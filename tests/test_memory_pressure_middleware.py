import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.fastapi.api.middleware.memory_pressure_middleware import MemoryPressureMiddleware
from backend.fastapi.api.utils.cgroup_memory_monitor import MemoryPressure

@pytest.fixture
def app():
    """Create test FastAPI app with memory pressure middleware."""
    app = FastAPI()
    app.add_middleware(MemoryPressureMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)

def test_normal_pressure_allows_requests(client):
    """Test requests pass through under normal memory pressure."""
    with patch('backend.fastapi.api.utils.cgroup_memory_monitor.get_memory_monitor') as mock_monitor:
        mock_instance = MagicMock()
        mock_instance.should_throttle.return_value = False
        mock_monitor.return_value = mock_instance
        
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

def test_high_pressure_allows_requests(client):
    """Test requests still pass under high (but not critical) pressure."""
    with patch('backend.fastapi.api.utils.cgroup_memory_monitor.get_memory_monitor') as mock_monitor:
        mock_instance = MagicMock()
        mock_instance.should_throttle.return_value = True
        mock_instance.get_memory_pressure.return_value = MemoryPressure(
            usage_bytes=1800000000, limit_bytes=2000000000,
            usage_percent=90, pressure_level="high", is_containerized=True
        )
        mock_monitor.return_value = mock_instance
        
        response = client.get("/test")
        assert response.status_code == 200

def test_critical_pressure_blocks_requests(client):
    """Test requests blocked under critical memory pressure."""
    with patch('backend.fastapi.api.utils.cgroup_memory_monitor.get_memory_monitor') as mock_monitor:
        mock_instance = MagicMock()
        mock_instance.should_throttle.return_value = True
        mock_instance.get_memory_pressure.return_value = MemoryPressure(
            usage_bytes=1950000000, limit_bytes=2000000000,
            usage_percent=97.5, pressure_level="critical", is_containerized=True
        )
        mock_monitor.return_value = mock_instance
        
        response = client.get("/test")
        assert response.status_code == 503
        assert "service_unavailable" in response.json()["error"]
        assert "Retry-After" in response.headers
