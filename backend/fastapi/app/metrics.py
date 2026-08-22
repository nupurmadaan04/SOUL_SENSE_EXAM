"""
Simple metrics collection system for test environment fidelity.
Tracks test execution, environment health, and edge case handling.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class TestMetric:
    """Single test execution metric."""
    test_name: str
    category: str  # 'unit', 'integration', 'edge_case'
    passed: bool
    duration_ms: float
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    error: Optional[str] = None


@dataclass
class FidelityScore:
    """Test environment fidelity score breakdown."""
    unit_tests: float = 0.0  # 0-100
    integration_tests: float = 0.0  # 0-100
    edge_cases: float = 0.0  # 0-100
    reproducibility: float = 0.0  # 0-100
    overall: float = 0.0  # weighted 0-100

    def calculate_overall(self) -> float:
        """Calculate weighted overall score."""
        self.overall = (
            self.unit_tests * 0.25 +
            self.integration_tests * 0.25 +
            self.edge_cases * 0.25 +
            self.reproducibility * 0.25
        )
        return self.overall


class MetricsCollector:
    """Collects and aggregates test metrics."""
    
    def __init__(self):
        self.metrics: List[TestMetric] = []
        self.start_time: float = datetime.utcnow().timestamp()
    
    def record(self, test_name: str, category: str, passed: bool, 
               duration_ms: float, error: Optional[str] = None) -> None:
        """Record a test metric."""
        metric = TestMetric(
            test_name=test_name,
            category=category,
            passed=passed,
            duration_ms=duration_ms,
            error=error
        )
        self.metrics.append(metric)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        if not self.metrics:
            return {"total_tests": 0}
        
        categories = {}
        total_passed = 0
        total_duration = 0
        
        for metric in self.metrics:
            if metric.category not in categories:
                categories[metric.category] = {"pass": 0, "fail": 0, "duration": 0}
            
            if metric.passed:
                categories[metric.category]["pass"] += 1
                total_passed += 1
            else:
                categories[metric.category]["fail"] += 1
            
            categories[metric.category]["duration"] += metric.duration_ms
            total_duration += metric.duration_ms
        
        return {
            "total_tests": len(self.metrics),
            "total_passed": total_passed,
            "total_failed": len(self.metrics) - total_passed,
            "pass_rate": round(total_passed / len(self.metrics) * 100, 2) if self.metrics else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": round(total_duration / len(self.metrics), 2) if self.metrics else 0,
            "by_category": {
                cat: {
                    "total": cat_data["pass"] + cat_data["fail"],
                    "passed": cat_data["pass"],
                    "failed": cat_data["fail"],
                    "pass_rate": round(cat_data["pass"] / (cat_data["pass"] + cat_data["fail"]) * 100, 2),
                    "avg_duration_ms": round(cat_data["duration"] / (cat_data["pass"] + cat_data["fail"]), 2)
                }
                for cat, cat_data in categories.items()
            }
        }
    
    def calculate_fidelity_score(self) -> FidelityScore:
        """Calculate test environment fidelity score."""
        stats = self.get_stats()
        score = FidelityScore()
        
        by_category = stats.get("by_category", {})
        
        # Score each category based on pass rate
        score.unit_tests = by_category.get("unit", {}).get("pass_rate", 0)
        score.integration_tests = by_category.get("integration", {}).get("pass_rate", 0)
        score.edge_cases = by_category.get("edge_case", {}).get("pass_rate", 0)
        
        # Reproducibility: all tests passed on this run
        score.reproducibility = 100.0 if stats.get("total_failed", 0) == 0 else 50.0
        
        return score.calculate_overall() and score or score
    
    def export_json(self) -> str:
        """Export metrics as JSON."""
        data = {
            "stats": self.get_stats(),
            "score": asdict(self.calculate_fidelity_score()),
            "metrics": [asdict(m) for m in self.metrics]
        }
        return json.dumps(data, indent=2)
    
    def export_report(self) -> Dict[str, Any]:
        """Export metrics as dict for reporting."""
        score = self.calculate_fidelity_score()
        return {
            "overall_score": round(score.overall, 2),
            "stats": self.get_stats(),
            "score_breakdown": asdict(score),
            "passed": score.overall >= 75.0
        }


# Global instance
_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def reset_collector() -> None:
    """Reset global collector (useful for tests)."""
    global _collector
    _collector = None
