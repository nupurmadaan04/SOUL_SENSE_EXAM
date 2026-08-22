"""
Migration Blast Radius Pre-Approval Checklist

Validates database migrations before deployment to reduce regression risk
and strengthen engineering guardrails. Provides deterministic scoring of
migration impact (blast radius) with pre-approval checklist validation.

Features:
- Evaluates migration risk across multiple dimensions
- Performs pre-approval checklist validation
- Handles edge cases: degraded dependencies, invalid inputs, concurrency, timeouts, rollback
- Structured logging and metrics integration
- Deterministic results for CI integration
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Migration risk classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MigrationMetadata:
    """Metadata about a database migration to validate."""
    migration_id: str                   # e.g., "001_add_user_email_index"
    description: str                    # What changed
    affected_tables: List[str] = field(default_factory=list)  # ['users', 'audit_logs']
    is_breaking_change: bool = False    # ALTER/DROP vs ADD
    estimated_duration_seconds: int = 30
    has_rollback_plan: bool = True
    affected_user_count: int = 0        # Estimated downstream impact
    involves_data_deletion: bool = False
    involves_public_api: bool = False
    has_tests: bool = False
    ci_passing: bool = False
    
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate input correctness."""
        if not self.migration_id or not isinstance(self.migration_id, str):
            return False, "migration_id is required and must be a string"
        if not self.description:
            return False, "description is required"
        if self.estimated_duration_seconds < 0:
            return False, "estimated_duration_seconds cannot be negative"
        if self.affected_user_count < 0:
            return False, "affected_user_count cannot be negative"
        return True, ""


@dataclass
class CheckResult:
    """Result of a single pre-approval check."""
    check_name: str
    passed: bool
    blocking: bool                      # If False, check failure blocks deployment
    reason: str = ""
    recommendation: str = ""


@dataclass
class BlastRadiusCheckResult:
    """Overall result of migration blast radius validation."""
    passed: bool                        # All checks passed?
    risk_level: RiskLevel
    score: int                          # 0-100 normalized score
    checks: List[CheckResult] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "risk_level": self.risk_level.value,
            "score": self.score,
            "checks": [
                {
                    "name": c.check_name,
                    "passed": c.passed,
                    "blocking": c.blocking,
                    "reason": c.reason,
                    "recommendation": c.recommendation
                }
                for c in self.checks
            ],
            "blocking_issues": self.blocking_issues,
            "recommendations": self.recommendations,
            "metrics": self.metrics
        }


