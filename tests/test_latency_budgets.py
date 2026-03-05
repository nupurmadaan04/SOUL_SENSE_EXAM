"""
Latency Budget Tests

Tests for latency budget annotations, alert triggering, and metrics collection.
Includes artificial delay injection for reproducible testing.

GitHub Issue: #1368
"""

import pytest
import time
from typing import Tuple
from app.latency_budget import monitor_latency, LatencyBudget
from app.latency_monitor import LatencyMonitor
from app.latency_alerts import AlertManager, AlertLevel


class TestLatencyDecorator:
    """Tests for the latency monitoring decorator."""
    
    def setup_method(self):
        """Clear metrics before each test."""
        monitor = LatencyMonitor()
        monitor.clear_metrics()
        alert_mgr = AlertManager()
        alert_mgr.clear_alerts()
    
    def test_decorator_registers_budget(self):
        """Test that decorator registers latency budget."""
        @monitor_latency("test_operation", budget_ms=500, operation_type="query")
        def dummy_func():
            return "result"
        
        dummy_func()
        
        budget = LatencyBudget.get("test_operation")
        assert budget is not None
        assert budget.operation_name == "test_operation"
        assert budget.budget_ms == 500
        assert budget.operation_type == "query"
    
    def test_decorator_measures_execution_time(self):
        """Test that decorator correctly measures execution time."""
        @monitor_latency("fast_operation", budget_ms=500)
        def fast_func():
            time.sleep(0.05)  # 50ms
            return "result"
        
        fast_func()
        
        monitor = LatencyMonitor()
        stats = monitor.get_stats("fast_operation")
        
        assert stats["count"] == 1
        assert 40 < stats["min_ms"] < 100  # Should be around 50ms
    
    def test_decorator_detects_budget_breach(self):
        """Test that decorator detects when budget is exceeded."""
        @monitor_latency("slow_operation", budget_ms=100, operation_type="command")
        def slow_func():
            time.sleep(0.2)  # 200ms
            return "result"
        
        slow_func()
        
        monitor = LatencyMonitor()
        breaches = monitor.get_breached_operations()
        
        assert len(breaches) == 1
        assert breaches[0].operation_name == "slow_operation"
        assert breaches[0].execution_time_ms > 100
    
    def test_decorator_triggers_alert_at_threshold(self):
        """Test that alert is triggered when threshold is reached."""
        @monitor_latency(
            "alert_test",
            budget_ms=1000,
            alert_threshold_percent=50
        )
        def approaching_budget():
            time.sleep(0.6)  # 600ms, which is 60% of 1000ms
            return "result"
        
        approaching_budget()
        
        alert_mgr = AlertManager()
        alerts = alert_mgr.get_alerts_by_operation("alert_test")
        
        assert len(alerts) == 1
        assert alerts[0].alert_level == AlertLevel.WARNING
    
    def test_decorator_critical_alert_on_breach(self):
        """Test that critical alert is triggered on significant breach."""
        @monitor_latency("critical_test", budget_ms=100)
        def critical_slow():
            time.sleep(0.3)  # 300ms, 200% over budget
            return "result"
        
        critical_slow()
        
        alert_mgr = AlertManager()
        critical_alerts = alert_mgr.get_critical_alerts()
        
        assert len(critical_alerts) >= 1
        assert any(a.operation_name == "critical_test" for a in critical_alerts)
    
    def test_decorator_transparent_result(self):
        """Test that decorator doesn't modify function result."""
        @monitor_latency("result_test", budget_ms=500)
        def returning_func(a: int, b: int) -> int:
            return a + b
        
        result = returning_func(5, 3)
        
        assert result == 8
    
    def test_decorator_with_exception(self):
        """Test that decorator still records metrics even when exception occurs."""
        @monitor_latency("exception_test", budget_ms=500)
        def failing_func():
            time.sleep(0.1)
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        monitor = LatencyMonitor()
        stats = monitor.get_stats("exception_test")
        
        assert stats["count"] == 1


