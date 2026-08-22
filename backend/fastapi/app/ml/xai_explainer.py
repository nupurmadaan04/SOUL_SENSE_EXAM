"""
XAI Module for SoulSense - Works with unified database connection.
"""
import json
import logging
from datetime import datetime
from sqlalchemy import text
from app.db import safe_db_context, get_engine

logger = logging.getLogger(__name__)

class SoulSenseXAI:
    """XAI (Explainable AI) module for SoulSense emotional analysis."""

    def __init__(self):
        """Initialize the XAI explainer with unified database engine."""
        # Create table for explanations if not exists (health check/init)
        with safe_db_context() as session:
            engine = get_engine()
            if 'postgresql' in str(engine.url):
                session.execute(text("""
                CREATE TABLE IF NOT EXISTS explanations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    timestamp TEXT,
                    total_score INTEGER,
                    explanation_text TEXT,
                    feature_analysis TEXT
                )
                """))
            else:
                session.execute(text("""
                CREATE TABLE IF NOT EXISTS explanations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    timestamp TEXT,
                    total_score INTEGER,
                    explanation_text TEXT,
                    feature_analysis TEXT,
                    FOREIGN KEY (user_id) REFERENCES scores (id)
                )
                """))
        
        # Question analysis mapping
        self.question_analysis = {
            1: {
                "low_score": "Difficulty recognizing emotions as they happen",
                "high_score": "Strong emotional awareness and recognition",
                "feature": "Emotional Recognition"
            },
            2: {
                "low_score": "Challenges understanding emotional causes",
                "high_score": "Good understanding of emotional triggers",
                "feature": "Emotional Understanding"
            },
            3: {
                "low_score": "Emotional control needs improvement in stress",
                "high_score": "Strong emotional regulation under pressure",
                "feature": "Emotional Regulation"
            },
            4: {
                "low_score": "Limited reflection on emotional reactions",
                "high_score": "Strong reflective practice on emotions",
                "feature": "Emotional Reflection"
            },
            5: {
                "low_score": "Less awareness of emotional impact on others",
                "high_score": "High awareness of interpersonal emotional impact",
                "feature": "Social Emotional Awareness"
            }
        }
    
    def analyze_score(self, total_score, username, age):
        """Generate XAI explanation based on total score.

        Args:
            total_score: Total assessment score.
            username: User's name.
            age: User's age.

        Returns:
            str: Formatted explanation report.
        """
        
        # Score interpretation
        if total_score <= 10:
            risk_level = "HIGH"
            interpretation = "May benefit from emotional awareness support"
            color = "🔴"
        elif total_score <= 15:
            risk_level = "MEDIUM"
            interpretation = "Moderate emotional awareness, some areas to improve"
            color = "🟡"
        else:
            risk_level = "LOW"
            interpretation = "Good emotional intelligence foundation"
            color = "🟢"
        
        # Calculate average per question
        avg_per_question = total_score / 5  # Assuming 5 questions
        
        # Generate insights
        insights = []
        if avg_per_question < 2.5:
            insights.append("Your responses suggest room for growth in emotional awareness")
        elif avg_per_question < 4:
            insights.append("You show balanced emotional intelligence")
        else:
            insights.append("You demonstrate strong emotional intelligence")
        
        # Age-based insights
        if age < 18:
            insights.append("At your age, developing emotional awareness is particularly valuable")
        elif age < 25:
            insights.append("This is a key period for emotional intelligence development")
        
        # Generate explanation report
        explanation = f"""
        📊 **SOUL SENSE ANALYSIS REPORT**
        {'='*40}
        
        👤 User: {username}
        🎂 Age: {age}
        📈 Total Score: {total_score}/25
        ⚠️ Risk Level: {color} {risk_level}
        
        📋 **KEY FINDINGS:**
        {interpretation}
        
        💡 **INSIGHTS:**
        """
        
        for i, insight in enumerate(insights, 1):
            explanation += f"\n{i}. {insight}"
        
        explanation += f"""
        
        📊 **SCORE DISTRIBUTION ANALYSIS:**
        • Each question scored 1-5 points
        • Your average: {avg_per_question:.1f}/5 per question
        • Score range: 5-25 (Higher = Better emotional awareness)
        
        🎯 **RECOMMENDATIONS:**
        1. Practice daily emotional check-ins
        2. Journal about emotional responses
        3. Seek feedback from trusted individuals
        4. Consider mindfulness exercises
        
        📅 Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        return explanation
    
    def get_detailed_analysis(self, user_id):
        """Get detailed analysis for a specific user."""
        with safe_db_context() as session:
            result = session.execute(text("""
            SELECT username, age, total_score FROM scores WHERE id = :user_id
            """), {"user_id": user_id})
            user = result.fetchone()
            
            if not user:
                return None
            
            username, age, total_score = user
            
            # Get all explanations for this user
            result = session.execute(text("""
            SELECT explanation_text FROM explanations 
            WHERE user_id = :user_id ORDER BY timestamp DESC
            """), {"user_id": user_id})
            
            explanations = result.fetchall()
        
        analysis = {
            'user_info': {
                'username': username,
                'age': age,
                'total_score': total_score
            },
            'score_breakdown': self._calculate_breakdown(total_score),
            'previous_explanations': [exp[0] for exp in explanations],
            'trend_analysis': self._analyze_trends(user_id)
        }
        
        return analysis
    
    def _calculate_breakdown(self, total_score):
        """Calculate detailed score breakdown."""
        breakdown = {
            'emotional_awareness': (total_score * 0.3),  # 30% weight
            'emotional_regulation': (total_score * 0.25),  # 25% weight
            'social_awareness': (total_score * 0.25),  # 25% weight
            'self_reflection': (total_score * 0.2)  # 20% weight
        }
        return breakdown
    
    def _analyze_trends(self, user_id):
        """Analyze score trends over time."""
        with safe_db_context() as session:
            result = session.execute(text("""
            SELECT total_score, timestamp FROM scores 
            WHERE id = :user_id ORDER BY id DESC LIMIT 5
            """), {"user_id": user_id})
            
            scores = result.fetchall()
        
        if len(scores) < 2:
            return "Insufficient data for trend analysis"
        
        # Calculate trend
        recent_score = scores[0][0]
        previous_score = scores[1][0] if len(scores) > 1 else recent_score
        
        if recent_score > previous_score:
            trend = "📈 Improving"
        elif recent_score < previous_score:
            trend = "📉 Declining"
        else:
            trend = "➡️ Stable"
        
        return f"Score trend: {trend} (from {previous_score} to {recent_score})"
    
    def save_explanation(self, user_id, total_score, explanation_text):
        """Save explanation to database."""
        with safe_db_context() as session:
            session.execute(text("""
            INSERT INTO explanations (user_id, timestamp, total_score, explanation_text)
            VALUES (:user_id, :timestamp, :total_score, :explanation_text)
            """), {
                "user_id": user_id, 
                "timestamp": datetime.now().isoformat(), 
                "total_score": total_score, 
                "explanation_text": explanation_text
            })
    
    def get_last_user_id(self):
        """Get the last inserted user ID."""
        with safe_db_context() as session:
            engine = get_engine()
            if 'postgresql' in str(engine.url):
                result = session.execute(text("SELECT lastval()"))
            else:
                result = session.execute(text("SELECT last_insert_rowid()"))
            return result.fetchone()[0]
    
    def close(self):
        """Close database engine resources."""
        # Pooled connections are returned to the pool; no explicit close needed here.
        pass

# Quick test function
def test_xai():
    """Test the XAI system."""
    xai = SoulSenseXAI()
    
    # Test with sample data
    explanation = xai.analyze_score(18, "Test User", 22)
    print(explanation)
    
    xai.close()

if __name__ == "__main__":
    test_xai()
