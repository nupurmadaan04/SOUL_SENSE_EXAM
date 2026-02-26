import pytest
import os
import shutil
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.fastapi.api.main import app
from backend.fastapi.api.root_models import User, Score
from app.auth.auth import AuthManager
from backend.fastapi.api.services.export_service import ExportService
from backend.fastapi.api.routers.export import _export_rate_limits

# Setup client
client = TestClient(app)

@pytest.fixture
def auth_headers(temp_db: Session):
    """Creates a test user and returns auth headers."""
    username = "export_user"
    password = "ExportPass123!"
    email = "export@example.com"
    
    # Cleanup
    temp_db.query(User).filter_by(username=username).delete()
    temp_db.commit()
    
    # Create user
    auth = AuthManager()
    auth.register_user(username, email, "Export", "User", 30, "M", password)
    
    # Login
    response = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def clean_exports():
    """Cleanup exports directory and rate limits before/after tests."""
    # Ensure dir exists
    ExportService.ensure_export_dir()
    
    # Clear directory
    for f in ExportService.EXPORT_DIR.glob("*"):
        if f.is_file():
            f.unlink()
            
    # Clear rate limits
    _export_rate_limits.clear()
            
    yield
    
    # Cleanup after
    for f in ExportService.EXPORT_DIR.glob("*"):
        if f.is_file():
            f.unlink()
    
    _export_rate_limits.clear()

def test_export_json_flow(auth_headers, temp_db, clean_exports):
    """Test generating and downloading a JSON export."""
    # 1. Generate Data (Score)
    # We need a score for the user
    user = temp_db.query(User).filter_by(username="export_user").first()
    score = Score(
        user_id=user.id,
        username=user.username,
        total_score=30,
        sentiment_score=50.0,
        reflection_text="Test reflection",
        timestamp="2023-01-01T12:00:00",
        age=30,
        detailed_age_group="Adult"
    )
    temp_db.add(score)
    temp_db.commit()
    
    # 2. Request Export
    response = client.post("/api/v1/export", json={"format": "json"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "job_id" in data
    assert "download_url" in data
    
    job_id = data["job_id"]
    download_url = data["download_url"]
    
    # 3. Check Status Endpoint
    status_response = client.get(f"/api/v1/export/{job_id}/status", headers=auth_headers)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "completed"
    assert status_data["job_id"] == job_id
    
    # 4. Download File
    file_response = client.get(download_url, headers=auth_headers)
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "application/octet-stream"
    
    # Verify Content
    content = file_response.json()
    assert content["meta"]["username"] == "export_user"
    assert len(content["data"]) == 1
    assert content["data"][0]["total_score"] == 30

def test_export_status_access_control(auth_headers, temp_db, clean_exports):
    """Test that users cannot check status of others' jobs."""
    # Create Job (implicitly via export)
    user = temp_db.query(User).filter_by(username="export_user").first()
    ExportService.generate_export(temp_db, user, "json")
    
    # Get a job ID we just created
    # Since we can't easily get it without API return, we'll manually insert one into _export_jobs for testing isolation
    # or just use the API flow.
    response = client.post("/api/v1/export", json={"format": "json"}, headers=auth_headers)
    job_id = response.json()["job_id"]
    
    # Simulate another user trying to access it
    # We need a second user token
    auth = AuthManager()
    auth.register_user("hacker", "hacker@example.com", "Hack", "User", 20, "M", "HackPass123!")
    login_resp = client.post("/api/v1/auth/login", data={"username": "hacker", "password": "HackPass123!"})
    hacker_token = login_resp.json()["access_token"]
    hacker_headers = {"Authorization": f"Bearer {hacker_token}"}
    
    # Attempt access
    status_resp = client.get(f"/api/v1/export/{job_id}/status", headers=hacker_headers)
    assert status_resp.status_code == 403

def test_export_csv_injection(auth_headers, temp_db, clean_exports):
    """Test CSV injection prevention."""
    user = temp_db.query(User).filter_by(username="export_user").first()
    
    # Inject malicious reflection
    malicious_text = "=cmd|' /C calc'!A0"
    score = Score(
        user_id=user.id,
        username=user.username,
        total_score=10,
        sentiment_score=10.0,
        reflection_text=malicious_text, # Injection payload
        timestamp="2023-01-01T12:00:00",
        age=30,
        detailed_age_group="Adult"
    )
    temp_db.add(score)
    temp_db.commit()
    
    # Export CSV
    response = client.post("/api/v1/export", json={"format": "csv"}, headers=auth_headers)
    assert response.status_code == 200
    download_url = response.json()["download_url"]
    
    # Download
    file_response = client.get(download_url, headers=auth_headers)
    assert file_response.status_code == 200
    
    content = file_response.text
    # Verify payload is neutralized with simple quote
    # CSV writer might double quote fields: "'=cmd..."
    assert f"'{malicious_text}" in content or f"'={malicious_text}" in content or ("'=" in content and "cmd" in content)

def test_rate_limiting(auth_headers, clean_exports):
    """Test rate limiting prevents rapid requests."""
    # First request
    r1 = client.post("/api/v1/export", json={"format": "json"}, headers=auth_headers)
    assert r1.status_code == 200 or r1.status_code == 429 # Might be 429 if previous test just ran
    
    # Second request immediately
    r2 = client.post("/api/v1/export", json={"format": "json"}, headers=auth_headers)
    assert r2.status_code == 429
    assert "Rate limit exceeded" in r2.json()["detail"]

def test_unauthorized_download_traversal(auth_headers, clean_exports):
    """Test preventing path traversal."""
    # Try to access a known file outside exports
    # e.g. ../requirements.txt 
    # The router expects {filename} in URL.
    
    traversal_filename = "..%2Frequirements.txt"  # URL encoded ../
    response = client.get(f"/api/v1/export/{traversal_filename}/download", headers=auth_headers)
    
    # Should get 403 or 404 depending on validation order
    # Service validation returns False for validate_export_access first
    assert response.status_code in (403, 404) 

def test_invalid_format(auth_headers):
    response = client.post("/api/v1/export", json={"format": "xml"}, headers=auth_headers)
    assert response.status_code == 400
