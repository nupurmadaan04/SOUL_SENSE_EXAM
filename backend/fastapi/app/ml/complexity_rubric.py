"""Feature complexity scoring rubric automation.

Provides a deterministic, unit-testable rubric that scores feature complexity
across multiple dimensions and returns a breakdown and normalized score.
"""
from typing import Dict, Any


DEFAULT_WEIGHTS = {
    "user_visible": 0.15,
    "infra_changes": 0.15,
    "data_required": 0.15,
    "dependencies": 0.15,
    "security_impact": 0.15,
    "rollout_complexity": 0.15,
    "backward_incompat": 0.1,
}


class ComplexityRubric:
    """Compute a complexity score for a feature.

    Input values are expected on a 0-10 scale for each dimension. The rubric
    returns a breakdown of weighted scores and a normalized 0-100 total score.
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def _validate_inputs(self, vals: Dict[str, Any]):
        for k, v in vals.items():
            if v is None:
                continue
            if not isinstance(v, (int, float)):
                raise ValueError(f"value for {k} must be numeric")
            if v < 0 or v > 10:
                raise ValueError(f"value for {k} must be between 0 and 10")

    def score(self, features: Dict[str, float], effort_hours: float = 0.0) -> Dict[str, Any]:
        """Return a score breakdown and total.

        Args:
            features: mapping of dimension -> value (0-10). Missing keys treated as 0.
            effort_hours: optional estimated effort, which contributes modestly to score.

        Returns:
            Dict with `breakdown`, `raw_score`, `normalized_score`, `category`.
        """
        if not isinstance(features, dict):
            raise ValueError("features must be a dict")

        self._validate_inputs(features)

        # Compute contribution per weighted dimension (normalize 0-10 -> 0-1)
        breakdown = {}
        raw_total = 0.0
        weight_sum = sum(self.weights.values())

        for dim, weight in self.weights.items():
            value = float(features.get(dim, 0.0) or 0.0)
            contrib = (value / 10.0) * weight
            breakdown[dim] = round(contrib, 4)
            raw_total += contrib

        # Effort contributes as a small additive factor: longer efforts slightly increase complexity
        # Scale effort into 0-1 by capping at 200 hours
        effort_factor = min(float(effort_hours) / 200.0, 1.0)
        effort_weight = 0.05
        breakdown["effort_factor"] = round(effort_factor * effort_weight, 4)
        raw_total += effort_factor * effort_weight

        # Normalize raw_total by weight_sum + effort_weight so that normalized_score in [0,1]
        norm_denom = weight_sum + effort_weight
        normalized = raw_total / norm_denom if norm_denom > 0 else 0.0
        normalized_score = round(normalized * 100.0, 2)

        # Categorize
        if normalized_score >= 80:
            category = "Critical"
        elif normalized_score >= 60:
            category = "High"
        elif normalized_score >= 35:
            category = "Medium"
        else:
            category = "Low"

        return {
            "breakdown": breakdown,
            "raw_score": round(raw_total, 4),
            "normalized_score": normalized_score,
            "category": category,
        }


__all__ = ["ComplexityRubric"]
