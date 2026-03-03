import asyncio

import pytest

from app.ml import scheduler_service


class FakePatternService:
    def detect_temporal_patterns(self, username, *args, **kwargs):
        return {"patterns": [{"id": 1, "desc": "fake"}]}


class FakeAnalyticsService:
    def __init__(self):
        self.pattern_service = FakePatternService()

    def get_correlation_matrix(self, username):
        return {"significant_correlations": []}

    def get_emotional_forecast(self, username, days=7):
        return {"predictions": []}

    def get_personalized_recommendations(self, username):
        return {"recommendations": []}


@pytest.mark.asyncio
async def test_prewarm_and_validate_success(monkeypatch):
    # Replace AnalyticsService with a fake that returns quick, deterministic results
    monkeypatch.setattr(scheduler_service, "AnalyticsService", FakeAnalyticsService)

    scheduler = scheduler_service.AnalyticsScheduler()

    summary = await scheduler._prewarm_and_validate(sample_usernames=["user_a", "user_b"], timeout_seconds=5)

    assert isinstance(summary, dict)
    assert summary.get("total") == 2
    assert summary.get("failures") == 0
    assert all(r.get("status") == "success" for r in summary.get("results", []))


def test_prewarm_timeout(monkeypatch):
    # Create a fake that delays beyond timeout
    class SlowAnalyticsService(FakeAnalyticsService):
        async def get_emotional_forecast(self, username, days=7):
            await asyncio.sleep(2)
            return {"predictions": []}

    monkeypatch.setattr(scheduler_service, "AnalyticsService", SlowAnalyticsService)

    scheduler = scheduler_service.AnalyticsScheduler()

    # run with a very short timeout to trigger timeout behavior
    result = asyncio.run(scheduler._prewarm_and_validate(sample_usernames=["slow_user"], timeout_seconds=0))
    assert result.get("status") in ("timeout", "error")
