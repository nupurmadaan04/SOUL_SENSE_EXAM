"""
Query Plan Regression Detector

Tracks query execution plans and detects performance regressions by:
- Capturing baseline plans for registered queries
- Comparing current plans against baselines
- Detecting execution time increases and plan changes
- Providing alerts and metrics

Usage:
    detector = QueryPlanRegressionDetector()
    detector.register_baseline(
        query_id="user_scores",
        sql="SELECT * FROM scores WHERE user_id = ?",
        connection=conn,
        expected_time_ms=10
    )
    regression = detector.detect_regression("user_scores", current_time_ms=25)
    if regression:
        print(regression)
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Regression severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class QueryExecutionPlan:
    """Represents a single query execution plan."""
    query_id: str
    sql_text: str
    plan_output: str  # Raw EXPLAIN QUERY PLAN output
    execution_time_ms: float
    row_count: int
    timestamp: str
    table_names: List[str] = field(default_factory=list)
    uses_index: bool = False
    is_scan: bool = True  # True if SCAN, False if SEARCH

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


@dataclass
class RegressionBaseline:
    """Stores baseline metrics for a query."""
    query_id: str
    sql_text: str
    baseline_plan: str
    baseline_time_ms: float
    baseline_row_count: int
    table_names: List[str] = field(default_factory=list)
    uses_index: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_verified: str = field(default_factory=lambda: datetime.now().isoformat())
    observation_count: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(**data)


@dataclass
class RegressionAlert:
    """Represents a detected regression."""
    query_id: str
    severity: Severity
    regression_type: str  # "time", "plan", "scan_vs_search"
    details: str
    baseline_value: float
    current_value: float
    variance_percent: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['severity'] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        data['severity'] = Severity(data['severity'])
        return cls(**data)


class QueryPlanRegressionDetector:
    """Detects query plan regressions."""

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize detector with optional custom registry path."""
        if registry_path is None:
            registry_path = Path(__file__).parent.parent.parent / "data" / "query_baselines_registry.json"
        
        self.registry_path = Path(registry_path)
        self.baselines: Dict[str, RegressionBaseline] = {}
        self.alerts: List[RegressionAlert] = []
        self._load_baselines()

    def _load_baselines(self) -> None:
        """Load baselines from registry file."""
        if not self.registry_path.exists():
            self.baselines = {}
            return

        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                self.baselines = {
                    qid: RegressionBaseline.from_dict(baseline)
                    for qid, baseline in data.get('baselines', {}).items()
                }
                self.alerts = [
                    RegressionAlert.from_dict(alert)
                    for alert in data.get('alerts', [])
                ]
            logger.info(f"Loaded {len(self.baselines)} query baselines")
        except Exception as e:
            logger.warning(f"Failed to load baselines: {e}")
            self.baselines = {}
            self.alerts = []

    def _persist_baselines(self) -> None:
        """Save baselines to registry file."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'baselines': {qid: bl.to_dict() for qid, bl in self.baselines.items()},
                'alerts': [a.to_dict() for a in self.alerts[-100:]],  # Keep last 100 alerts
                'updated_at': datetime.now().isoformat()
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist baselines: {e}")

    def _analyze_plan(self, plan_output: str) -> Tuple[bool, bool]:
        """Analyze query plan to extract key metrics.
        
        Returns: (uses_index, is_scan)
        - uses_index: True if any index is used
        - is_scan: True if plan contains table scan
        """
        plan_str = str(plan_output).upper()
        
        uses_index = 'SEARCH' in plan_str and any(
            idx in plan_str for idx in ['IX_', 'IDX_', 'AUTOINDEX']
        )
        is_scan = 'SCAN' in plan_str
        
        return uses_index, is_scan

    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL (simple heuristic)."""
        sql_upper = sql.upper()
        tables = []
        
        keywords = ['FROM', 'INTO', 'UPDATE', 'JOIN']
        for keyword in keywords:
            parts = sql_upper.split(keyword)
            if len(parts) > 1:
                tokens = parts[1].split()[0]
                clean_name = tokens.strip('(),. ')
                if clean_name and not clean_name.startswith('SELECT'):
                    tables.append(clean_name.lower())
        
        return list(set(tables))

    def _get_query_plan(self, sql: str, connection: sqlite3.Connection) -> str:
        """Execute EXPLAIN QUERY PLAN for given SQL."""
        try:
            cursor = connection.cursor()
            # For parameterized queries, provide dummy values
            # Replace ? with dummy constants for EXPLAIN
            explain_sql = f"EXPLAIN QUERY PLAN {sql}"
            
            # Try without parameters first
            try:
                cursor.execute(explain_sql)
                plan = cursor.fetchall()
                return str(plan)
            except sqlite3.InterfaceError:
                # If parameters needed, replace ? with dummy values
                param_count = sql.count('?')
                params = [0] * param_count
                cursor.execute(explain_sql, params)
                plan = cursor.fetchall()
                return str(plan)
        except Exception as e:
            logger.warning(f"Could not get query plan: {e}, will use basic analysis")
            # Still create baseline even without plan
            return "SCAN"  # Default conservative assumption

    def register_baseline(
        self,
        query_id: str,
        sql: str,
        connection: sqlite3.Connection,
        expected_time_ms: float,
        row_count: int = 0
    ) -> bool:
        """Register a new query baseline.
        
        Args:
            query_id: Unique identifier for the query
            sql: SQL query text
            connection: SQLite database connection
            expected_time_ms: Expected execution time (baseline)
            row_count: Expected row count
        
        Returns:
            True if baseline registered successfully
        """
        if query_id in self.baselines:
            logger.warning(f"Baseline already exists for {query_id}, updating...")

        try:
            plan = self._get_query_plan(sql, connection)

            uses_index, is_scan = self._analyze_plan(plan)
            tables = self._extract_tables(sql)

            baseline = RegressionBaseline(
                query_id=query_id,
                sql_text=sql,
                baseline_plan=plan,
                baseline_time_ms=expected_time_ms,
                baseline_row_count=row_count,
                table_names=tables,
                uses_index=uses_index,
                observation_count=1
            )

            self.baselines[query_id] = baseline
            self._persist_baselines()
            logger.info(f"Baseline registered for query {query_id}")
            return True

        except Exception as e:
            logger.error(f"Error registering baseline for {query_id}: {e}")
            return False

    def detect_regression(
        self,
        query_id: str,
        current_time_ms: float,
        current_plan: Optional[str] = None,
        row_count: int = 0,
        threshold_percent: float = 10.0
    ) -> Optional[RegressionAlert]:
        """Detect if query has regressed.
        
        Args:
            query_id: Query identifier
            current_time_ms: Current execution time
            current_plan: Current EXPLAIN output (optional)
            row_count: Current row count
            threshold_percent: Regression threshold percentage
        
        Returns:
            RegressionAlert if regression detected, None otherwise
        """
        if query_id not in self.baselines:
            logger.warning(f"No baseline for query {query_id}")
            return None

        baseline = self.baselines[query_id]
        variance = ((current_time_ms - baseline.baseline_time_ms) / baseline.baseline_time_ms) * 100

        # Check execution time regression
        if variance > threshold_percent:
            severity = Severity.CRITICAL if variance > 30 else Severity.WARNING if variance > 15 else Severity.INFO
            
            alert = RegressionAlert(
                query_id=query_id,
                severity=severity,
                regression_type="time",
                details=f"Execution time increased from {baseline.baseline_time_ms:.2f}ms to {current_time_ms:.2f}ms",
                baseline_value=baseline.baseline_time_ms,
                current_value=current_time_ms,
                variance_percent=variance
            )
            
            self.alerts.append(alert)
            self._persist_baselines()
            logger.warning(f"{severity.upper()} regression detected for {query_id}: {variance:.1f}%")
            return alert

        # Check plan change
        if current_plan and current_plan != baseline.baseline_plan:
            uses_index, is_scan = self._analyze_plan(current_plan)
            
            # Alert if plan became a scan when it wasn't before
            if is_scan and not baseline.is_scan:
                alert = RegressionAlert(
                    query_id=query_id,
                    severity=Severity.CRITICAL,
                    regression_type="scan_vs_search",
                    details=f"Query changed from SEARCH to SCAN (no index utilization)",
                    baseline_value=1 if baseline.uses_index else 0,
                    current_value=1 if uses_index else 0,
                    variance_percent=100.0
                )
                
                self.alerts.append(alert)
                self._persist_baselines()
                logger.warning(f"CRITICAL regression detected for {query_id}: index no longer used")
                return alert

        return None

    def get_baseline(self, query_id: str) -> Optional[RegressionBaseline]:
        """Get baseline for a query."""
        return self.baselines.get(query_id)

    def list_baselines(self) -> List[RegressionBaseline]:
        """Get all registered baselines."""
        return list(self.baselines.values())

    def get_alerts_for_query(self, query_id: str) -> List[RegressionAlert]:
        """Get all alerts for a specific query."""
        return [a for a in self.alerts if a.query_id == query_id]

    def get_recent_alerts(self, hours: int = 24) -> List[RegressionAlert]:
        """Get alerts from last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            a for a in self.alerts
            if datetime.fromisoformat(a.timestamp) > cutoff
        ]

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive regression report."""
        recent_alerts = self.get_recent_alerts(24)
        critical_count = len([a for a in recent_alerts if a.severity == Severity.CRITICAL])
        warning_count = len([a for a in recent_alerts if a.severity == Severity.WARNING])

        return {
            'total_baselines': len(self.baselines),
            'total_queries_monitored': len(self.baselines),
            'recent_alerts_24h': len(recent_alerts),
            'critical_alerts': critical_count,
            'warning_alerts': warning_count,
            'info_alerts': len(recent_alerts) - critical_count - warning_count,
            'most_regressed_queries': [
                {
                    'query_id': a.query_id,
                    'severity': a.severity.value,
                    'variance': f"{a.variance_percent:.1f}%",
                    'type': a.regression_type
                }
                for a in sorted(recent_alerts, key=lambda x: abs(x.variance_percent), reverse=True)[:5]
            ],
            'timestamp': datetime.now().isoformat()
        }

    def reset_baseline(self, query_id: str) -> bool:
        """Reset baseline for a query (will be re-registered on next capture)."""
        if query_id in self.baselines:
            del self.baselines[query_id]
            self._persist_baselines()
            logger.info(f"Baseline reset for query {query_id}")
            return True
        return False

    def clear_old_alerts(self, days: int = 30) -> int:
        """Clear alerts older than N days."""
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.alerts)
        self.alerts = [
            a for a in self.alerts
            if datetime.fromisoformat(a.timestamp) > cutoff
        ]
        removed = original_count - len(self.alerts)
        self._persist_baselines()
        logger.info(f"Removed {removed} old alerts")
        return removed
