import asyncio

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


def test_scheduler_start_stop_and_prewarm(monkeypatch):
    # Monkeypatch AnalyticsService used by the scheduler to a deterministic fake
    monkeypatch.setattr(scheduler_service, "AnalyticsService", FakeAnalyticsService)

    sched = scheduler_service.AnalyticsScheduler()

    # Start scheduler (this will attempt to trigger prewarm)
    sched.start()
    assert sched.is_running() is True

    # Run prewarm explicitly to get the validation summary
    summary = asyncio.run(sched._prewarm_and_validate(sample_usernames=["int_user_1", "int_user_2"], timeout_seconds=5))

    assert isinstance(summary, dict)
    assert summary.get("total") == 2
    assert summary.get("failures") == 0

    # Stop scheduler cleanly
    sched.stop()
    assert sched.is_running() is False
