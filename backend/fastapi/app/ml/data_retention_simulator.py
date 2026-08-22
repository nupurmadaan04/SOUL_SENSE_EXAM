"""
Data retention impact simulator for feasibility analysis.

Provides deterministic, testable predictions of storage/performance impact
from different data retention policies.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RetentionPolicy:
    """Configuration for retention days per table type."""
    otp_codes: int = 7
    user_sessions: int = 90
    refresh_tokens: int = 180
    password_history: int = 365
    token_revocations: int = 7
    login_attempts: int = 90
    audit_logs: int = 1095  # 3 years for compliance
    analytics_events: int = 365
    scores: int = 1825  # 5 years
    responses: int = 1825  # 5 years
    users: int = 36500  # 100 years (keep indefinitely)


class DataRetentionSimulator:
    """Simulate storage and performance impact of retention policies."""

    # Table metadata: (avg_bytes_per_row, table_tier)
    TABLE_METADATA = {
        "otp_codes": (150, "transient"),
        "user_sessions": (500, "sessions"),
        "refresh_tokens": (200, "sessions"),
        "password_history": (100, "transactional"),
        "token_revocations": (80, "transient"),
        "login_attempts": (200, "audit"),
        "audit_logs": (800, "compliance"),
        "analytics_events": (400, "analytics"),
        "scores": (300, "transactional"),
        "responses": (200, "transactional"),
        "users": (1000, "core"),
    }

    def __init__(self, current_row_counts: Optional[Dict[str, int]] = None):
        """
        Initialize simulator.
        
        Args:
            current_row_counts: Dict of table_name -> row_count. Defaults to typical production values.
        """
        self.current_row_counts = current_row_counts or {
            "otp_codes": 50000,
            "user_sessions": 100000,
            "refresh_tokens": 80000,
            "password_history": 200000,
            "token_revocations": 30000,
            "login_attempts": 500000,
            "audit_logs": 1000000,
            "analytics_events": 2000000,
            "scores": 500000,
            "responses": 3000000,
            "users": 10000,
        }

    def calculate_storage_impact(
        self, policy: RetentionPolicy
    ) -> Dict[str, any]:
        """
        Calculate storage impact of retention policy.
        
        Returns dict with current_gb, projected_gb, savings_pct.
        """
        current_storage_gb = self._calculate_total_storage()
        
        retained_rows = self._estimate_retained_rows(policy)
        projected_storage_gb = self._storage_from_rows(retained_rows)
        
        savings_pct = (
            (current_storage_gb - projected_storage_gb) / current_storage_gb * 100
            if current_storage_gb > 0
            else 0
        )

        return {
            "current_gb": round(current_storage_gb, 1),
            "projected_gb": round(projected_storage_gb, 1),
            "savings_pct": round(savings_pct, 1),
        }

    def calculate_performance_impact(self, policy: RetentionPolicy) -> Dict[str, any]:
        """
        Calculate performance impact (slowdown, cleanup time).
        
        Returns dict with query_slowdown_pct, cleanup_time_hours, index_fragmentation.
        """
        retained_rows = self._estimate_retained_rows(policy)
        total_retained = sum(retained_rows.values())
        total_current = sum(self.current_row_counts.values())
        
        deletion_ratio = (
            (total_current - total_retained) / total_current
            if total_current > 0
            else 0
        )
        
        # Model: 10% deletion = ~2% query slowdown (conservative)
        query_slowdown_pct = deletion_ratio * 20
        
        # Cleanup time: ~1 record per 10ms (conservative)
        cleanup_time_hours = total_current * deletion_ratio * 0.01 / 3600
        
        # Index fragmentation: high if >50% deleted
        if deletion_ratio > 0.5:
            fragmentation = "high"
        elif deletion_ratio > 0.3:
            fragmentation = "moderate"
        else:
            fragmentation = "low"

        return {
            "query_slowdown_pct": round(query_slowdown_pct, 1),
            "cleanup_time_hours": round(cleanup_time_hours, 2),
            "index_fragmentation": fragmentation,
        }

    def calculate_compliance_impact(self, policy: RetentionPolicy) -> Dict[str, any]:
        """
        Calculate compliance score and check retention sufficiency.
        
        Returns dict with score (0-100), violations, recommendations.
        """
        score = 100
        violations = []
        recommendations = []

        # GDPR: Audit logs minimum 1 year
        if policy.audit_logs < 365:
            violations.append("GDPR: audit_logs < 1 year")
            score -= 20

        # PII: Sensitive data (users, profiles) should be kept unless deleted
        if policy.users < 100:
            violations.append("Risk: users retention too low")
            score -= 15

        # Transient data should be short-lived
        if policy.otp_codes > 30:
            recommendations.append("OTP retention > 30 days (recommend lowering)")

        # Compliance scoring: weighted by table importance
        if policy.audit_logs < 1095:
            recommendations.append("Consider 3-year audit retention for compliance")

        return {
            "score": max(0, score),
            "violations": violations,
            "recommendations": recommendations,
        }

    def recommend_policy(
        self,
        max_storage_gb: Optional[int] = None,
        compliance_strict: bool = False,
    ) -> Tuple[RetentionPolicy, Dict[str, any]]:
        """
        Recommend retention policy based on constraints.
        
        Args:
            max_storage_gb: Max storage budget. None = no limit.
            compliance_strict: If True, enforce strict compliance (3yr audit logs, etc.)
        
        Returns: (RetentionPolicy, rationale_dict)
        """
        if compliance_strict:
            policy = RetentionPolicy(
                otp_codes=7,
                user_sessions=90,
                refresh_tokens=180,
                password_history=365,
                audit_logs=1095,  # 3 years strict
                scores=1825,
                responses=1825,
            )
        else:
            policy = RetentionPolicy()  # Defaults

        storage = self.calculate_storage_impact(policy)
        
        returned_policy = policy
        if max_storage_gb and storage["projected_gb"] > max_storage_gb:
            # Suggest aggressive cleanup
            returned_policy = RetentionPolicy(
                otp_codes=3,
                user_sessions=30,
                refresh_tokens=60,
                password_history=180,
                audit_logs=730,  # 2 years
                scores=730,
                responses=730,
            )
            storage = self.calculate_storage_impact(returned_policy)

        rationale = {
            "policy_name": "strict_compliance" if compliance_strict else "default",
            "storage": storage,
            "reason": f"Projected storage: {storage['projected_gb']}GB",
        }

        return returned_policy, rationale

    def simulate_cleanup(
        self, policy: RetentionPolicy, risk_assessment: bool = True
    ) -> Dict[str, any]:
        """
        Simulate cleanup operation (dry-run style).
        
        Args:
            policy: Retention policy to apply.
            risk_assessment: If True, flag cascading deletes and race conditions.
        
        Returns dict with rows_deleted, storage_freed_gb, warnings.
        """
        retained_rows = self._estimate_retained_rows(policy)
        total_current = sum(self.current_row_counts.values())
        total_retained = sum(retained_rows.values())
        rows_deleted = total_current - total_retained

        storage_freed_gb = rows_deleted * 0.0005  # Rough average per row

        warnings = []
        if risk_assessment:
            # Cascading delete warnings
            if rows_deleted > 1000000:
                warnings.append("Large deletion (>1M rows): test on staging first")
            if self.current_row_counts.get("users", 0) > 0:
                warnings.append("User cascade: deleting scores/responses will cascade to users")

        return {
            "rows_deleted": rows_deleted,
            "storage_freed_gb": round(storage_freed_gb, 1),
            "cleanup_time_hours": self.calculate_performance_impact(policy)[
                "cleanup_time_hours"
            ],
            "warnings": warnings,
        }

    # === Private Helpers ===

    def _calculate_total_storage(self) -> float:
        """Calculate current total storage in GB."""
        total_bytes = sum(
            rows * self.TABLE_METADATA[table][0]
            for table, rows in self.current_row_counts.items()
            if table in self.TABLE_METADATA
        )
        return total_bytes / (1024 ** 3)

    def _estimate_retained_rows(self, policy: RetentionPolicy) -> Dict[str, int]:
        """Estimate rows retained after applying retention policy."""
        retention_map = {
            "otp_codes": policy.otp_codes,
            "user_sessions": policy.user_sessions,
            "refresh_tokens": policy.refresh_tokens,
            "password_history": policy.password_history,
            "token_revocations": policy.token_revocations,
            "login_attempts": policy.login_attempts,
            "audit_logs": policy.audit_logs,
            "analytics_events": policy.analytics_events,
            "scores": policy.scores,
            "responses": policy.responses,
            "users": policy.users,
        }

        retained = {}
        for table, current_rows in self.current_row_counts.items():
            days = retention_map.get(table, 365)
            # Rough linear assumption: rows uniformly distributed over time
            # Assume data is 5 years old on average, so (days/1825) retained
            retention_ratio = min(days / 1825, 1.0)
            retained[table] = int(current_rows * retention_ratio)

        return retained

    def _storage_from_rows(self, row_counts: Dict[str, int]) -> float:
        """Calculate storage in GB from row counts."""
        total_bytes = sum(
            rows * self.TABLE_METADATA[table][0]
            for table, rows in row_counts.items()
            if table in self.TABLE_METADATA
        )
        return total_bytes / (1024 ** 3)
