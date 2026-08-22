"""Third-party vendor fallback readiness scoring.

Provides a deterministic readiness score and recommended fallback action
based on vendor health indicators to help gate high-risk architecture changes.
"""
from typing import Dict, Any


DEFAULT_WEIGHTS = {
    "availability": 0.25,         # % uptime influence
    "latency": 0.15,              # lower is better
    "error_rate": 0.2,            # lower is better
    "support_response_time": 0.1, # lower is better
    "retryability": 0.1,          # higher is better
    "sla_coverage": 0.1,          # higher is better
    "cost_impact": 0.1,           # lower is better
}


class VendorFallback:
    """Compute a readiness score and fallback recommendation.

    Input expected as a dict with keys matching DEFAULT_WEIGHTS. Values should be
    normalized in the following directions:
      - availability: percent [0-100] (higher better)
      - latency: milliseconds (lower better)
      - error_rate: percent [0-100] (lower better)
      - support_response_time: hours (lower better)
      - retryability: score 0-10 (higher better)
      - sla_coverage: percent [0-100] (higher better)
      - cost_impact: relative score 0-10 (lower better)
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def _validate(self, metrics: Dict[str, Any]):
        if not isinstance(metrics, dict):
            raise ValueError("metrics must be a dict")

    def _scale(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Normalize metrics into 0-1 where 1 is best readiness."""
        scaled: Dict[str, float] = {}

        # availability: 0-100 -> 0-1
        avail = float(metrics.get("availability", 0.0) or 0.0)
        scaled["availability"] = min(max(avail / 100.0, 0.0), 1.0)

        # latency: assume baseline target 200ms -> scale as 1 - min(latency/200,1)
        latency = float(metrics.get("latency", 1000.0))
        scaled["latency"] = 1.0 - min(latency / 200.0, 1.0)

        # error_rate: percent -> lower is better
        err = float(metrics.get("error_rate", 100.0))
        scaled["error_rate"] = 1.0 - min(err / 100.0, 1.0)

        # support_response_time: hours -> faster is better; baseline 48h
        srt = float(metrics.get("support_response_time", 168.0))
        scaled["support_response_time"] = 1.0 - min(srt / 48.0, 1.0)

        # retryability: 0-10 -> 0-1
        retry = float(metrics.get("retryability", 0.0))
        scaled["retryability"] = min(max(retry / 10.0, 0.0), 1.0)

        # sla_coverage: percent -> 0-1
        sla = float(metrics.get("sla_coverage", 0.0) or 0.0)
        scaled["sla_coverage"] = min(max(sla / 100.0, 0.0), 1.0)

        # cost_impact: 0-10 where lower is better; invert
        cost = float(metrics.get("cost_impact", 10.0))
        scaled["cost_impact"] = 1.0 - min(max(cost / 10.0, 0.0), 1.0)

        return scaled

    def readiness(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Return readiness score, breakdown and recommended action.

        Recommended actions: `use_primary`, `enable_degraded_mode`, `switch_to_backup`, `disable_feature`.
        """
        self._validate(metrics)

        scaled = self._scale(metrics)

        raw = 0.0
        for k, w in self.weights.items():
            raw += scaled.get(k, 0.0) * w

        # normalized 0-100
        normalized = round(raw / sum(self.weights.values()) * 100.0, 2)

        # Determine category and action
        if normalized >= 75.0:
            category = "Ready"
            action = "use_primary"
        elif normalized >= 50.0:
            category = "At Risk"
            action = "enable_degraded_mode"
        elif normalized >= 30.0:
            category = "High Risk"
            action = "switch_to_backup"
        else:
            category = "Unready"
            action = "disable_feature"

        breakdown = {k: round(v, 4) for k, v in scaled.items()}

        return {
            "normalized_score": normalized,
            "category": category,
            "recommended_action": action,
            "breakdown": breakdown,
        }


__all__ = ["VendorFallback"]
