"""Lightweight cost estimation for ML endpoints.

Provides a deterministic, testable estimator to compute request cost
based on model tier, runtime duration, tokens processed and concurrency.
This is a simple pricing model intended for feasibility and CI validation.
"""
from typing import Dict


MODEL_RATES_PER_SEC = {
    "small": 0.0005,   # USD per second
    "medium": 0.0020,
    "large": 0.0100,
}

DATA_COST_PER_TOKEN = 0.000001  # USD per token (ingest + egress)


class CostEstimator:
    """Estimate cost for a single request to an ML endpoint.

    Methods are deterministic and unit-testable. Rates are configurable constants.
    """

    def estimate(self, *, model_tier: str, duration_seconds: float, tokens: int = 0, concurrency: int = 1) -> Dict[str, float]:
        """Return cost breakdown for a request.

        Args:
            model_tier: One of ('small','medium','large').
            duration_seconds: Wall-clock runtime for the request (seconds).
            tokens: Number of tokens processed (input+output).
            concurrency: Number of parallel workers used for this request (default 1).

        Returns:
            Dict with `compute_cost`, `data_cost`, `total_cost`.

        Raises:
            ValueError for invalid inputs.
        """
        if model_tier not in MODEL_RATES_PER_SEC:
            raise ValueError(f"unknown model_tier: {model_tier}")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be >= 0")
        if tokens < 0:
            raise ValueError("tokens must be >= 0")
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")

        rate = MODEL_RATES_PER_SEC[model_tier]

        compute_cost = rate * duration_seconds * concurrency
        data_cost = DATA_COST_PER_TOKEN * tokens

        total_cost = round(compute_cost + data_cost, 8)

        return {
            "model_tier": model_tier,
            "compute_cost": round(compute_cost, 8),
            "data_cost": round(data_cost, 8),
            "total_cost": total_cost,
            "duration_seconds": duration_seconds,
            "tokens": tokens,
            "concurrency": concurrency,
        }


__all__ = ["CostEstimator"]
