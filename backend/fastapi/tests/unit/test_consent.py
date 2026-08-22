"""
Tests for consent management and privacy compliance.

Tests consent tracking, validation middleware, and analytics blocking.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from api.main import app
from api.services.db_service import get_db
from api.services.analytics_service import AnalyticsService


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Database session fixture."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def test_track_consent_event_given(client, db_session):
    """Test tracking consent_given event."""
    anonymous_id = "test_user_123"

    response = client.post(
        "/api/v1/consent/track",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "consent_given",
            "consent_version": "1.0"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "event_id" in data

    # Verify consent status
    status_response = client.get(f"/api/v1/consent/status/{anonymous_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["analytics_consent_given"] is True
    assert status_data["consent_version"] == "1.0"


def test_track_consent_event_revoked(client, db_session):
    """Test tracking consent_revoked event."""
    anonymous_id = "test_user_456"

    # First give consent
    client.post(
        "/api/v1/consent/track",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "consent_given",
            "consent_version": "1.0"
        }
    )

    # Then revoke consent
    response = client.post(
        "/api/v1/consent/track",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "consent_revoked",
            "consent_version": "1.0"
        }
    )

    assert response.status_code == 200

    # Verify consent is revoked
    status_response = client.get(f"/api/v1/consent/status/{anonymous_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["analytics_consent_given"] is False


def test_analytics_blocked_without_consent(client, db_session):
    """Test that analytics events are blocked without consent."""
    anonymous_id = "test_user_no_consent"

    # Try to log analytics event without consent
    response = client.post(
        "/api/v1/analytics/events",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "page_view",
            "event_name": "test_page",
            "event_data": {"page": "/test"}
        }
    )

    # Should be blocked by middleware
    assert response.status_code == 403
    data = response.json()
    assert "consent_required" in data
    assert data["consent_required"] is True


def test_analytics_allowed_with_consent(client, db_session):
    """Test that analytics events are allowed with consent."""
    anonymous_id = "test_user_with_consent"

    # Give consent first
    client.post(
        "/api/v1/consent/track",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "consent_given",
            "consent_version": "1.0"
        }
    )

    # Now try to log analytics event
    response = client.post(
        "/api/v1/analytics/events",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "page_view",
            "event_name": "test_page",
            "event_data": {"page": "/test"}
        }
    )

    # Should be allowed
    assert response.status_code == 200


def test_update_consent_preferences(client, db_session):
    """Test updating consent preferences."""
    anonymous_id = "test_user_prefs"

    response = client.put(
        f"/api/v1/consent/preferences/{anonymous_id}",
        json={
            "analytics_consent_given": True,
            "consent_version": "2.0"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["analytics_consent_given"] is True
    assert data["consent_version"] == "2.0"


def test_check_analytics_consent_endpoint(client, db_session):
    """Test the lightweight consent check endpoint."""
    anonymous_id = "test_user_check"

    # Check without consent
    response = client.get(f"/api/v1/consent/check/{anonymous_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["analytics_consent_given"] is False

    # Give consent
    client.post(
        "/api/v1/consent/track",
        json={
            "anonymous_id": anonymous_id,
            "event_type": "consent_given",
            "consent_version": "1.0"
        }
    )

    # Check with consent
    response = client.get(f"/api/v1/consent/check/{anonymous_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["analytics_consent_given"] is True


def test_consent_validation_service_methods(db_session):
    """Test consent validation service methods directly."""
    anonymous_id = "test_service_user"

    # Test initial state (no consent)
    status = AnalyticsService.check_analytics_consent(db_session, anonymous_id)
    assert status["analytics_consent_given"] is False

    # Track consent given
    AnalyticsService.track_consent_event(
        db=db_session,
        anonymous_id=anonymous_id,
        event_type="consent_given",
        consent_version="1.0"
    )

    # Check consent given
    status = AnalyticsService.check_analytics_consent(db_session, anonymous_id)
    assert status["analytics_consent_given"] is True
    assert status["consent_version"] == "1.0"

    # Track consent revoked
    AnalyticsService.track_consent_event(
        db=db_session,
        anonymous_id=anonymous_id,
        event_type="consent_revoked",
        consent_version="1.0"
    )

    # Check consent revoked
    status = AnalyticsService.check_analytics_consent(db_session, anonymous_id)
    assert status["analytics_consent_given"] is False


def test_invalid_consent_event_type(client):
    """Test validation of consent event types."""
    response = client.post(
        "/api/v1/consent/track",
        json={
            "anonymous_id": "test_user",
            "event_type": "invalid_event",
            "consent_version": "1.0"
        }
    )

    assert response.status_code == 422  # Validation error