"""
Cost Trend Analyzer

Tracks historical costs and computes baseline averages for anomaly detection.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """Single cost data point."""
    service_name: str
    cost_amount: float
    timestamp: datetime


class CostTrendAnalyzer:
    """Analyzes cost trends and computes baselines.
    
    Singleton pattern for tracking historical costs across the application.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize analyzer."""
        if self._initialized:
            return
        
        self._initialized = True
        self.records: List[CostRecord] = []
    
    def record_cost(self, service_name: str, cost_amount: float, 
                    timestamp: Optional[datetime] = None) -> None:
        """Record a cost data point.
        
        Args:
            service_name: Name of the service (e.g., 'ml_endpoints', 'database')
            cost_amount: Cost in USD
            timestamp: When the cost was incurred (defaults to now)
            
        Raises:
            ValueError: If cost_amount is negative
        """
        if cost_amount < 0:
            raise ValueError(f"cost_amount must be >= 0, got {cost_amount}")
        
        if not service_name or not isinstance(service_name, str):
            raise ValueError(f"service_name must be non-empty string, got {service_name}")
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        record = CostRecord(
            service_name=service_name,
            cost_amount=cost_amount,
            timestamp=timestamp
        )
        self.records.append(record)
        logger.debug(f"Recorded cost for {service_name}: ${cost_amount:.2f}")
    
    def get_baseline(self, service_name: str, days: int = 7) -> Optional[float]:
        """Compute rolling average cost for a service.
        
        Args:
            service_name: Service to analyze
            days: Number of days to include (default 7)
            
        Returns:
            Average cost if data available, None if insufficient history
        """
        if days < 1:
            raise ValueError(f"days must be >= 1, got {days}")
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        relevant = [
            r for r in self.records
            if r.service_name == service_name and r.timestamp >= cutoff
        ]
        
        if not relevant:
            return None
        
        total = sum(r.cost_amount for r in relevant)
        return total / len(relevant)
    
    def get_rate_of_change(self, service_name: str, 
                          window_hours: int = 1) -> Optional[float]:
        """Calculate cost velocity (change rate).
        
        Compares most recent window against previous window.
        Returns: (current_avg - previous_avg) / previous_avg * 100
        
        Args:
            service_name: Service to analyze
            window_hours: Size of each comparison window (default 1 hour)
            
        Returns:
            Percentage change rate, or None if insufficient data
        """
        if window_hours < 1:
            raise ValueError(f"window_hours must be >= 1, got {window_hours}")
        
        now = datetime.utcnow()
        current_start = now - timedelta(hours=window_hours)
        previous_start = now - timedelta(hours=2 * window_hours)
        
        current_records = [
            r for r in self.records
            if r.service_name == service_name and current_start <= r.timestamp <= now
        ]
        previous_records = [
            r for r in self.records
            if r.service_name == service_name and previous_start <= r.timestamp < current_start
        ]
        
        if not current_records or not previous_records:
            return None
        
        current_avg = sum(r.cost_amount for r in current_records) / len(current_records)
        previous_avg = sum(r.cost_amount for r in previous_records) / len(previous_records)
        
        if previous_avg == 0:
            return None
        
        return ((current_avg - previous_avg) / previous_avg) * 100
    
    def get_records(self, service_name: Optional[str] = None) -> List[CostRecord]:
        """Get all cost records, optionally filtered by service."""
        if service_name is None:
            return list(self.records)
        return [r for r in self.records if r.service_name == service_name]
    
    def clear(self) -> None:
        """Clear all records (useful for testing)."""
        self.records.clear()


__all__ = ["CostTrendAnalyzer", "CostRecord"]
