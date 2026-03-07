"""
Test Suite for Query Plan Regression Detector

Comprehensive tests for query plan detection, baseline management, and regression alerts.

Run with: pytest tests/test_query_plan_regression_detector.py -v
Or:      python tests/test_query_plan_regression_detector.py
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infra.query_plan_regression_detector import (
    QueryPlanRegressionDetector,
    RegressionBaseline,
    RegressionAlert,
    QueryExecutionPlan,
    Severity
)


class BaselinesManagementTests(unittest.TestCase):
    """Test baseline registration and management."""

    def setUp(self):
        """Set up test detector with temporary registry."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = Path(self.temp_dir.name) / "test_registry.json"
        self.detector = QueryPlanRegressionDetector(registry_path=self.registry_path)
        
        # In-memory test database
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self._create_test_tables()

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_dir.cleanup()

    def _create_test_tables(self):
        """Create test tables."""
        self.cursor.execute('''
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                value INTEGER,
                timestamp DATETIME
            )
        ''')
        self.cursor.execute('CREATE INDEX ix_scores_user_id ON scores(user_id)')
        self.cursor.execute('CREATE INDEX ix_scores_timestamp ON scores(timestamp)')
        self.conn.commit()

    def test_01_register_baseline_success(self):
        """Test successful baseline registration."""
        result = self.detector.register_baseline(
            query_id="test_query_1",
            sql="SELECT * FROM scores WHERE user_id = ?",
            connection=self.conn,
            expected_time_ms=10.5,
            row_count=100
        )
        
        self.assertTrue(result, "Baseline should register successfully")
        self.assertIn("test_query_1", self.detector.baselines)
        
        baseline = self.detector.baselines["test_query_1"]
        self.assertEqual(baseline.query_id, "test_query_1")
        self.assertEqual(baseline.baseline_time_ms, 10.5)
        self.assertEqual(baseline.baseline_row_count, 100)

    def test_02_register_baseline_creates_registry(self):
        """Test that registry file is created on baseline registration."""
        self.detector.register_baseline(
            query_id="test_query",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=5.0
        )
        
        self.assertTrue(self.registry_path.exists(), "Registry file should be created")
        
        with open(self.registry_path) as f:
            data = json.load(f)
            self.assertIn('baselines', data)
            self.assertIn('test_query', data['baselines'])

    def test_03_register_multiple_baselines(self):
        """Test registering multiple baselines."""
        for i in range(5):
            self.detector.register_baseline(
                query_id=f"query_{i}",
                sql=f"SELECT * FROM scores LIMIT {i+1}",
                connection=self.conn,
                expected_time_ms=float(i+1)
            )
        
        self.assertEqual(len(self.detector.baselines), 5)
        self.assertEqual(len(self.detector.list_baselines()), 5)

    def test_04_load_baselines_from_file(self):
        """Test loading baselines from persisted registry."""
        # Register and persist
        self.detector.register_baseline(
            query_id="persisted_query",
            sql="SELECT * FROM scores WHERE user_id = ?",
            connection=self.conn,
            expected_time_ms=7.2
        )
        
        # Create new detector instance - should load from file
        detector2 = QueryPlanRegressionDetector(registry_path=self.registry_path)
        
        self.assertIn("persisted_query", detector2.baselines)
        baseline = detector2.baselines["persisted_query"]
        self.assertEqual(baseline.baseline_time_ms, 7.2)

    def test_05_reset_baseline(self):
        """Test resetting a baseline."""
        self.detector.register_baseline(
            query_id="query_to_reset",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=5.0
        )
        
        self.assertIn("query_to_reset", self.detector.baselines)
        
        result = self.detector.reset_baseline("query_to_reset")
        
        self.assertTrue(result)
        self.assertNotIn("query_to_reset", self.detector.baselines)

    def test_06_reset_nonexistent_baseline(self):
        """Test resetting a baseline that doesn't exist."""
        result = self.detector.reset_baseline("nonexistent")
        self.assertFalse(result)

    def test_07_get_baseline(self):
        """Test retrieving a specific baseline."""
        self.detector.register_baseline(
            query_id="test_get",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=3.0
        )
        
        baseline = self.detector.get_baseline("test_get")
        
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline.query_id, "test_get")
        self.assertEqual(baseline.baseline_time_ms, 3.0)

    def test_08_baseline_has_table_info(self):
        """Test that baseline extracts table names correctly."""
        self.detector.register_baseline(
            query_id="table_extraction",
            sql="SELECT * FROM scores WHERE user_id = ?",
            connection=self.conn,
            expected_time_ms=5.0
        )
        
        baseline = self.detector.baselines["table_extraction"]
        self.assertTrue(len(baseline.table_names) > 0)
        self.assertIn("scores", baseline.table_names)


