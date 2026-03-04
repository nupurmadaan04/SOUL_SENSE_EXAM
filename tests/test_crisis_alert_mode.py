"""
Test Crisis Alert Mode (Issue #1332)

Tests the crisis detection service to ensure it correctly identifies
extreme distress patterns and creates appropriate crisis alerts.
"""

import pytest
import logging
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, MagicMock

from app.models import Response, JournalEntry, CrisisAlert, User, Base
from app.services.crisis_detection_service import CrisisDetectionService
from app.db import engine, get_session, safe_db_context

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCrisisDetectionService:
    """Test suite for crisis detection functionality"""
    
    @pytest.fixture(scope="function", autouse=True)
    def setup_teardown(self):
        """Create and clean up test database"""
        # Create tables
        Base.metadata.create_all(engine)
        yield
        # Cleanup
        Base.metadata.drop_all(engine)
    
    def test_consecutive_negatives_detection(self):
        """Test detection of consecutive negative responses"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="test_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create 3 consecutive negative responses
            for i in range(3):
                response = Response(
                    user_id=user.id,
                    username=user.username,
                    question_id=1 + i,
                    response_value=2,  # Low score (negative)
                    timestamp=(datetime.now(UTC) - timedelta(hours=i)).isoformat()
                )
                session.add(response)
            
            session.commit()
        
        # Test detection
        is_crisis, alert = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        
        assert is_crisis, "Should detect crisis with 3 consecutive low responses"
        assert alert is not None, "Should create crisis alert"
        assert alert.consecutive_negative_count == 3, f"Expected 3 consecutive negatives, got {alert.consecutive_negative_count}"
    
    def test_negative_sentiment_detection(self):
        """Test detection of negative sentiment in journal entries"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="test_journal_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create entries with negative sentiment
            for i in range(3):
                entry = JournalEntry(
                    user_id=user.id,
                    username=user.username,
                    content=f"Feeling terrible, everything is falling apart {i}",
                    sentiment_score=-0.8,
                    timestamp=(datetime.now(UTC) - timedelta(days=i)).isoformat(),
                    is_deleted=False
                )
                session.add(entry)
            
            session.commit()
        
        # Test detection
        is_crisis, alert = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        
        assert is_crisis, "Should detect crisis with negative sentiment entries"
        assert alert is not None, "Should create crisis alert"
        assert alert.average_negative_intensity < -0.5, "Should detect low sentiment score"
    
    def test_no_crisis_with_positive_entries(self):
        """Test that positive entries don't trigger crisis alert"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="positive_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create positive responses
            for i in range(5):
                response = Response(
                    user_id=user.id,
                    username=user.username,
                    question_id=1 + i,
                    response_value=8,  # High score (positive)
                    timestamp=(datetime.now(UTC) - timedelta(hours=i)).isoformat()
                )
                session.add(response)
            
            session.commit()
        
        # Test detection
        is_crisis, alert = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        
        assert not is_crisis, "Should not detect crisis with positive entries"
        assert alert is None, "Should not create alert for positive patterns"
    
    def test_alert_cooldown(self):
        """Test that alert cooldown prevents repeated alerts"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="cooldown_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Create negative pattern
            for i in range(3):
                response = Response(
                    user_id=user.id,
                    username=user.username,
                    question_id=1 + i,
                    response_value=2,
                    timestamp=(datetime.now(UTC) - timedelta(hours=i)).isoformat()
                )
                session.add(response)
            
            session.commit()
        
        # First detection - should create alert
        is_crisis1, alert1 = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        assert is_crisis1, "First detection should trigger crisis alert"
        
        # Update alert to simulate recent notification
        with safe_db_context() as session:
            alert = session.query(CrisisAlert).filter(CrisisAlert.user_id == user.id).first()
            assert alert is not None, "Alert should be created"
            alert.last_alerted_at = datetime.now(UTC)
            session.commit()
        
        # Second detection - should be in cooldown
        is_crisis2, alert2 = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        assert not is_crisis2, "Second detection should be blocked by cooldown"
    
    def test_alert_acknowledgment(self):
        """Test acknowledging an alert"""
        with safe_db_context() as session:
            # Create test user and alert
            user = User(username="ack_user", password_hash="hash")
            alert = CrisisAlert(
                user_id=user.id,
                username=user.username,
                consecutive_negative_count=3,
                total_negative_entries=3,
                average_negative_intensity=-0.6,
                is_active=True
            )
            session.add(user)
            session.add(alert)
            session.commit()
            
            alert_id = alert.id
        
        # Acknowledge alert
        success = CrisisDetectionService.acknowledge_alert(alert_id)
        assert success, "Acknowledgment should succeed"
        
        # Verify alert is marked acknowledged
        with safe_db_context() as session:
            alert = session.query(CrisisAlert).filter(CrisisAlert.id == alert_id).first()
            assert alert.is_acknowledged, "Alert should be acknowledged"
            assert alert.intervention_modal_shown, "Modal shown flag should be set"
    
    def test_severity_calculation(self):
        """Test severity level calculation"""
        # Test critical severity
        severity = CrisisDetectionService._calculate_severity(
            consecutive_count=5,
            avg_sentiment=-0.9,
            negative_entry_count=4
        )
        assert severity == "critical", f"Expected 'critical', got {severity}"
        
        # Test high severity
        severity = CrisisDetectionService._calculate_severity(
            consecutive_count=3,
            avg_sentiment=-0.6,
            negative_entry_count=2
        )
        assert severity == "high", f"Expected 'high', got {severity}"
        
        # Test medium severity
        severity = CrisisDetectionService._calculate_severity(
            consecutive_count=2,
            avg_sentiment=-0.5,
            negative_entry_count=2
        )
        assert severity == "medium", f"Expected 'medium', got {severity}"
    
    def test_support_resources_available(self):
        """Test that support resources are properly configured"""
        resources = CrisisDetectionService.get_support_resources()
        
        assert resources is not None, "Resources should be available"
        assert "crisis_hotlines" in resources, "Should include crisis hotlines"
        assert "guidance" in resources, "Should include guidance"
        assert "resources" in resources, "Should include resources"
        
        assert len(resources["crisis_hotlines"]) > 0, "Should have at least one hotline"
        assert len(resources["guidance"]) > 0, "Should have guidance tips"
        
        # Verify hotline structure
        hotline = resources["crisis_hotlines"][0]
        assert "name" in hotline, "Hotline should have name"
        assert "number" in hotline, "Hotline should have number"
        assert "description" in hotline, "Hotline should have description"


