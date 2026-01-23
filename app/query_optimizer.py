"""Optimized database query manager"""
from sqlalchemy.orm import sessionmaker, joinedload, selectinload
from sqlalchemy import text
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class QueryOptimizer:
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
    
    @lru_cache(maxsize=128)
    def get_user_with_profiles(self, username: str):
        """Optimized user query with eager loading"""
        with self.Session() as session:
            from app.models import User
            return session.query(User).options(
                joinedload(User.personal_profile),
                joinedload(User.medical_profile),
                joinedload(User.strengths),
                joinedload(User.emotional_patterns)
            ).filter_by(username=username).first()
    
    @lru_cache(maxsize=64)
    def get_recent_scores(self, username: str, limit: int = 5):
        """Cached recent scores query"""
        with self.Session() as session:
            from app.models import Score
            return session.query(Score)\
                .filter_by(username=username)\
                .order_by(Score.timestamp.desc())\
                .limit(limit).all()
    
    def bulk_insert_responses(self, responses_data):
        """Optimized bulk insert for responses"""
        with self.Session() as session:
            from app.models import Response
            session.bulk_insert_mappings(Response, responses_data)
            session.commit()
    
    def clear_cache(self):
        """Clear query cache"""
        self.get_user_with_profiles.cache_clear()
        self.get_recent_scores.cache_clear()

# Global instance
query_optimizer = None

def get_query_optimizer():
    global query_optimizer
    if query_optimizer is None:
        from app.db import get_engine
        query_optimizer = QueryOptimizer(get_engine())
    return query_optimizer