class RegressionDetectionTests(unittest.TestCase):
    """Test regression detection logic."""

    def setUp(self):
        """Set up test detector."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = Path(self.temp_dir.name) / "test_registry.json"
        self.detector = QueryPlanRegressionDetector(registry_path=self.registry_path)
        
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self._create_test_tables()

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_dir.cleanup()

    def _create_test_tables(self):
        """Create test tables."""
        self.cursor.execute('''
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                value INTEGER,
                timestamp DATETIME
            )
        ''')
        self.cursor.execute('CREATE INDEX ix_scores_user_id ON scores(user_id)')
        self.conn.commit()

    def test_01_detect_time_regression_warning(self):
        """Test detecting time regression in WARNING range."""
        self.detector.register_baseline(
            query_id="time_test",
            sql="SELECT * FROM scores WHERE user_id = ?",
            connection=self.conn,
            expected_time_ms=10.0
        )
        
        # 18% increase = WARNING
        alert = self.detector.detect_regression(
            query_id="time_test",
            current_time_ms=11.8,
            threshold_percent=10.0
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, Severity.WARNING)
        self.assertEqual(alert.regression_type, "time")
        self.assertAlmostEqual(alert.variance_percent, 18.0, places=0)

    def test_02_detect_time_regression_critical(self):
        """Test detecting time regression in CRITICAL range."""
        self.detector.register_baseline(
            query_id="critical_test",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=10.0
        )
        
        # 35% increase = CRITICAL
        alert = self.detector.detect_regression(
            query_id="critical_test",
            current_time_ms=13.5,
            threshold_percent=10.0
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, Severity.CRITICAL)

    def test_03_no_regression_under_threshold(self):
        """Test no alert when under threshold."""
        self.detector.register_baseline(
            query_id="no_regression",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=10.0
        )
        
        # 5% increase, threshold 10% = no alert
        alert = self.detector.detect_regression(
            query_id="no_regression",
            current_time_ms=10.5,
            threshold_percent=10.0
        )
        
        self.assertIsNone(alert)

    def test_04_detect_regression_no_baseline(self):
        """Test detection with no baseline raises gracefully."""
        alert = self.detector.detect_regression(
            query_id="nonexistent",
            current_time_ms=5.0
        )
        
        self.assertIsNone(alert)

    def test_05_regression_stored_in_alerts(self):
        """Test that detected regressions are stored."""
        self.detector.register_baseline(
            query_id="alert_test",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=10.0
        )
        
        alert = self.detector.detect_regression(
            query_id="alert_test",
            current_time_ms=12.0,
            threshold_percent=10.0
        )
        
        self.assertIsNotNone(alert)
        self.assertEqual(len(self.detector.alerts), 1)
        self.assertEqual(self.detector.alerts[0], alert)

    def test_06_get_alerts_for_query(self):
        """Test retrieving alerts for specific query."""
        # Register and generate alerts
        self.detector.register_baseline(
            query_id="query_a",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=10.0
        )
        self.detector.register_baseline(
            query_id="query_b",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=10.0
        )
        
        self.detector.detect_regression("query_a", current_time_ms=15.0, threshold_percent=10)
        self.detector.detect_regression("query_b", current_time_ms=20.0, threshold_percent=10)
        
        alerts_a = self.detector.get_alerts_for_query("query_a")
        
        self.assertEqual(len(alerts_a), 1)
        self.assertEqual(alerts_a[0].query_id, "query_a")

    def test_07_get_recent_alerts(self):
        """Test retrieving recent alerts."""
        self.detector.register_baseline(
            query_id="recent_test",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=10.0
        )
        
        # Create alert
        self.detector.detect_regression(
            query_id="recent_test",
            current_time_ms=15.0,
            threshold_percent=10
        )
        
        recent = self.detector.get_recent_alerts(hours=1)
        
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].query_id, "recent_test")


class PlanAnalysisTests(unittest.TestCase):
    """Test query plan analysis."""

    def setUp(self):
        """Set up test detector."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = Path(self.temp_dir.name) / "test_registry.json"
        self.detector = QueryPlanRegressionDetector(registry_path=self.registry_path)

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_01_analyze_plan_with_index(self):
        """Test analyzing plan that uses index."""
        plan = "[(0, 0, 0, 'SEARCH TABLE scores USING INDEX ix_scores_user_id')]"
        
        uses_index, is_scan = self.detector._analyze_plan(plan)
        
        self.assertTrue(uses_index)
        self.assertFalse(is_scan)

    def test_02_analyze_plan_with_scan(self):
        """Test analyzing plan that uses table scan."""
        plan = "[(0, 0, 0, 'SCAN TABLE scores')]"
        
        uses_index, is_scan = self.detector._analyze_plan(plan)
        
        self.assertTrue(is_scan)

    def test_03_extract_tables_from_sql(self):
        """Test extracting table names from SQL."""
        sql = "SELECT * FROM scores WHERE user_id = ?"
        tables = self.detector._extract_tables(sql)
        
        self.assertIn("scores", tables)

    def test_04_extract_multiple_tables(self):
        """Test extracting multiple table names."""
        sql = "SELECT * FROM scores JOIN users ON scores.user_id = users.id"
        tables = self.detector._extract_tables(sql)
        
        self.assertGreaterEqual(len(tables), 1)


