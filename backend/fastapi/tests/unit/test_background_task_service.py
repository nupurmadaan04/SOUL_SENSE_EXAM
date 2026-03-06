"""
Unit tests for Background Task Service.

Tests cover:
- Task creation and tracking
- Status updates
- Task execution wrapper
- User task queries
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import timezone, datetime, timedelta
UTC = timezone.utc
import json

from api.services.background_task_service import (
    BackgroundTaskService,
    TaskStatus,
    TaskType,
    background_task
)


class TestBackgroundTaskService:
    """Tests for BackgroundTaskService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        return db
    
    @pytest.fixture
    def mock_job(self):
        """Create a mock BackgroundJob."""
        job = Mock()
        job.job_id = "test-job-123"
        job.user_id = 1
        job.task_type = TaskType.EXPORT_PDF.value
        job.status = TaskStatus.PENDING.value
        job.progress = 0
        job.params = None
        job.result = None
        job.error_message = None
        job.created_at = datetime.now(UTC)
        job.started_at = None
        job.completed_at = None
        job.updated_at = datetime.now(UTC)
        return job
    
    def test_create_task_success(self, mock_db):
        """Test successful task creation."""
        with patch('api.services.background_task_service.BackgroundJob') as MockJob:
            mock_job_instance = Mock()
            mock_job_instance.job_id = "generated-uuid"
            MockJob.return_value = mock_job_instance
            
            job = BackgroundTaskService.create_task(
                db=mock_db,
                user_id=1,
                task_type=TaskType.EXPORT_PDF,
                params={"format": "pdf"}
            )
            
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    def test_create_task_with_params(self, mock_db):
        """Test task creation with parameters serialized to JSON."""
        with patch('api.services.background_task_service.BackgroundJob') as MockJob:
            mock_job_instance = Mock()
            MockJob.return_value = mock_job_instance
            
            params = {"format": "pdf", "include_charts": True}
            BackgroundTaskService.create_task(
                db=mock_db,
                user_id=1,
                task_type=TaskType.EXPORT_PDF,
                params=params
            )
            
            # Verify params were passed (as JSON string)
            call_kwargs = MockJob.call_args[1]
            assert call_kwargs.get('params') == json.dumps(params)
    
    def test_update_task_status_to_processing(self, mock_db, mock_job):
        """Test updating task status to processing."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        result = BackgroundTaskService.update_task_status(
            db=mock_db,
            job_id="test-job-123",
            status=TaskStatus.PROCESSING
        )
        
        assert mock_job.status == TaskStatus.PROCESSING.value
        assert mock_job.started_at is not None
        mock_db.commit.assert_called_once()
    
    def test_update_task_status_to_completed(self, mock_db, mock_job):
        """Test updating task status to completed."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        result = BackgroundTaskService.update_task_status(
            db=mock_db,
            job_id="test-job-123",
            status=TaskStatus.COMPLETED,
            result={"filepath": "/path/to/file.pdf"}
        )
        
        assert mock_job.status == TaskStatus.COMPLETED.value
        assert mock_job.completed_at is not None
        assert mock_job.progress == 100
    
    def test_update_task_status_to_failed(self, mock_db, mock_job):
        """Test updating task status to failed with error message."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        result = BackgroundTaskService.update_task_status(
            db=mock_db,
            job_id="test-job-123",
            status=TaskStatus.FAILED,
            error_message="Connection timeout"
        )
        
        assert mock_job.status == TaskStatus.FAILED.value
        assert mock_job.error_message == "Connection timeout"
        assert mock_job.completed_at is not None
    
    def test_update_task_not_found(self, mock_db):
        """Test update when task is not found."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = BackgroundTaskService.update_task_status(
            db=mock_db,
            job_id="nonexistent",
            status=TaskStatus.COMPLETED
        )
        
        assert result is None
    
    def test_get_task_by_id(self, mock_db, mock_job):
        """Test retrieving a task by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        result = BackgroundTaskService.get_task(mock_db, "test-job-123")
        
        assert result == mock_job
    
    def test_get_task_with_user_filter(self, mock_db, mock_job):
        """Test retrieving a task with user ownership check."""
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_job
        
        result = BackgroundTaskService.get_task(mock_db, "test-job-123", user_id=1)
        
        assert result == mock_job
        # Verify user_id filter was applied
        mock_query.filter.assert_called()
    
    def test_get_user_tasks(self, mock_db, mock_job):
        """Test listing tasks for a user."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_job]
        
        result = BackgroundTaskService.get_user_tasks(mock_db, user_id=1)
        
        assert len(result) == 1
        assert result[0] == mock_job
    
    def test_get_user_tasks_with_filters(self, mock_db, mock_job):
        """Test listing tasks with type and status filters."""
        mock_query = Mock()
        mock_db.query.return_value.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_job]
        
        result = BackgroundTaskService.get_user_tasks(
            mock_db,
            user_id=1,
            task_type=TaskType.EXPORT_PDF,
            status=TaskStatus.COMPLETED
        )
        
        assert len(result) == 1
    
    def test_get_pending_tasks_count(self, mock_db):
        """Test counting pending tasks."""
        mock_db.query.return_value.filter.return_value.count.return_value = 3
        
        result = BackgroundTaskService.get_pending_tasks_count(mock_db)
        
        assert result == 3
    
    def test_execute_task_success(self):
        """Test successful task execution with status tracking."""
        def mock_task_fn(arg1, arg2):
            return {"result": "success", "filepath": "/path.pdf"}
        
        with patch('api.services.background_task_service.SessionLocal') as MockSession:
            mock_db = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_db)
            MockSession.return_value.__exit__ = Mock(return_value=False)
            
            with patch.object(BackgroundTaskService, 'update_task_status') as mock_update:
                BackgroundTaskService.execute_task(
                    "job-123",
                    mock_task_fn,
                    "arg1_value",
                    "arg2_value"
                )
                
                # Verify status was updated to PROCESSING first, then COMPLETED
                calls = mock_update.call_args_list
                assert len(calls) == 2
                # First call args: (db, job_id, status)
                assert calls[0][0][2] == TaskStatus.PROCESSING
                # Second call should be COMPLETED
                assert calls[1][0][2] == TaskStatus.COMPLETED
    
    def test_execute_task_failure(self):
        """Test task execution with failure handling."""
        def mock_failing_task():
            raise ValueError("Something went wrong")
        
        with patch('api.services.background_task_service.SessionLocal') as MockSession:
            mock_db = MagicMock()
            MockSession.return_value.__enter__ = Mock(return_value=mock_db)
            MockSession.return_value.__exit__ = Mock(return_value=False)
            
            with patch.object(BackgroundTaskService, 'update_task_status') as mock_update:
                BackgroundTaskService.execute_task(
                    "job-123",
                    mock_failing_task
                )
                
                # Verify status was updated to PROCESSING first, then FAILED
                calls = mock_update.call_args_list
                assert len(calls) == 2
                # First call should be PROCESSING
                assert calls[0][0][2] == TaskStatus.PROCESSING
                # Second call should be FAILED
                assert calls[1][0][2] == TaskStatus.FAILED


