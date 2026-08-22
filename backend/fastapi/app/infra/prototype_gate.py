"""Prototype gate for high-risk architecture changes.

Provides a deterministic, testable decision function that evaluates a proposed
change and returns a pass/fail decision along with reasons and suggested actions.
This is intended as a lightweight automation to flag high-risk PRs and enforce
additional review/guardrails.
"""
from typing import Dict, Any, List


class PrototypeGate:
    """Evaluate proposed changes and decide whether to block or allow a prototype.

    The input is a dict describing the change; the output contains `pass` boolean,
    `score` (0-100) and `reasons` explaining the decision.
    """

    def __init__(self, high_risk_threshold: float = 75.0):
        self.high_risk_threshold = float(high_risk_threshold)

    def evaluate(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the change.

        Expected keys in `change` (all optional but recommended):
          - `normalized_complexity` (0-100)
          - `introduces_infra` (bool)
          - `public_api_change` (bool)
          - `tests_added` (bool)
          - `ci_checks_passing` (bool)
          - `estimated_risk` ("low"|"medium"|"high")
          - `components` (list of strings)

        Returns dict with keys: `pass` (bool), `score` (float), `reasons` (list), `actions` (list).
        """
        reasons: List[str] = []
        actions: List[str] = []

        score = float(change.get("normalized_complexity", 0.0))

        introduces_infra = bool(change.get("introduces_infra", False))
        public_api_change = bool(change.get("public_api_change", False))
        tests_added = bool(change.get("tests_added", False))
        ci_checks_passing = bool(change.get("ci_checks_passing", False))
        estimated_risk = change.get("estimated_risk", "unknown")

        # Basic signals
        if score >= self.high_risk_threshold:
            reasons.append(f"Complexity score {score} >= high-risk threshold {self.high_risk_threshold}")

        if introduces_infra:
            reasons.append("Change introduces infrastructure modifications")

        if public_api_change:
            reasons.append("Public API changes detected")

        if not tests_added:
            reasons.append("No tests added for the change")
            actions.append("Add unit/integration tests covering the change")

        if not ci_checks_passing:
            reasons.append("CI checks are not passing")
            actions.append("Ensure CI passes before merging")

        if estimated_risk == "high" and "Complexity" not in " ".join(reasons):
            reasons.append("Author-estimated risk: high")

        # Heuristics to decide pass/fail
        block = False

        # Block when complexity high and lacking tests or CI
        if score >= self.high_risk_threshold and (not tests_added or not ci_checks_passing):
            block = True

        # Block infra changes unless tests and CI pass and complexity < threshold
        if introduces_infra and (not tests_added or not ci_checks_passing or score >= self.high_risk_threshold):
            block = True

        # Block public api changes if no tests or no CI
        if public_api_change and (not tests_added or not ci_checks_passing):
            block = True

        # Recommendations
        if block:
            actions.append("Request architectural review before merging")
            actions.append("Consider feature flagging and staged rollout")
        else:
            actions.append("Allowed: follow standard PR review and merge")

        decision = {
            "pass": not block,
            "score": score,
            "reasons": reasons,
            "actions": actions,
        }

        return decision


__all__ = ["PrototypeGate"]
