"""
Unit Tests for Cost Anomaly Detection System

Tests cover:
- CostTrendAnalyzer: Recording and baseline computation
- CostAnomalyDetector: Anomaly detection across 3 tiers
- CostAnomalyAlertManager: Alert lifecycle management
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from app.infra.cost_trend_analyzer import CostTrendAnalyzer, CostRecord
from app.infra.cost_anomaly_detector import (
    CostAnomalyDetector,
    CostAnomalyAlert,
    AlertLevel
)
from app.infra.cost_alert_manager import CostAnomalyAlertManager


class TestCostTrendAnalyzer:
    """Tests for CostTrendAnalyzer."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear singleton before each test."""
        analyzer = CostTrendAnalyzer()
        analyzer.clear()
        yield
        analyzer.clear()
    
    def test_record_cost_stores_data(self):
        """Test that record_cost stores data correctly."""
        analyzer = CostTrendAnalyzer()
        analyzer.record_cost("api_compute", 25.50)
        
        assert len(analyzer.records) == 1
        assert analyzer.records[0].service_name == "api_compute"
        assert analyzer.records[0].cost_amount == 25.50
    
    def test_record_cost_multiple_services(self):
        """Test recording costs for multiple services."""
        analyzer = CostTrendAnalyzer()
        analyzer.record_cost("api_compute", 10.0)
        analyzer.record_cost("ml_endpoints", 20.0)
        analyzer.record_cost("database", 5.0)
        
        assert len(analyzer.records) == 3
        api_records = analyzer.get_records("api_compute")
        assert len(api_records) == 1
        assert api_records[0].cost_amount == 10.0
    
    def test_record_cost_negative_raises_error(self):
        """Test that negative cost raises ValueError."""
        analyzer = CostTrendAnalyzer()
        with pytest.raises(ValueError, match="cost_amount must be >= 0"):
            analyzer.record_cost("api_compute", -10.0)
    
    def test_record_cost_invalid_service_name(self):
        """Test that invalid service name raises error."""
        analyzer = CostTrendAnalyzer()
        with pytest.raises(ValueError, match="service_name must be non-empty"):
            analyzer.record_cost("", 10.0)
    
    def test_get_baseline_computes_average(self):
        """Test baseline calculation with sufficient data."""
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Record 3 costs over past 7 days
        analyzer.record_cost("api_compute", 10.0, now - timedelta(days=6))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 30.0, now)
        
        baseline = analyzer.get_baseline("api_compute", days=7)
        assert baseline == 20.0  # (10+20+30)/3
    
    def test_get_baseline_insufficient_history(self):
        """Test baseline with no data returns None."""
        analyzer = CostTrendAnalyzer()
        baseline = analyzer.get_baseline("api_compute", days=7)
        assert baseline is None
    
    def test_get_baseline_respects_time_window(self):
        """Test that baseline only includes records within time window."""
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Record outside and inside window
        analyzer.record_cost("api_compute", 100.0, now - timedelta(days=10))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 30.0, now)
        
        baseline = analyzer.get_baseline("api_compute", days=7)
        assert baseline == 25.0  # (20+30)/2, excludes the 100.0
    
    def test_get_rate_of_change_calculates_velocity(self):
        """Test rate of change calculation."""
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Previous window: 10, 10 (avg=10)
        # Current window: 15, 15 (avg=15)
        # Rate: (15-10)/10 * 100 = 50%
        analyzer.record_cost("api_compute", 10.0, now - timedelta(hours=2.5))
        analyzer.record_cost("api_compute", 10.0, now - timedelta(hours=1.5))
        analyzer.record_cost("api_compute", 15.0, now - timedelta(hours=0.5))
        analyzer.record_cost("api_compute", 15.0, now)
        
        roc = analyzer.get_rate_of_change("api_compute", window_hours=1)
        assert roc == 50.0
    
    def test_get_rate_of_change_insufficient_data(self):
        """Test rate of change with insufficient data returns None."""
        analyzer = CostTrendAnalyzer()
        analyzer.record_cost("api_compute", 10.0)
        
        roc = analyzer.get_rate_of_change("api_compute", window_hours=1)
        assert roc is None
    
    def test_singleton_pattern(self):
        """Test that CostTrendAnalyzer is a singleton."""
        analyzer1 = CostTrendAnalyzer()
        analyzer2 = CostTrendAnalyzer()
        
        assert analyzer1 is analyzer2