class ReportGenerationTests(unittest.TestCase):
    """Test report generation."""

    def setUp(self):
        """Set up test detector."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = Path(self.temp_dir.name) / "test_registry.json"
        self.detector = QueryPlanRegressionDetector(registry_path=self.registry_path)
        
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self._create_test_tables()

    def tearDown(self):
        """Clean up."""
        self.conn.close()
        self.temp_dir.cleanup()

    def _create_test_tables(self):
        """Create test tables."""
        self.cursor.execute('''
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY,
                user_id INTEGER
            )
        ''')
        self.conn.commit()

    def test_01_generate_report_no_baselines(self):
        """Test generating report with no baselines."""
        report = self.detector.generate_report()
        
        self.assertEqual(report['total_baselines'], 0)
        self.assertEqual(report['recent_alerts_24h'], 0)

    def test_02_generate_report_with_baselines(self):
        """Test generating report with baselines and alerts."""
        # Register baselines
        for i in range(3):
            self.detector.register_baseline(
                query_id=f"query_{i}",
                sql="SELECT * FROM scores",
                connection=self.conn,
                expected_time_ms=5.0
            )
        
        # Generate some alerts
        self.detector.detect_regression("query_0", current_time_ms=6.0, threshold_percent=10)
        self.detector.detect_regression("query_1", current_time_ms=8.0, threshold_percent=10)
        
        report = self.detector.generate_report()
        
        self.assertEqual(report['total_baselines'], 3)
        self.assertEqual(report['recent_alerts_24h'], 2)
        self.assertGreater(len(report['most_regressed_queries']), 0)

    def test_03_report_contains_required_fields(self):
        """Test that report contains all required fields."""
        self.detector.register_baseline(
            query_id="test",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=5.0
        )
        
        report = self.detector.generate_report()
        
        required_fields = [
            'total_baselines', 'total_queries_monitored',
            'recent_alerts_24h', 'critical_alerts',
            'warning_alerts', 'info_alerts',
            'most_regressed_queries', 'timestamp'
        ]
        
        for field in required_fields:
            self.assertIn(field, report, f"Report should contain '{field}'")

    def test_04_clear_old_alerts(self):
        """Test clearing old alerts."""
        self.detector.register_baseline(
            query_id="test",
            sql="SELECT * FROM scores",
            connection=self.conn,
            expected_time_ms=5.0
        )
        
        # Create alert
        self.detector.detect_regression("test", current_time_ms=6.0, threshold_percent=10)
        
        # Manually backdate alert
        if self.detector.alerts:
            old_time = (datetime.now() - timedelta(days=40)).isoformat()
            self.detector.alerts[0].timestamp = old_time
        
        removed = self.detector.clear_old_alerts(days=30)
        
        self.assertGreater(removed, 0)


class DataModelTests(unittest.TestCase):
    """Test data models."""

    def test_01_baseline_to_from_dict(self):
        """Test baseline serialization."""
        baseline = RegressionBaseline(
            query_id="test",
            sql_text="SELECT *",
            baseline_plan="plan",
            baseline_time_ms=5.0,
            baseline_row_count=100,
            table_names=["scores"]
        )
        
        data = baseline.to_dict()
        restored = RegressionBaseline.from_dict(data)
        
        self.assertEqual(restored.query_id, baseline.query_id)
        self.assertEqual(restored.baseline_time_ms, baseline.baseline_time_ms)

    def test_02_alert_to_from_dict(self):
        """Test alert serialization."""
        alert = RegressionAlert(
            query_id="test",
            severity=Severity.WARNING,
            regression_type="time",
            details="Test alert",
            baseline_value=5.0,
            current_value=6.0,
            variance_percent=20.0
        )
        
        data = alert.to_dict()
        restored = RegressionAlert.from_dict(data)
        
        self.assertEqual(restored.query_id, alert.query_id)
        self.assertEqual(restored.severity, Severity.WARNING)


def run_all_tests():
    """Run all tests and print summary."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(BaselinesManagementTests))
    suite.addTests(loader.loadTestsFromTestCase(RegressionDetectionTests))
    suite.addTests(loader.loadTestsFromTestCase(PlanAnalysisTests))
    suite.addTests(loader.loadTestsFromTestCase(ReportGenerationTests))
    suite.addTests(loader.loadTestsFromTestCase(DataModelTests))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run:    {result.testsRun}")
    print(f"Passed:       {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed:       {len(result.failures)}")
    print(f"Errors:       {len(result.errors)}")
    print("=" * 70)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