class TestLatencyMonitor:
    """Tests for the latency monitoring system."""
    
    def setup_method(self):
        """Clear metrics before each test."""
        monitor = LatencyMonitor()
        monitor.clear_metrics()
    
    def test_record_latency_metric(self):
        """Test recording a single latency metric."""
        monitor = LatencyMonitor()
        monitor.record_latency(
            operation_name="test_op",
            execution_time_ms=250,
            budget_ms=500,
            operation_type="query",
            alert_threshold_percent=80
        )
        
        assert len(monitor.metrics) == 1
        assert monitor.metrics[0].operation_name == "test_op"
    
    def test_get_statistics(self):
        """Test getting statistics for an operation."""
        monitor = LatencyMonitor()
        
        # Record multiple executions
        for i in range(3):
            monitor.record_latency(
                operation_name="stats_test",
                execution_time_ms=100 + (i * 50),
                budget_ms=500,
                operation_type="query",
                alert_threshold_percent=80
            )
        
        stats = monitor.get_stats("stats_test")
        
        assert stats["count"] == 3
        assert stats["min_ms"] == 100
        assert stats["max_ms"] == 200
        assert stats["breach_rate"] == 0  # All within budget
    
    def test_breach_detection(self):
        """Test detection of budget breaches."""
        monitor = LatencyMonitor()
        
        monitor.record_latency("breach_test", 100, budget_ms=50, 
                              operation_type="query", alert_threshold_percent=80)
        monitor.record_latency("breach_test", 40, budget_ms=50, 
                              operation_type="query", alert_threshold_percent=80)
        
        breaches = monitor.get_breached_operations()
        assert len(breaches) == 1
        assert breaches[0].execution_time_ms == 100
    
    def test_alert_trigger_detection(self):
        """Test detection of alert thresholds."""
        monitor = LatencyMonitor()
        
        # 400ms execution, 500ms budget, 80% threshold = 400ms trigger
        monitor.record_latency("threshold_test", 400, budget_ms=500, 
                              operation_type="query", alert_threshold_percent=80)
        
        alerted = monitor.get_alerted_operations()
        assert len(alerted) == 1
        assert alerted[0].alert_triggered is True
    
    def test_percentile_calculations(self):
        """Test statistical percentile calculations."""
        monitor = LatencyMonitor()
        
        times = [100, 150, 200, 250, 300]
        for t in times:
            monitor.record_latency("percentile_test", t, budget_ms=500, 
                                  operation_type="query", alert_threshold_percent=80)
        
        stats = monitor.get_stats("percentile_test")
        
        assert stats["median_ms"] == 200
        assert stats["avg_ms"] == 200


class TestAlertManager:
    """Tests for the alert system."""
    
    def setup_method(self):
        """Clear alerts before each test."""
        alert_mgr = AlertManager()
        alert_mgr.clear_alerts()
    
    def test_create_warning_alert(self):
        """Test creating a warning alert."""
        alert_mgr = AlertManager()
        alert = alert_mgr.create_alert(
            operation_name="warning_test",
            actual_time_ms=450,
            budget_ms=500,
            alert_threshold_percent=80
        )
        
        assert alert.alert_level == AlertLevel.WARNING
        assert alert.operation_name == "warning_test"
    
    def test_create_critical_alert(self):
        """Test creating a critical alert."""
        alert_mgr = AlertManager()
        alert = alert_mgr.create_alert(
            operation_name="critical_test",
            actual_time_ms=800,
            budget_ms=500,
            alert_threshold_percent=80
        )
        
        assert alert.alert_level == AlertLevel.CRITICAL
        assert "CRITICAL" in alert.message
    
    def test_retrieve_alerts_by_operation(self):
        """Test retrieving alerts for specific operation."""
        alert_mgr = AlertManager()
        
        alert_mgr.create_alert("op_a", 450, 500, 80)
        alert_mgr.create_alert("op_b", 450, 500, 80)
        alert_mgr.create_alert("op_a", 460, 500, 80)
        
        op_a_alerts = alert_mgr.get_alerts_by_operation("op_a")
        assert len(op_a_alerts) == 2
    
    def test_get_critical_alerts(self):
        """Test retrieving only critical alerts."""
        alert_mgr = AlertManager()
        
        alert_mgr.create_alert("op_warning", 450, 500, 80)  # Warning
        alert_mgr.create_alert("op_critical", 800, 500, 80)  # Critical
        
        critical = alert_mgr.get_critical_alerts()
        assert len(critical) >= 1
        assert any(a.operation_name == "op_critical" for a in critical)


