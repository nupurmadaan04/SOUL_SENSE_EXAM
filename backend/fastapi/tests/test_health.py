"""
Health Endpoint Test

Tests the /health endpoint for issue #1058.
Run with: python -m pytest backend/fastapi/tests/test_health.py -v
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import the health functions directly instead of the full app
from backend.fastapi.api.routers.health import health_check, check_database, check_redis
from backend.fastapi.api.schemas import ServiceStatus


def test_check_database_success():
    """Test database check when successful."""
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.fetchone.return_value = [1]
    mock_db.execute.return_value = mock_result

    status = check_database(mock_db)

    assert status.status == "healthy"
    assert status.latency_ms is not None
    assert status.latency_ms > 0


def test_check_database_failure():
    """Test database check when failed."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("Connection failed")

    status = check_database(mock_db)

    assert status.status == "unhealthy"
    assert "Connection failed" in status.message
    assert status.latency_ms is None


def test_check_redis_success():
    """Test Redis check when successful."""
    mock_redis = Mock()
    mock_redis.ping.return_value = True

    status = check_redis(mock_redis)

    assert status.status == "healthy"
    assert status.latency_ms is not None
    assert status.latency_ms > 0


def test_check_redis_failure():
    """Test Redis check when failed."""
    mock_redis = Mock()
    mock_redis.ping.side_effect = Exception("Connection refused")

    status = check_redis(mock_redis)

    assert status.status == "unhealthy"
    assert "Connection refused" in status.message
    assert status.latency_ms is None


@pytest.mark.asyncio
async def test_health_check_all_healthy():
    """Test health check when all services are healthy."""
    from backend.fastapi.api.schemas import HealthResponse

    with patch('backend.fastapi.api.routers.health.check_database') as mock_db_check, \
         patch('backend.fastapi.api.routers.health.check_redis') as mock_redis_check:

        mock_db_check.return_value = ServiceStatus(status="healthy", latency_ms=5.2)
        mock_redis_check.return_value = ServiceStatus(status="healthy", latency_ms=2.1)

        response = await health_check()

        assert response.status == "healthy"
        assert response.services["database"].status == "healthy"
        assert response.services["redis"].status == "healthy"
        assert "version" in response.model_dump()


@pytest.mark.asyncio
async def test_health_check_database_unhealthy():
    """Test health check when database is unhealthy."""
    from backend.fastapi.api.schemas import HealthResponse

    with patch('backend.fastapi.api.routers.health.check_database') as mock_db_check, \
         patch('backend.fastapi.api.routers.health.check_redis') as mock_redis_check:

        mock_db_check.return_value = ServiceStatus(
            status="unhealthy",
            message="Connection timeout",
            latency_ms=None
        )
        mock_redis_check.return_value = ServiceStatus(status="healthy", latency_ms=2.1)

        response = await health_check()

        assert response.status == "unhealthy"
        assert response.services["database"].status == "unhealthy"
        assert response.services["redis"].status == "healthy"


@pytest.mark.asyncio
async def test_health_check_redis_unhealthy():
    """Test health check when Redis is unhealthy."""
    from backend.fastapi.api.schemas import HealthResponse

    with patch('backend.fastapi.api.routers.health.check_database') as mock_db_check, \
         patch('backend.fastapi.api.routers.health.check_redis') as mock_redis_check:

        mock_db_check.return_value = ServiceStatus(status="healthy", latency_ms=5.2)
        mock_redis_check.return_value = ServiceStatus(
            status="unhealthy",
            message="Connection refused",
            latency_ms=None
        )

        response = await health_check()

        assert response.status == "unhealthy"
        assert response.services["database"].status == "healthy"
        assert response.services["redis"].status == "unhealthy"


@pytest.mark.asyncio
async def test_health_check_all_unhealthy():
    """Test health check when all services are unhealthy."""
    from backend.fastapi.api.schemas import HealthResponse

    with patch('backend.fastapi.api.routers.health.check_database') as mock_db_check, \
         patch('backend.fastapi.api.routers.health.check_redis') as mock_redis_check:

        mock_db_check.return_value = ServiceStatus(
            status="unhealthy",
            message="Connection failed",
            latency_ms=None
        )
        mock_redis_check.return_value = ServiceStatus(
            status="unhealthy",
            message="Connection refused",
            latency_ms=None
        )

        response = await health_check()

        assert response.status == "unhealthy"
        assert response.services["database"].status == "unhealthy"
        assert response.services["redis"].status == "unhealthy"</content>