class TestTaskStatus:
    """Tests for TaskStatus enum."""
    
    def test_status_values(self):
        """Test all status values are correct."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestTaskType:
    """Tests for TaskType enum."""
    
    def test_export_types(self):
        """Test export task types."""
        assert TaskType.EXPORT_PDF.value == "export_pdf"
        assert TaskType.EXPORT_CSV.value == "export_csv"
        assert TaskType.EXPORT_JSON.value == "export_json"
        assert TaskType.EXPORT_XML.value == "export_xml"
        assert TaskType.EXPORT_HTML.value == "export_html"
    
    def test_other_types(self):
        """Test other task types."""
        assert TaskType.SEND_EMAIL.value == "send_email"
        assert TaskType.DATA_ANALYSIS.value == "data_analysis"
        assert TaskType.REPORT_GENERATION.value == "report_generation"


class TestBackgroundTaskDecorator:
    """Tests for the background_task decorator."""
    
    def test_decorator_creates_task(self):
        """Test that decorator properly creates and schedules tasks."""
        @background_task(TaskType.EXPORT_PDF)
        def my_export_function(db, user):
            return {"filepath": "/path.pdf"}
        
        mock_background_tasks = Mock()
        mock_db = Mock()
        
        with patch.object(BackgroundTaskService, 'create_task') as mock_create:
            mock_job = Mock()
            mock_job.job_id = "decorated-job-123"
            mock_create.return_value = mock_job
            
            job_id = my_export_function(
                mock_background_tasks,
                mock_db,
                user_id=1
            )
            
            assert job_id == "decorated-job-123"
            mock_create.assert_called_once()
            mock_background_tasks.add_task.assert_called_once()
