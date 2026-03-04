"""
Crisis Alert Mode Service (Issue #1332)

Detects extreme distress patterns by monitoring consecutive negative intensity logs.
Triggers intervention support when patterns indicate crisis-level emotional distress.
Prevents false positives through alert timing and intervention history tracking.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Tuple
from sqlalchemy import desc, and_
from app.db import safe_db_context
from app.models import CrisisAlert, Response, Score, JournalEntry, User

logger = logging.getLogger(__name__)

# Configuration
CONSECUTIVE_THRESHOLD = 3  # Number of consecutive negative responses to trigger alert
NEGATIVE_INTENSITY_THRESHOLD = -0.5  # Sentiment score below this is considered negative
LOW_RESPONSE_THRESHOLD = 3  # Response value below 4 (on 1-10 scale) is considered low
ALERT_COOLDOWN_HOURS = 24  # Prevent spamming alerts within 24 hours
LOOKBACK_DAYS = 7  # Look at last 7 days of entries for pattern detection


class CrisisDetectionService:
    """
    Service for detecting crisis patterns and managing crisis alerts.
    
    Monitors user responses and journal entries for patterns of extreme
    emotional distress, triggering intervention modals with support resources
    when crisis thresholds are met.
    """
    
    @staticmethod
    def check_crisis_pattern(user_id: int, username: str) -> Tuple[bool, Optional[CrisisAlert]]:
        """
        Check if user shows crisis-level distress pattern.
        
        Analyzes:
        1. Consecutive negative responses in recent assessments
        2. Low sentiment scores in journal entries
        3. Pattern severity and timing
        
        Args:
            user_id: User ID to check
            username: Username to check
            
        Returns:
            Tuple of (is_crisis_detected, crisis_alert_object)
        """
        try:
            with safe_db_context() as session:
                # Get recent responses (last 7 days)
                lookback_date = datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)
                
                recent_responses = session.query(Response).filter(
                    Response.user_id == user_id,
                    Response.timestamp >= lookback_date.isoformat()
                ).order_by(desc(Response.timestamp)).limit(20).all()
                
                # Check if responses show consecutive negative pattern
                consecutive_negatives = CrisisDetectionService._count_consecutive_negatives(recent_responses)
                
                # Get recent journal entries for sentiment analysis
                recent_entries = session.query(JournalEntry).filter(
                    JournalEntry.user_id == user_id,
                    JournalEntry.timestamp >= lookback_date.isoformat(),
                    JournalEntry.is_deleted == False
                ).order_by(desc(JournalEntry.timestamp)).limit(10).all()
                
                # Calculate average negative sentiment
                negative_entries, avg_sentiment = CrisisDetectionService._analyze_sentiment_pattern(recent_entries)
                
                # Determine if crisis pattern exists
                total_negative = len([r for r in recent_responses if CrisisDetectionService._is_response_negative(r)]) + negative_entries
                
                is_crisis = (
                    consecutive_negatives >= CONSECUTIVE_THRESHOLD or
                    (avg_sentiment < NEGATIVE_INTENSITY_THRESHOLD and negative_entries >= 2) or
                    (total_negative >= 5 and len(recent_responses) + len(recent_entries) >= 7)
                )
                
                if not is_crisis:
                    return False, None
                
                # Check if we should alert (cooldown period)
                existing_alert = session.query(CrisisAlert).filter(
                    CrisisAlert.user_id == user_id,
                    CrisisAlert.is_active == True
                ).first()
                
                if existing_alert:
                    # Check cooldown
                    if not CrisisDetectionService._is_cooldown_expired(existing_alert):
                        logger.info(f"Crisis detected for {username} but in cooldown period")
                        return False, None
                    # Mark existing as acknowledged if new pattern found
                    existing_alert.is_active = False
                    existing_alert.acknowledged_at = datetime.now(UTC)
                    session.commit()
                
                # Create new crisis alert
                crisis_alert = CrisisAlert(
                    user_id=user_id,
                    username=username,
                    consecutive_negative_count=consecutive_negatives,
                    total_negative_entries=total_negative,
                    average_negative_intensity=avg_sentiment,
                    severity=CrisisDetectionService._calculate_severity(
                        consecutive_negatives, avg_sentiment, negative_entries
                    ),
                    detected_at=datetime.now(UTC),
                    is_active=True,
                    intervention_modal_shown=False
                )
                
                session.add(crisis_alert)
                session.commit()
                
                logger.warning(
                    f"Crisis alert created for {username} (ID: {user_id}): "
                    f"consecutive={consecutive_negatives}, sentiment={avg_sentiment:.2f}"
                )
                
                return True, crisis_alert
                
        except Exception as e:
            logger.error(f"Error checking crisis pattern for user {user_id}: {e}")
            return False, None
    
    @staticmethod
    def acknowledge_alert(alert_id: int) -> bool:
        """Mark crisis alert as acknowledged by user."""
        try:
            with safe_db_context() as session:
                alert = session.query(CrisisAlert).filter(CrisisAlert.id == alert_id).first()
                if alert:
                    alert.is_acknowledged = True
                    alert.acknowledged_at = datetime.now(UTC)
                    alert.intervention_modal_shown = True
                    alert.support_resources_provided = True
                    session.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
    
    @staticmethod
    def get_active_alerts(user_id: int) -> List[CrisisAlert]:
        """Get all active crisis alerts for a user."""
        try:
            with safe_db_context() as session:
                alerts = session.query(CrisisAlert).filter(
                    CrisisAlert.user_id == user_id,
                    CrisisAlert.is_active == True
                ).order_by(desc(CrisisAlert.detected_at)).all()
                return alerts
        except Exception as e:
            logger.error(f"Error fetching alerts for user {user_id}: {e}")
            return []
    
    @staticmethod
    def _count_consecutive_negatives(responses: List[Response]) -> int:
        """Count consecutive negative responses from most recent."""
        count = 0
        for response in responses:
            if CrisisDetectionService._is_response_negative(response):
                count += 1
            else:
                break  # Stop counting at first positive response
        return count
    
    @staticmethod
    def _is_response_negative(response: Response) -> bool:
        """Check if a response is considered negative (low score)."""
        # Assuming response_value is 1-10 scale, anything <= 3 is negative
        return response.response_value <= LOW_RESPONSE_THRESHOLD
    
    @staticmethod
    def _analyze_sentiment_pattern(entries: List[JournalEntry]) -> Tuple[int, float]:
        """
        Analyze sentiment patterns in journal entries.
        
        Returns:
            Tuple of (count_negative_entries, average_sentiment_score)
        """
        if not entries:
            return 0, 0.0
        
        negative_count = 0
        total_sentiment = 0.0
        
        for entry in entries:
            sentiment = entry.sentiment_score or 0.0
            total_sentiment += sentiment
            if sentiment < NEGATIVE_INTENSITY_THRESHOLD:
                negative_count += 1
        
        avg_sentiment = total_sentiment / len(entries) if entries else 0.0
        return negative_count, avg_sentiment
    
    @staticmethod
    def _is_cooldown_expired(alert: CrisisAlert) -> bool:
        """Check if alert cooldown period has expired."""
        if not alert.last_alerted_at:
            return True
        
        cooldown_end = alert.last_alerted_at + timedelta(hours=ALERT_COOLDOWN_HOURS)
        return datetime.now(UTC) >= cooldown_end
    
    @staticmethod
    def _calculate_severity(
        consecutive_count: int,
        avg_sentiment: float,
        negative_entry_count: int
    ) -> str:
        """Calculate alert severity based on pattern indicators."""
        score = 0
        
        # Weight consecutive negatives heavily
        if consecutive_count >= CONSECUTIVE_THRESHOLD:
            score += consecutive_count * 2
        
        # Weight extreme sentiment
        if avg_sentiment < -0.7:
            score += 3
        elif avg_sentiment < -0.5:
            score += 2
        
        # Weight multiple negative entries
        if negative_entry_count >= 3:
            score += 2
        
        # Determine severity level
        if score >= 7:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def get_support_resources() -> dict:
        """
        Get list of crisis support resources to display in alert modal.
        
        Returns:
            Dictionary with support resources, hotlines, and guidance
        """
        return {
            "crisis_hotlines": [
                {
                    "name": "National Crisis Hotline",
                    "number": "988",
                    "description": "Free, confidential support 24/7",
                    "available_24_7": True
                },
                {
                    "name": "Crisis Text Line",
                    "number": "Text HOME to 741741",
                    "description": "Text-based crisis support",
                    "available_24_7": True
                }
            ],
            "guidance": [
                "Reach out to a trusted friend or family member",
                "Contact a mental health professional",
                "Engage in grounding techniques (5-4-3-2-1 method)",
                "Practice deep breathing exercises",
                "Consider stepping outside for fresh air"
            ],
            "resources": [
                {
                    "name": "Therapist Finder",
                    "url": "https://www.psychologytoday.com/us/basics/therapy",
                    "description": "Find licensed mental health professionals"
                },
                {
                    "name": "NAMI - National Alliance on Mental Illness",
                    "url": "https://www.nami.org/",
                    "description": "Support, education, and advocacy for mental health"
                }
            ]
        }
