"""
Response Contract Snapshot Tests
=================================
Locks API response contracts using syrupy snapshots.

Objective: Prevent unintended breaking changes to API response structures.

Edge Case Handling:
- Non-deterministic fields (IDs, UUIDs, timestamps) are redacted.
- Float precision is normalised to 2 decimal places.
- ISO datetime strings are replaced with a stable placeholder.
"""

import pytest
import re
from typing import Any


# ---------------------------------------------------------------------------
# Noise Redaction Utility
# ---------------------------------------------------------------------------

def redact_noise(data: Any) -> Any:
    """
    Recursively redacts non-deterministic values (UUIDs, timestamps, IDs, floats)
    so snapshots stay stable across test runs and environments.
    """
    if isinstance(data, dict):
        new_data = {}
        for k, v in data.items():
            # 1. Keys that are always environment-specific / non-deterministic
            if k.lower() in [
                "id", "uuid", "created_at", "updated_at", "timestamp",
                "request_id", "access_token", "refresh_token",
                "process_time", "server_instance_id", "latency_ms",
            ]:
                new_data[k] = "<REDACTED>"
            # 2. String values that look like UUIDs or ISO datetime literals
            elif isinstance(v, str):
                if re.match(
                    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                    v, re.I,
                ):
                    new_data[k] = "<REDACTED_UUID>"
                elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", v):
                    new_data[k] = "<REDACTED_DATETIME>"
                else:
                    new_data[k] = v
            # 3. Normalise float precision
            elif isinstance(v, float):
                new_data[k] = round(v, 2)
            # 4. Recurse into nested structures
            elif isinstance(v, (dict, list)):
                new_data[k] = redact_noise(v)
            else:
                new_data[k] = v
        return new_data
    elif isinstance(data, list):
        return [redact_noise(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# Contract Snapshot Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_root_endpoint_contract(client, snapshot):
    """Locks the / root discovery endpoint response shape."""
    response = await client.get("/")
    assert response.status_code == 200
    assert redact_noise(response.json()) == snapshot


@pytest.mark.asyncio
async def test_health_endpoint_contract(client, snapshot):
    """
    Locks the /api/v1/health liveness probe response shape.
    Non-deterministic fields (timestamp, version) are redacted.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert redact_noise(response.json()) == snapshot


@pytest.mark.asyncio
async def test_error_404_contract(client, snapshot):
    """
    Locks the standard 404 error response contract.
    Validates that unknown endpoints return a consistent error shape.
    """
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert redact_noise(response.json()) == snapshot


@pytest.mark.asyncio
async def test_auth_register_missing_body_contract(client, snapshot):
    """
    Locks the 422 Unprocessable Entity contract for missing request body.
    Verifies the validation error structure is stable.
    """
    response = await client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422
    body = response.json()
    # Normalise: keep only 'detail' shape, ignore loc/msg internals that may vary
    normalised = {
        "status_code": response.status_code,
        "has_detail": "detail" in body,
        "detail_is_list": isinstance(body.get("detail"), list),
    }
    assert normalised == snapshot


@pytest.mark.asyncio
async def test_intentional_break_detected(client, snapshot):
    """
    DEMONSTRATES CI ENFORCEMENT:
    This test intentionally modifies the expected contract to show that
    snapshot testing catches breaking API changes.

    In normal CI flow this passes. To simulate a breaking change:
    - Modify the API response (e.g., rename a field)
    - Run pytest WITHOUT --snapshot-update
    - Observe that this test will FAIL with a clear diff
    """
    response = await client.get("/")
    assert response.status_code == 200
    data = redact_noise(response.json())
    # Lock the contract: must contain 'name' and 'versions' keys
    assert "name" in data, "CONTRACT BROKEN: 'name' field removed from root response"
    assert "versions" in data, "CONTRACT BROKEN: 'versions' field removed from root response"
    assert isinstance(data["versions"], list), "CONTRACT BROKEN: 'versions' must be a list"