class TestCrisisAlertIntegration:
    """Integration tests for crisis alert system"""
    
    @pytest.fixture(scope="function", autouse=True)
    def setup_teardown(self):
        """Create and clean up test database"""
        Base.metadata.create_all(engine)
        yield
        Base.metadata.drop_all(engine)
    
    def test_crisis_alert_in_exam_flow(self):
        """Test that crisis detection integrates with exam completion"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="exam_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Simulate exam with negative responses
            for i in range(4):
                response = Response(
                    user_id=user.id,
                    username=user.username,
                    question_id=1 + i,
                    response_value=2,
                    timestamp=(datetime.now(UTC) - timedelta(hours=i)).isoformat()
                )
                session.add(response)
            
            session.commit()
        
        # Test crisis detection
        is_crisis, alert = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        
        assert is_crisis, "Exam with all low scores should trigger crisis"
        assert alert.severity in ["high", "critical"], "Should be high severity"
    
    def test_crisis_alert_in_journal_flow(self):
        """Test that crisis detection integrates with journal submission"""
        with safe_db_context() as session:
            # Create test user
            user = User(username="journal_user", password_hash="hash")
            session.add(user)
            session.commit()
            
            # Simulate multiple journal entries with negative sentiment
            for i in range(3):
                entry = JournalEntry(
                    user_id=user.id,
                    username=user.username,
                    content=f"Struggling with depression and anxiety {i}",
                    sentiment_score=-0.75,
                    timestamp=(datetime.now(UTC) - timedelta(days=i)).isoformat(),
                    mood_score=2,
                    energy_level=1,
                    stress_level=9,
                    is_deleted=False
                )
                session.add(entry)
            
            session.commit()
        
        # Test crisis detection
        is_crisis, alert = CrisisDetectionService.check_crisis_pattern(user.id, user.username)
        
        assert is_crisis, "Multiple negative journal entries should trigger crisis"
        assert alert.total_negative_entries >= 3, "Should count negative entries"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