class TestCostAnomalyDetector:
    """Tests for CostAnomalyDetector."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup detector and clear data before each test."""
        analyzer = CostTrendAnalyzer()
        analyzer.clear()
        yield
        analyzer.clear()
    
    def _get_config(self) -> dict:
        """Get default test configuration."""
        return {
            "enabled": True,
            "baseline_days": 7,
            "services": {
                "api_compute": {
                    "daily_budget_usd": 50.0,
                    "spike_threshold_percent": 20,
                    "rate_of_change_multiplier": 2.0
                },
                "ml_endpoints": {
                    "daily_budget_usd": 100.0,
                    "spike_threshold_percent": 25,
                    "rate_of_change_multiplier": 2.0
                }
            }
        }
    
    def test_detect_no_anomaly_normal_range(self):
        """Test no alerts when cost is within normal range."""
        detector = CostAnomalyDetector()
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Establish baseline: 20, 20, 20 (avg=20)
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=2))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=1))
        
        config = self._get_config()
        alerts = detector.detect_anomaly("api_compute", 21.0, config)
        
        assert len(alerts) == 0
    
    def test_detect_spike_20_percent_warning(self):
        """Test WARNING alert for 20% spike above baseline."""
        detector = CostAnomalyDetector()
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Baseline: 20
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=2))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=1))
        
        # Current: 24 (20% above baseline)
        config = self._get_config()
        alerts = detector.detect_anomaly("api_compute", 24.0, config)
        
        assert len(alerts) == 1
        assert alerts[0].alert_level == AlertLevel.WARNING
        assert abs(alerts[0].deviation_percent - 20.0) < 0.01
    
    def test_detect_spike_50_percent_critical(self):
        """Test CRITICAL alert for 50% spike above baseline."""
        detector = CostAnomalyDetector()
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Baseline: 20
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=2))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=1))
        
        # Current: 30 (50% above baseline)
        config = self._get_config()
        alerts = detector.detect_anomaly("api_compute", 30.0, config)
        
        assert len(alerts) == 1
        assert alerts[0].alert_level == AlertLevel.CRITICAL
        assert abs(alerts[0].deviation_percent - 50.0) < 0.01
    
    def test_detect_absolute_limit_breach(self):
        """Test CRITICAL alert when exceeding daily budget."""
        detector = CostAnomalyDetector()
        config = self._get_config()
        
        # Daily budget is $50
        alerts = detector.detect_anomaly("api_compute", 75.0, config)
        
        assert len(alerts) >= 1
        critical_alert = [a for a in alerts if a.alert_level == AlertLevel.CRITICAL]
        assert len(critical_alert) == 1
        assert "budget" in critical_alert[0].reason.lower()
    
    def test_detect_multiple_anomalies_same_service(self):
        """Test that multiple tiers can trigger for same service."""
        detector = CostAnomalyDetector()
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Establish baseline
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=2))
        analyzer.record_cost("api_compute", 20.0, now - timedelta(days=1))
        
        # Current cost is 60 (exceeds both baseline spike AND daily budget)
        config = self._get_config()
        alerts = detector.detect_anomaly("api_compute", 60.0, config)
        
        # Should have both spike and budget alerts
        assert len(alerts) >= 2
    
    def test_detect_disabled_in_config(self):
        """Test no alerts when disabled in config."""
        detector = CostAnomalyDetector()
        config = self._get_config()
        config["enabled"] = False
        
        alerts = detector.detect_anomaly("api_compute", 100.0, config)
        assert len(alerts) == 0
    
    def test_detect_unconfigured_service(self):
        """Test no alerts for service not in config."""
        detector = CostAnomalyDetector()
        config = self._get_config()
        
        alerts = detector.detect_anomaly("unknown_service", 100.0, config)
        assert len(alerts) == 0
    
    def test_zero_baseline_edge_case(self):
        """Test handling when baseline is 0."""
        detector = CostAnomalyDetector()
        analyzer = CostTrendAnalyzer()
        now = datetime.utcnow()
        
        # Baseline: 0
        analyzer.record_cost("api_compute", 0.0, now - timedelta(days=3))
        analyzer.record_cost("api_compute", 0.0, now - timedelta(days=2))
        analyzer.record_cost("api_compute", 0.0, now - timedelta(days=1))
        
        config = self._get_config()
        alerts = detector.detect_anomaly("api_compute", 10.0, config)
        
        # Should handle gracefully
        assert isinstance(alerts, list)