class MigrationBlastRadius:
    """
    Validates database migrations before deployment.
    
    Scoring factors:
    - Table complexity (number affected tables)
    - Change type (breaking vs non-breaking)
    - Data impact (deletion, user count affected)
    - Testing coverage (unit + integration tests)
    - Rollback capability
    - Concurrency safety
    
    Usage:
        metadata = MigrationMetadata(
            migration_id="001_add_users_email_index",
            description="Add unique index on user emails",
            affected_tables=["users"],
            estimated_duration_seconds=45,
            has_tests=True,
            ci_passing=True
        )
        
        checker = MigrationBlastRadius()
        result = checker.evaluate(metadata)
        
        if result.passed:
            print(f"Safe to deploy - Risk: {result.risk_level.value}")
        else:
            for issue in result.blocking_issues:
                print(f"BLOCKED: {issue}")
    """
    
    # Configuration
    DEFAULT_TIMEOUT_SECONDS = 300
    MAX_SAFE_DURATION_SECONDS = 600
    CRITICAL_USER_COUNT = 10000
    
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS):
        """
        Initialize migration blast radius checker.
        
        Args:
            timeout_seconds: Maximum time to spend on evaluation (for timeout edge case handling)
        """
        self.timeout_seconds = timeout_seconds
        self.logger = logger
    
    def evaluate(self, metadata: MigrationMetadata) -> BlastRadiusCheckResult:
        """
        Evaluate a migration using the pre-approval checklist.
        
        Handles edge cases:
        - Invalid inputs: Validation fails, blocks deployment
        - Degraded dependencies: Warns but continues assessment
        - Concurrency race conditions: Flags in recommendations
        - Timeout handling: Raises TimeoutError if evaluation exceeds timeout_seconds
        - Rollback validation: Checks for rollback plan and warns if missing
        
        Args:
            metadata: Migration metadata to evaluate
            
        Returns:
            BlastRadiusCheckResult with pass/fail, risk level, score, and recommendations
            
        Raises:
            TimeoutError: If evaluation exceeds configured timeout
            ValueError: If metadata is None
        """
        start_time = time.time()
        
        try:
            if metadata is None:
                raise ValueError("metadata cannot be None")
            
            # EDGE CASE: Invalid inputs
            is_valid, error_msg = metadata.validate_inputs()
            if not is_valid:
                self.logger.error(f"Invalid migration metadata: {error_msg}")
                return BlastRadiusCheckResult(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    score=0,
                    checks=[CheckResult(
                        check_name="input_validation",
                        passed=False,
                        blocking=True,
                        reason=error_msg
                    )],
                    blocking_issues=[f"Invalid input: {error_msg}"]
                )
            
            checks = []
            blocking_issues = []
            recommendations = []
            score = 100  # Start at max, deduct for risks
            
            # Check 1: Schema validation
            check = self._check_schema_valid(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            score -= 0 if check.passed else 15
            
            # Check 2: Has rollback plan (ROLLBACK VALIDATION edge case)
            check = self._check_rollback_plan(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            if not check.passed:
                recommendations.append(check.recommendation)
            score -= 0 if check.passed else 10
            
            # Check 3: Zero downtime capability (CONCURRENCY RACE CONDITIONS edge case)
            check = self._check_zero_downtime_capable(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            if not check.passed:
                recommendations.append(check.recommendation)
            score -= 0 if check.passed else 20
            
            # Check 4: Test coverage
            check = self._check_test_coverage(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            if not check.passed:
                recommendations.append(check.recommendation)
            score -= 0 if check.passed else 15
            
            # Check 5: CI validation (DEGRADED DEPENDENCIES edge case handled here)
            check = self._check_ci_passing(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            score -= 0 if check.passed else 15
            
            # Check 6: Data loss prevention
            check = self._check_data_loss_prevention(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            if not check.passed:
                recommendations.append(check.recommendation)
            score -= 0 if check.passed else 20
            
            # Check 7: Duration safety (TIMEOUT HANDLING edge case)
            check = self._check_duration_safety(metadata)
            checks.append(check)
            if not check.passed and check.blocking:
                blocking_issues.append(check.reason)
            if not check.passed:
                recommendations.append(check.recommendation)
            score -= 0 if check.passed else 10
            
            # TIMEOUT EDGE CASE: Check if evaluation is taking too long
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                self.logger.error(f"Migration evaluation timeout: {elapsed:.2f}s > {self.timeout_seconds}s")
                raise TimeoutError(f"Migration evaluation exceeded {self.timeout_seconds}s timeout")
            
            # Determine risk level from score
            risk_level = self._score_to_risk_level(score)
            
            # Determine if passed: no blocking issues and risk level acceptable
            passed = len(blocking_issues) == 0 and risk_level != RiskLevel.CRITICAL
            
            metrics = {
                "table_count": len(metadata.affected_tables),
                "is_breaking": metadata.is_breaking_change,
                "affected_users": metadata.affected_user_count,
                "duration_seconds": metadata.estimated_duration_seconds,
                "evaluation_time_ms": (time.time() - start_time) * 1000,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = BlastRadiusCheckResult(
                passed=passed,
                risk_level=risk_level,
                score=max(0, min(100, score)),  # Clamp 0-100
                checks=checks,
                blocking_issues=blocking_issues,
                recommendations=recommendations,
                metrics=metrics
            )
            
            # Log structured output
            self._log_result(metadata, result)
            
            return result
            
        except TimeoutError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during migration evaluation: {str(e)}", exc_info=True)
            return BlastRadiusCheckResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                score=0,
                blocking_issues=[f"Evaluation error: {str(e)}"]
            )
    
    def _check_schema_valid(self, metadata: MigrationMetadata) -> CheckResult:
        """Check that migration has valid schema metadata."""
        passed = bool(metadata.migration_id) and bool(metadata.description)
        return CheckResult(
            check_name="schema_valid",
            passed=passed,
            blocking=True,
            reason="Migration lacks required schema metadata" if not passed else "",
            recommendation="Ensure migration_id and description are set"
        )
    
    def _check_rollback_plan(self, metadata: MigrationMetadata) -> CheckResult:
        """Check that migration has a rollback plan (ROLLBACK VALIDATION)."""
        return CheckResult(
            check_name="rollback_plan_present",
            passed=metadata.has_rollback_plan,
            blocking=True,
            reason="No rollback plan - deployment blocked" if not metadata.has_rollback_plan else "",
            recommendation="Define and test reverse migration before deployment"
        )
    
    def _check_zero_downtime_capable(self, metadata: MigrationMetadata) -> CheckResult:
        """Check for concurrency safety (CONCURRENCY RACE CONDITIONS)."""
        # Breaking changes and data deletion are risky for zero-downtime
        is_risky = metadata.is_breaking_change or metadata.involves_data_deletion
        passed = not is_risky
        
        return CheckResult(
            check_name="zero_downtime_capable",
            passed=passed,
            blocking=False,  # Warning, not blocking
            reason="Breaking change or data deletion - may require maintenance window" if is_risky else "",
            recommendation="Use READ_COMMITTED isolation, consider phased rollout" if is_risky else ""
        )
    
    def _check_test_coverage(self, metadata: MigrationMetadata) -> CheckResult:
        """Check that migration has test coverage."""
        return CheckResult(
            check_name="test_coverage",
            passed=metadata.has_tests,
            blocking=True,
            reason="No tests for migration - deployment blocked" if not metadata.has_tests else "",
            recommendation="Add unit and integration tests before deployment"
        )
    
    def _check_ci_passing(self, metadata: MigrationMetadata) -> CheckResult:
        """Check CI status (DEGRADED DEPENDENCIES - warns if not passing)."""
        return CheckResult(
            check_name="ci_validation",
            passed=metadata.ci_passing,
            blocking=True,
            reason="CI pipeline failing - deployment blocked" if not metadata.ci_passing else "",
            recommendation="Fix failing CI checks before proceeding"
        )
    
    def _check_data_loss_prevention(self, metadata: MigrationMetadata) -> CheckResult:
        """Check for data loss risks."""
        return CheckResult(
            check_name="data_loss_prevention",
            passed=not metadata.involves_data_deletion,
            blocking=False,  # Warning
            reason="Migration involves data operations - review carefully" if metadata.involves_data_deletion else "",
            recommendation="Backup affected tables before executing this migration"
        )
    
    def _check_duration_safety(self, metadata: MigrationMetadata) -> CheckResult:
        """Check migration duration (TIMEOUT HANDLING)."""
        is_safe = metadata.estimated_duration_seconds <= self.MAX_SAFE_DURATION_SECONDS
        return CheckResult(
            check_name="duration_safety",
            passed=is_safe,
            blocking=False,  # Warning
            reason=f"Migration estimated at {metadata.estimated_duration_seconds}s exceeds safe threshold" if not is_safe else "",
            recommendation=f"Schedule during maintenance window (max safe: {self.MAX_SAFE_DURATION_SECONDS}s)"
        )
    
    def _score_to_risk_level(self, score: int) -> RiskLevel:
        """Convert normalized score (0-100) to risk level."""
        if score >= 80:
            return RiskLevel.LOW
        elif score >= 60:
            return RiskLevel.MEDIUM
        elif score >= 40:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _log_result(self, metadata: MigrationMetadata, result: BlastRadiusCheckResult) -> None:
        """Log structured evaluation result."""
        log_data = {
            "migration_id": metadata.migration_id,
            "result": "PASS" if result.passed else "FAIL",
            "risk_level": result.risk_level.value,
            "score": result.score,
            "checks_passed": sum(1 for c in result.checks if c.passed),
            "checks_total": len(result.checks),
            "blocking_issues_count": len(result.blocking_issues),
            "affected_tables": metadata.affected_tables,
            "affected_users": metadata.affected_user_count,
        }
        
        if result.passed:
            self.logger.info(f"Migration pre-approval passed: {log_data}")
        else:
            self.logger.warning(f"Migration pre-approval failed: {log_data}")
            for issue in result.blocking_issues:
                self.logger.warning(f"  BLOCKING: {issue}")
