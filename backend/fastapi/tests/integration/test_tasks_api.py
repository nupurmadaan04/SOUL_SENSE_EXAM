"""
Integration tests for Background Tasks API endpoints.

Tests cover:
- POST /api/v1/reports/export/async - Async export creation
- GET /api/v1/tasks/{job_id} - Task status polling
- GET /api/v1/tasks - List user tasks
- DELETE /api/v1/tasks/{job_id} - Cancel pending task
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json


class TestTasksAPI:
    """Integration tests for tasks API endpoints."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.is_active = True
        user.is_deleted = False
        user.deleted_at = None
        return user
    
    @pytest.fixture
    def mock_job(self):
        """Create a mock background job."""
        from datetime import timezone, datetime
        UTC = timezone.utc
        job = Mock()
        job.job_id = "test-job-uuid-123"
        job.user_id = 1
        job.task_type = "export_pdf"
        job.status = "pending"
        job.progress = 0
        job.params = '{"format": "pdf"}'
        job.result = None
        job.error_message = None
        job.created_at = datetime.now(UTC)
        job.started_at = None
        job.completed_at = None
        job.updated_at = datetime.now(UTC)
        return job
    
    @pytest.fixture
    def mock_completed_job(self, mock_job):
        """Create a mock completed job."""
        from datetime import timezone, datetime
        UTC = timezone.utc
        mock_job.status = "completed"
        mock_job.progress = 100
        mock_job.result = '{"filepath": "/exports/test.pdf", "export_id": "export-123"}'
        mock_job.completed_at = datetime.now(UTC)
        return mock_job
    
    def test_async_export_returns_202(self, mock_user):
        """Test async export endpoint returns 202 Accepted."""
        from api.main import app
        
        with patch('api.routers.export.get_current_user', return_value=mock_user):
            with patch('api.routers.export._check_rate_limit'):
                with patch('api.routers.export.BackgroundTaskService') as MockService:
                    mock_task = Mock()
                    mock_task.job_id = "new-task-123"
                    MockService.get_pending_tasks_count.return_value = 0
                    MockService.create_task.return_value = mock_task
                    
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/reports/export/async",
                        json={"format": "pdf"},
                        headers={"Authorization": "Bearer fake-token"}
                    )
                    
                    assert response.status_code == 202
                    data = response.json()
                    assert "job_id" in data
                    assert data["status"] == "processing"
                    assert "poll_url" in data
    
    def test_get_task_status_success(self, mock_user, mock_job):
        """Test getting task status returns correct data."""
        from api.main import app
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_task.return_value = mock_job
                
                client = TestClient(app)
                response = client.get(
                    f"/api/v1/tasks/{mock_job.job_id}",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["job_id"] == mock_job.job_id
                assert data["status"] == "pending"
                assert data["task_type"] == "export_pdf"
                assert data["created_at"].endswith("+00:00")
    
    def test_get_task_not_found(self, mock_user):
        """Test 404 when task not found."""
        from api.main import app
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_task.return_value = None
                
                client = TestClient(app)
                response = client.get(
                    "/api/v1/tasks/nonexistent-job",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 404
    
    def test_get_completed_task_with_result(self, mock_user, mock_completed_job):
        """Test getting completed task includes result data."""
        from api.main import app
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_task.return_value = mock_completed_job
                
                client = TestClient(app)
                response = client.get(
                    f"/api/v1/tasks/{mock_completed_job.job_id}",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["progress"] == 100
                assert data["result"] is not None
                assert "filepath" in data["result"]
    
    def test_list_user_tasks(self, mock_user, mock_job):
        """Test listing all tasks for a user."""
        from api.main import app
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_user_tasks.return_value = [mock_job]
                
                client = TestClient(app)
                response = client.get(
                    "/api/v1/tasks",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 1
                assert len(data["tasks"]) == 1
                assert data["tasks"][0]["created_at"].endswith("+00:00")
    
    def test_list_tasks_with_filter(self, mock_user, mock_job):
        """Test listing tasks with status filter."""
        from api.main import app
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_user_tasks.return_value = [mock_job]
                
                client = TestClient(app)
                response = client.get(
                    "/api/v1/tasks?status=pending",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
    
    def test_cancel_pending_task(self, mock_user, mock_job):
        """Test cancelling a pending task."""
        from api.main import app
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_task.return_value = mock_job
                
                client = TestClient(app)
                response = client.delete(
                    f"/api/v1/tasks/{mock_job.job_id}",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "cancelled"
    
    def test_cannot_cancel_processing_task(self, mock_user, mock_job):
        """Test cannot cancel a task that's already processing."""
        from api.main import app
        
        mock_job.status = "processing"
        
        with patch('api.routers.tasks.get_current_user', return_value=mock_user):
            with patch('api.routers.tasks.BackgroundTaskService') as MockService:
                MockService.get_task.return_value = mock_job
                
                client = TestClient(app)
                response = client.delete(
                    f"/api/v1/tasks/{mock_job.job_id}",
                    headers={"Authorization": "Bearer fake-token"}
                )
                
                assert response.status_code == 400
    
    def test_rate_limit_on_async_export(self, mock_user):
        """Test rate limiting prevents too many pending tasks."""
        from api.main import app
        
        with patch('api.routers.export.get_current_user', return_value=mock_user):
            with patch('api.routers.export._check_rate_limit'):
                with patch('api.routers.export.BackgroundTaskService') as MockService:
                    # Simulate 5 pending tasks already
                    MockService.get_pending_tasks_count.return_value = 5
                    
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/reports/export/async",
                        json={"format": "pdf"},
                        headers={"Authorization": "Bearer fake-token"}
                    )
                    
                    assert response.status_code == 429
                    assert "Too many pending exports" in response.json()["detail"]


class TestAsyncPDFExport:
    """Integration tests specifically for async PDF export."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock authenticated user."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.is_active = True
        user.is_deleted = False
        user.deleted_at = None
        return user
    
    def test_async_pdf_export_convenience_endpoint(self, mock_user):
        """Test the /async/pdf convenience endpoint."""
        from api.main import app
        
        with patch('api.routers.export.get_current_user', return_value=mock_user):
            with patch('api.routers.export._check_rate_limit'):
                with patch('api.routers.export.BackgroundTaskService') as MockService:
                    mock_task = Mock()
                    mock_task.job_id = "pdf-task-123"
                    MockService.get_pending_tasks_count.return_value = 0
                    MockService.create_task.return_value = mock_task
                    
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/reports/export/async/pdf",
                        json={"include_charts": True},
                        headers={"Authorization": "Bearer fake-token"}
                    )
                    
                    assert response.status_code == 202
                    data = response.json()
                    assert data["format"] == "pdf"
    
    def test_invalid_format_rejected(self, mock_user):
        """Test that invalid formats are rejected."""
        from api.main import app
        
        with patch('api.routers.export.get_current_user', return_value=mock_user):
            with patch('api.routers.export._check_rate_limit'):
                with patch('api.routers.export.BackgroundTaskService') as MockService:
                    MockService.get_pending_tasks_count.return_value = 0
                    
                    client = TestClient(app)
                    response = client.post(
                        "/api/v1/reports/export/async",
                        json={"format": "invalid_format"},
                        headers={"Authorization": "Bearer fake-token"}
                    )
                    
                    assert response.status_code == 400
                    assert "Unsupported format" in response.json()["detail"]