class TestCostAnomalyAlertManager:
    """Tests for CostAnomalyAlertManager."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear singleton before each test."""
        manager = CostAnomalyAlertManager()
        manager.clear()
        yield
        manager.clear()
    
    def test_singleton_pattern(self):
        """Test that CostAnomalyAlertManager is a singleton."""
        manager1 = CostAnomalyAlertManager()
        manager2 = CostAnomalyAlertManager()
        assert manager1 is manager2
    
    def test_add_alert_appends_to_list(self):
        """Test adding a single alert."""
        manager = CostAnomalyAlertManager()
        alert = CostAnomalyAlert(
            service_name="api_compute",
            current_cost=30.0,
            baseline_cost=20.0,
            alert_level=AlertLevel.WARNING,
            reason="Test spike",
            timestamp=datetime.utcnow(),
            deviation_percent=50.0
        )
        
        manager.add_alert(alert)
        assert len(manager.alerts) == 1
        assert manager.alerts[0] == alert
    
    def test_add_alerts_multiple(self):
        """Test adding multiple alerts at once."""
        manager = CostAnomalyAlertManager()
        now = datetime.utcnow()
        
        alerts = [
            CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "Test", now),
            CostAnomalyAlert("ml_endpoints", 120.0, 100.0, AlertLevel.CRITICAL, "Test", now)
        ]
        
        manager.add_alerts(alerts)
        assert len(manager.alerts) == 2
    
    def test_get_alerts_filters_by_service(self):
        """Test filtering alerts by service name."""
        manager = CostAnomalyAlertManager()
        now = datetime.utcnow()
        
        manager.add_alert(CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "Test", now))
        manager.add_alert(CostAnomalyAlert("ml_endpoints", 120.0, 100.0, AlertLevel.WARNING, "Test", now))
        
        api_alerts = manager.get_alerts(service_name="api_compute")
        assert len(api_alerts) == 1
        assert api_alerts[0].service_name == "api_compute"
    
    def test_get_alerts_filters_by_level(self):
        """Test filtering alerts by severity level."""
        manager = CostAnomalyAlertManager()
        now = datetime.utcnow()
        
        manager.add_alert(CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "Test", now))
        manager.add_alert(CostAnomalyAlert("ml_endpoints", 120.0, 100.0, AlertLevel.CRITICAL, "Test", now))
        
        critical = manager.get_alerts(alert_level=AlertLevel.CRITICAL)
        assert len(critical) == 1
        assert critical[0].alert_level == AlertLevel.CRITICAL
    
    def test_get_alerts_combined_filters(self):
        """Test filtering with both service and level."""
        manager = CostAnomalyAlertManager()
        now = datetime.utcnow()
        
        manager.add_alert(CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "Test", now))
        manager.add_alert(CostAnomalyAlert("api_compute", 60.0, 20.0, AlertLevel.CRITICAL, "Test", now))
        manager.add_alert(CostAnomalyAlert("ml_endpoints", 120.0, 100.0, AlertLevel.CRITICAL, "Test", now))
        
        api_critical = manager.get_alerts(service_name="api_compute", alert_level=AlertLevel.CRITICAL)
        assert len(api_critical) == 1
        assert api_critical[0].service_name == "api_compute"
        assert api_critical[0].alert_level == AlertLevel.CRITICAL
    
    def test_clear_alerts_before(self):
        """Test clearing old alerts by timestamp."""
        manager = CostAnomalyAlertManager()
        old_time = datetime.utcnow() - timedelta(hours=2)
        new_time = datetime.utcnow()
        
        manager.add_alert(CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "Old", old_time))
        manager.add_alert(CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "New", new_time))
        
        cleared = manager.clear_alerts_before(datetime.utcnow() - timedelta(hours=1))
        
        assert cleared == 1
        assert len(manager.alerts) == 1
        assert manager.alerts[0].reason == "New"
    
    def test_get_summary(self):
        """Test summary statistics."""
        manager = CostAnomalyAlertManager()
        now = datetime.utcnow()
        
        manager.add_alert(CostAnomalyAlert("api_compute", 30.0, 20.0, AlertLevel.WARNING, "Test", now))
        manager.add_alert(CostAnomalyAlert("api_compute", 60.0, 20.0, AlertLevel.CRITICAL, "Test", now))
        manager.add_alert(CostAnomalyAlert("ml_endpoints", 120.0, 100.0, AlertLevel.CRITICAL, "Test", now))
        
        summary = manager.get_summary()
        
        assert summary["total"] == 3
        assert summary["critical"] == 2
        assert summary["warning"] == 1
        assert set(summary["services"]) == {"api_compute", "ml_endpoints"}


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear singletons before each test."""
        analyzer = CostTrendAnalyzer()
        analyzer.clear()
        manager = CostAnomalyAlertManager()
        manager.clear()
        yield
        analyzer.clear()
        manager.clear()
    
    def test_end_to_end_cost_spike_detection(self):
        """Test complete workflow: record costs, detect anomalies, manage alerts."""
        analyzer = CostTrendAnalyzer()
        detector = CostAnomalyDetector(analyzer)
        manager = CostAnomalyAlertManager()
        
        config = {
            "enabled": True,
            "baseline_days": 7,
            "services": {
                "api_compute": {
                    "daily_budget_usd": 50.0,
                    "spike_threshold_percent": 20,
                    "rate_of_change_multiplier": 2.0
                }
            }
        }
        
        now = datetime.utcnow()
        
        # Step 1: Establish baseline (7 days of $20 cost)
        for i in range(7):
            analyzer.record_cost("api_compute", 20.0, now - timedelta(days=7-i))
        
        # Step 2: Simulate cost spike to $24 (20% over baseline)
        alerts = detector.detect_anomaly("api_compute", 24.0, config)
        manager.add_alerts(alerts)
        
        # Step 3: Verify alert was created
        assert len(manager.alerts) >= 1
        spike_alert = [a for a in manager.alerts if "spike" in a.reason.lower()]
        assert len(spike_alert) > 0
        
        # Step 4: Get alerts and verify filtering
        api_alerts = manager.get_alerts(service_name="api_compute")
        assert len(api_alerts) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