class TestArtificialDelays:
    """Tests with artificial delays to validate latency budgets."""
    
    def setup_method(self):
        """Clear metrics before each test."""
        monitor = LatencyMonitor()
        monitor.clear_metrics()
        alert_mgr = AlertManager()
        alert_mgr.clear_alerts()
    
    def test_slow_query_breach(self):
        """Simulate a slow query that exceeds budget."""
        @monitor_latency("slow_query", budget_ms=200, operation_type="query")
        def slow_db_query():
            # Simulates slow database query due to missing index
            time.sleep(0.5)  # 500ms
            return [{"id": 1, "name": "test"}]
        
        slow_db_query()
        
        monitor = LatencyMonitor()
        breaches = monitor.get_breached_operations()
        
        assert len(breaches) == 1
        assert breaches[0].execution_time_ms > 200
    
    def test_slow_write_command(self):
        """Simulate a slow write operation."""
        @monitor_latency("slow_write", budget_ms=500, operation_type="command")
        def slow_db_write():
            # Simulates slow write with transaction overhead
            time.sleep(0.8)  # 800ms
            return {"affected_rows": 1}
        
        slow_db_write()
        
        monitor = LatencyMonitor()
        breaches = monitor.get_breached_operations()
        
        assert len(breaches) == 1
    
    def test_cold_start_vs_warm(self):
        """Compare cold start (first call) vs warm (subsequent calls)."""
        @monitor_latency("cold_warm_test", budget_ms=300)
        def potentially_slow_op():
            # First call might be slow, subsequent calls faster
            time.sleep(0.1)
            return "result"
        
        # Cold start
        potentially_slow_op()
        
        # Warm starts
        for _ in range(3):
            potentially_slow_op()
        
        monitor = LatencyMonitor()
        stats = monitor.get_stats("cold_warm_test")
        
        assert stats["count"] == 4
        # All should be within budget since we're sleeping 100ms
        assert stats["breach_rate"] == 0
    
    def test_downstream_slow_service(self):
        """Simulate latency from downstream service dependency."""
        @monitor_latency("downstream_call", budget_ms=1000)
        def call_downstream_service():
            # Simulates call to external/downstream service
            time.sleep(1.5)  # 1500ms (exceeds budget)
            return {"status": "success"}
        
        call_downstream_service()
        
        monitor = LatencyMonitor()
        breaches = monitor.get_breached_operations()
        
        assert len(breaches) == 1
    
    def test_parallel_execution_simulation(self):
        """Test monitoring multiple concurrent operations."""
        @monitor_latency("parallel_op", budget_ms=300)
        def fast_operation():
            time.sleep(0.1)
            return "fast"
        
        @monitor_latency("parallel_op", budget_ms=300)
        def another_operation():
            time.sleep(0.15)
            return "medium"
        
        # Simulate parallel execution
        fast_operation()
        another_operation()
        
        monitor = LatencyMonitor()
        stats = monitor.get_stats("parallel_op")
        
        assert stats["count"] == 2
        assert stats["breach_rate"] == 0


class TestLatencyMetricsIntegration:
    """Integration tests for the complete latency system."""
    
    def setup_method(self):
        """Clear state before each test."""
        monitor = LatencyMonitor()
        monitor.clear_metrics()
        alert_mgr = AlertManager()
        alert_mgr.clear_alerts()
    
    def test_end_to_end_flow(self):
        """Test complete flow from operation to alert."""
        @monitor_latency("e2e_test", budget_ms=100, alert_threshold_percent=50)
        def test_operation():
            time.sleep(0.08)  # 80ms (within budget, triggers alert)
            return "result"
        
        test_operation()
        
        # Check metrics
        monitor = LatencyMonitor()
        stats = monitor.get_stats("e2e_test")
        assert stats["count"] == 1
        
        # Check alerts
        alert_mgr = AlertManager()
        alerts = alert_mgr.get_alerts_by_operation("e2e_test")
        assert len(alerts) == 1
    
    def test_multiple_operations_tracked_independently(self):
        """Test that multiple operations are tracked independently."""
        @monitor_latency("op1", budget_ms=100)
        def operation_1():
            time.sleep(0.05)
            return 1
        
        @monitor_latency("op2", budget_ms=200)
        def operation_2():
            time.sleep(0.15)
            return 2
        
        operation_1()
        operation_1()
        operation_2()
        operation_2()
        
        monitor = LatencyMonitor()
        
        stats_op1 = monitor.get_stats("op1")
        stats_op2 = monitor.get_stats("op2")
        
        assert stats_op1["count"] == 2
        assert stats_op2["count"] == 2
        assert stats_op1["breach_rate"] == 0
        assert stats_op2["breach_rate"] == 0
