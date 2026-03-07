"""
Progressive Delivery Canary Automation Module

This module provides automated canary deployment capabilities for progressive delivery,
enabling safe rollouts with traffic splitting, health monitoring, and automated rollback.

Features:
- Canary deployment configuration and management
- Traffic splitting and weight adjustment
- Health metrics monitoring and analysis
- Automated promotion and rollback
- A/B testing integration
- Rollout strategies (linear, exponential, custom)
"""

import asyncio
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class CanaryStatus(str, Enum):
    """Canary deployment status."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    ANALYZING = "analyzing"
    PROMOTING = "promoting"
    PROMOTED = "promoted"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    PAUSED = "paused"


class RolloutStrategy(str, Enum):
    """Traffic rollout strategy."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    CUSTOM = "custom"
    ALL_AT_ONCE = "all_at_once"


class MetricOperator(str, Enum):
    """Metric comparison operators."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN_OR_EQUALS = ">="
    LESS_THAN_OR_EQUALS = "<="


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CanaryStep:
    """Single step in canary rollout."""
    step_number: int
    canary_weight: int  # 0-100
    duration_minutes: int
    metrics_thresholds: Dict[str, Any] = field(default_factory=dict)
    automated_analysis: bool = True
    pause_after: bool = False


@dataclass
class MetricThreshold:
    """Metric threshold for health evaluation."""
    metric_name: str
    operator: MetricOperator
    threshold_value: float
    baseline_comparison: bool = False  # Compare against baseline
    tolerance_percentage: Optional[float] = None  # For baseline comparison
    duration_minutes: int = 5  # Duration to evaluate


@dataclass
class HealthMetric:
    """Health metric data point."""
    metric_name: str
    timestamp: datetime
    canary_value: float
    baseline_value: Optional[float] = None
    unit: Optional[str] = None
    status: HealthStatus = HealthStatus.UNKNOWN


@dataclass
class CanaryDeployment:
    """Canary deployment configuration and state."""
    canary_id: str
    name: str
    description: str
    service_name: str
    namespace: str = "default"
    
    # Version info
    canary_version: str
    baseline_version: str
    
    # Status
    status: CanaryStatus
    status_message: Optional[str] = None
    
    # Rollout configuration
    strategy: RolloutStrategy = RolloutStrategy.LINEAR
    steps: List[CanaryStep] = field(default_factory=list)
    current_step: int = 0
    
    # Traffic split
    canary_weight: int = 0
    baseline_weight: int = 100
    
    # Health monitoring
    metric_thresholds: List[MetricThreshold] = field(default_factory=list)
    health_metrics: List[HealthMetric] = field(default_factory=list)
    
    # Automated actions
    auto_promote: bool = False
    auto_rollback: bool = True
    rollback_on_degraded: bool = True
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Analysis results
    analysis_result: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    
    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class TrafficSplit:
    """Traffic split configuration."""
    split_id: str
    canary_id: str
    service_name: str
    canary_percentage: float
    baseline_percentage: float
    applied_at: datetime = field(default_factory=datetime.utcnow)
    applied_by: Optional[str] = None


@dataclass
class RollbackConfig:
    """Rollback configuration."""
    rollback_id: str
    canary_id: str
    trigger: str  # manual, automatic, health_check
    reason: str
    initiated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, completed, failed


@dataclass
class CanaryAnalysis:
    """Canary deployment analysis result."""
    analysis_id: str
    canary_id: str
    step_number: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Metrics comparison
    metrics_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Decision
    recommendation: str = "continue"  # continue, pause, rollback, promote
    confidence_score: float = 0.0  # 0-1
    
    # Issues found
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeploymentEvent:
    """Canary deployment event."""
    event_id: str
    canary_id: str
    event_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical


class RolloutStrategyCalculator:
    """Calculator for rollout step weights."""
    
    @staticmethod
    def calculate_linear_steps(
        num_steps: int,
        final_weight: int = 100
    ) -> List[int]:
        """Calculate weights for linear rollout strategy."""
        if num_steps <= 0:
            return [final_weight]
        
        step_size = final_weight / num_steps
        weights = []
        for i in range(1, num_steps + 1):
            weight = min(int(step_size * i), final_weight)
            weights.append(weight)
        
        return weights
    
    @staticmethod
    def calculate_exponential_steps(
        num_steps: int,
        final_weight: int = 100,
        base: float = 2.0
    ) -> List[int]:
        """Calculate weights for exponential rollout strategy."""
        if num_steps <= 0:
            return [final_weight]
        
        weights = []
        for i in range(1, num_steps + 1):
            # Exponential growth: 2^1, 2^2, 2^3...
            weight = min(int(base ** i), final_weight)
            weights.append(weight)
        
        return weights
    
    @staticmethod
    def generate_steps(
        strategy: RolloutStrategy,
        num_steps: int,
        step_duration: int,
        custom_weights: Optional[List[int]] = None
    ) -> List[CanaryStep]:
        """Generate canary steps based on strategy."""
        if strategy == RolloutStrategy.LINEAR:
            weights = RolloutStrategyCalculator.calculate_linear_steps(num_steps)
        elif strategy == RolloutStrategy.EXPONENTIAL:
            weights = RolloutStrategyCalculator.calculate_exponential_steps(num_steps)
        elif strategy == RolloutStrategy.CUSTOM and custom_weights:
            weights = custom_weights
        elif strategy == RolloutStrategy.ALL_AT_ONCE:
            weights = [100]
            num_steps = 1
        else:
            weights = RolloutStrategyCalculator.calculate_linear_steps(num_steps)
        
        steps = []
        for i, weight in enumerate(weights, 1):
            step = CanaryStep(
                step_number=i,
                canary_weight=weight,
                duration_minutes=step_duration
            )
            steps.append(step)
        
        return steps


class HealthAnalyzer:
    """Analyzer for canary health metrics."""
    
    @staticmethod
    def evaluate_metric(
        metric: HealthMetric,
        threshold: MetricThreshold
    ) -> HealthStatus:
        """Evaluate a metric against its threshold."""
        value = metric.canary_value
        
        # Baseline comparison
        if threshold.baseline_comparison and metric.baseline_value is not None:
            baseline = metric.baseline_value
            tolerance = threshold.tolerance_percentage or 10.0
            
            # Calculate percentage difference
            if baseline != 0:
                diff_pct = abs((value - baseline) / baseline) * 100
            else:
                diff_pct = abs(value - baseline) * 100
            
            if diff_pct <= tolerance:
                return HealthStatus.HEALTHY
            elif diff_pct <= tolerance * 2:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.UNHEALTHY
        
        # Direct threshold comparison
        threshold_val = threshold.threshold_value
        op = threshold.operator
        
        if op == MetricOperator.GREATER_THAN:
            status = HealthStatus.HEALTHY if value > threshold_val else HealthStatus.UNHEALTHY
        elif op == MetricOperator.LESS_THAN:
            status = HealthStatus.HEALTHY if value < threshold_val else HealthStatus.UNHEALTHY
        elif op == MetricOperator.EQUALS:
            status = HealthStatus.HEALTHY if value == threshold_val else HealthStatus.UNHEALTHY
        elif op == MetricOperator.NOT_EQUALS:
            status = HealthStatus.HEALTHY if value != threshold_val else HealthStatus.UNHEALTHY
        elif op == MetricOperator.GREATER_THAN_OR_EQUALS:
            status = HealthStatus.HEALTHY if value >= threshold_val else HealthStatus.UNHEALTHY
        elif op == MetricOperator.LESS_THAN_OR_EQUALS:
            status = HealthStatus.HEALTHY if value <= threshold_val else HealthStatus.UNHEALTHY
        else:
            status = HealthStatus.UNKNOWN
        
        return status
    
    @staticmethod
    def analyze_deployment(
        canary: CanaryDeployment,
        metrics: List[HealthMetric]
    ) -> CanaryAnalysis:
        """Analyze canary deployment health."""
        analysis_id = f"analysis_{secrets.token_hex(8)}"
        
        issues = []
        warnings = []
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for metric in metrics:
            # Find matching threshold
            threshold = None
            for t in canary.metric_thresholds:
                if t.metric_name == metric.metric_name:
                    threshold = t
                    break
            
            if not threshold:
                continue
            
            # Evaluate
            status = HealthAnalyzer.evaluate_metric(metric, threshold)
            metric.status = status
            
            if status == HealthStatus.HEALTHY:
                healthy_count += 1
            elif status == HealthStatus.DEGRADED:
                degraded_count += 1
                warnings.append({
                    "metric": metric.metric_name,
                    "message": f"Metric {metric.metric_name} is degraded",
                    "value": metric.canary_value,
                    "baseline": metric.baseline_value
                })
            elif status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
                issues.append({
                    "metric": metric.metric_name,
                    "message": f"Metric {metric.metric_name} is unhealthy",
                    "value": metric.canary_value,
                    "baseline": metric.baseline_value
                })
        
        # Determine recommendation
        total_metrics = len([m for m in metrics if m.status != HealthStatus.UNKNOWN])
        
        if unhealthy_count > 0:
            recommendation = "rollback"
            confidence = min(0.9, unhealthy_count / max(total_metrics, 1))
        elif degraded_count > total_metrics * 0.3:  # > 30% degraded
            recommendation = "pause"
            confidence = min(0.7, degraded_count / max(total_metrics, 1))
        elif healthy_count == total_metrics:
            recommendation = "continue"
            confidence = 0.95
        else:
            recommendation = "continue"
            confidence = 0.7
        
        return CanaryAnalysis(
            analysis_id=analysis_id,
            canary_id=canary.canary_id,
            step_number=canary.current_step,
            recommendation=recommendation,
            confidence_score=confidence,
            issues=issues,
            warnings=warnings
        )


class CanaryDeploymentManager:
    """
    Central manager for canary deployments.
    
    Provides functionality for:
    - Canary deployment creation and configuration
    - Traffic splitting and weight management
    - Health monitoring and analysis
    - Automated promotion and rollback
    - Rollout strategy execution
    """
    
    def __init__(self):
        self.deployments: Dict[str, CanaryDeployment] = {}
        self.traffic_splits: Dict[str, TrafficSplit] = {}
        self.rollbacks: Dict[str, RollbackConfig] = {}
        self.events: List[DeploymentEvent] = []
        self.analyses: Dict[str, List[CanaryAnalysis]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the canary deployment manager."""
        async with self._lock:
            if self._initialized:
                return
            
            self._initialized = True
            logger.info("CanaryDeploymentManager initialized successfully")
    
    # Deployment Management
    
    async def create_deployment(
        self,
        name: str,
        description: str,
        service_name: str,
        canary_version: str,
        baseline_version: str,
        namespace: str = "default",
        strategy: RolloutStrategy = RolloutStrategy.LINEAR,
        num_steps: int = 5,
        step_duration_minutes: int = 10,
        custom_weights: Optional[List[int]] = None,
        auto_promote: bool = False,
        auto_rollback: bool = True
    ) -> CanaryDeployment:
        """Create a new canary deployment."""
        async with self._lock:
            canary_id = f"canary_{secrets.token_hex(8)}"
            
            # Generate steps
            steps = RolloutStrategyCalculator.generate_steps(
                strategy=strategy,
                num_steps=num_steps,
                step_duration=step_duration_minutes,
                custom_weights=custom_weights
            )
            
            canary = CanaryDeployment(
                canary_id=canary_id,
                name=name,
                description=description,
                service_name=service_name,
                namespace=namespace,
                canary_version=canary_version,
                baseline_version=baseline_version,
                status=CanaryStatus.PENDING,
                strategy=strategy,
                steps=steps,
                auto_promote=auto_promote,
                auto_rollback=auto_rollback
            )
            
            self.deployments[canary_id] = canary
            
            await self._log_event(
                canary_id=canary_id,
                event_type="created",
                message=f"Canary deployment created: {name}"
            )
            
            logger.info(f"Created canary deployment: {canary_id}")
            return canary
    
    async def start_deployment(self, canary_id: str) -> Optional[CanaryDeployment]:
        """Start a canary deployment."""
        async with self._lock:
            canary = self.deployments.get(canary_id)
            if not canary:
                return None
            
            if canary.status != CanaryStatus.PENDING:
                return None
            
            canary.status = CanaryStatus.INITIALIZING
            canary.started_at = datetime.utcnow()
            canary.current_step = 1
            
            # Set initial traffic split
            first_step = canary.steps[0] if canary.steps else None
            if first_step:
                canary.canary_weight = first_step.canary_weight
                canary.baseline_weight = 100 - first_step.canary_weight
            
            await self._log_event(
                canary_id=canary_id,
                event_type="started",
                message="Canary deployment started"
            )
            
            canary.status = CanaryStatus.RUNNING
            logger.info(f"Started canary deployment: {canary_id}")
            return canary
    
    async def get_deployment(self, canary_id: str) -> Optional[CanaryDeployment]:
        """Get a canary deployment by ID."""
        return self.deployments.get(canary_id)
    
    async def list_deployments(
        self,
        service_name: Optional[str] = None,
        status: Optional[CanaryStatus] = None
    ) -> List[CanaryDeployment]:
        """List canary deployments."""
        deployments = list(self.deployments.values())
        
        if service_name:
            deployments = [d for d in deployments if d.service_name == service_name]
        if status:
            deployments = [d for d in deployments if d.status == status]
        
        return sorted(deployments, key=lambda d: d.created_at, reverse=True)
    
    # Traffic Management
    
    async def update_traffic_split(
        self,
        canary_id: str,
        canary_percentage: float,
        applied_by: Optional[str] = None
    ) -> Optional[TrafficSplit]:
        """Update traffic split for a canary deployment."""
        async with self._lock:
            canary = self.deployments.get(canary_id)
            if not canary:
                return None
            
            split_id = f"split_{secrets.token_hex(8)}"
            
            split = TrafficSplit(
                split_id=split_id,
                canary_id=canary_id,
                service_name=canary.service_name,
                canary_percentage=canary_percentage,
                baseline_percentage=100 - canary_percentage,
                applied_by=applied_by
            )
            
            self.traffic_splits[split_id] = split
            
            # Update canary weights
            canary.canary_weight = int(canary_percentage)
            canary.baseline_weight = int(100 - canary_percentage)
            
            await self._log_event(
                canary_id=canary_id,
                event_type="traffic_split_updated",
                message=f"Traffic split updated: canary={canary_percentage}%, baseline={100-canary_percentage}%",
                details={"canary_percentage": canary_percentage}
            )
            
            logger.info(f"Updated traffic split for {canary_id}: {canary_percentage}%")
            return split
    
    # Step Management
    
    async def advance_step(self, canary_id: str) -> Optional[CanaryDeployment]:
        """Advance to the next canary step."""
        async with self._lock:
            canary = self.deployments.get(canary_id)
            if not canary:
                return None
            
            if canary.status != CanaryStatus.RUNNING:
                return None
            
            if canary.current_step >= len(canary.steps):
                # All steps completed
                if canary.auto_promote:
                    return await self.promote_deployment(canary_id)
                return canary
            
            canary.current_step += 1
            step = canary.steps[canary.current_step - 1]
            
            # Update traffic split
            canary.canary_weight = step.canary_weight
            canary.baseline_weight = 100 - step.canary_weight
            
            await self._log_event(
                canary_id=canary_id,
                event_type="step_advanced",
                message=f"Advanced to step {canary.current_step}: canary weight {step.canary_weight}%",
                details={"step": canary.current_step, "canary_weight": step.canary_weight}
            )
            
            logger.info(f"Advanced canary {canary_id} to step {canary.current_step}")
            return canary
    
    # Health Monitoring
    
    async def record_metric(
        self,
        canary_id: str,
        metric_name: str,
        canary_value: float,
        baseline_value: Optional[float] = None,
        unit: Optional[str] = None
    ) -> HealthMetric:
        """Record a health metric."""
        canary = self.deployments.get(canary_id)
        if not canary:
            raise ValueError(f"Canary deployment not found: {canary_id}")
        
        metric = HealthMetric(
            metric_name=metric_name,
            timestamp=datetime.utcnow(),
            canary_value=canary_value,
            baseline_value=baseline_value,
            unit=unit
        )
        
        canary.health_metrics.append(metric)
        
        # Keep only last 1000 metrics per canary
        if len(canary.health_metrics) > 1000:
            canary.health_metrics = canary.health_metrics[-1000:]
        
        return metric
    
    async def analyze_health(
        self,
        canary_id: str
    ) -> Optional[CanaryAnalysis]:
        """Analyze canary deployment health."""
        canary = self.deployments.get(canary_id)
        if not canary:
            return None
        
        # Get recent metrics
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        recent_metrics = [
            m for m in canary.health_metrics
            if m.timestamp >= cutoff
        ]
        
        analysis = HealthAnalyzer.analyze_deployment(canary, recent_metrics)
        
        self.analyses[canary_id].append(analysis)
        canary.analysis_result = {
            "recommendation": analysis.recommendation,
            "confidence": analysis.confidence_score,
            "issues_count": len(analysis.issues),
            "warnings_count": len(analysis.warnings)
        }
        
        # Auto-rollback if unhealthy
        if analysis.recommendation == "rollback" and canary.auto_rollback:
            await self.rollback_deployment(
                canary_id,
                reason="Automated rollback due to health issues",
                trigger="health_check"
            )
        
        await self._log_event(
            canary_id=canary_id,
            event_type="health_analyzed",
            message=f"Health analysis: {analysis.recommendation} (confidence: {analysis.confidence_score:.2f})",
            details={
                "recommendation": analysis.recommendation,
                "confidence": analysis.confidence_score,
                "issues": len(analysis.issues)
            }
        )
        
        return analysis
    
    # Promotion and Rollback
    
    async def promote_deployment(
        self,
        canary_id: str,
        promoted_by: Optional[str] = None
    ) -> Optional[CanaryDeployment]:
        """Promote canary to full deployment."""
        async with self._lock:
            canary = self.deployments.get(canary_id)
            if not canary:
                return None
            
            canary.status = CanaryStatus.PROMOTING
            
            # Set 100% traffic to canary
            canary.canary_weight = 100
            canary.baseline_weight = 0
            
            canary.status = CanaryStatus.PROMOTED
            canary.completed_at = datetime.utcnow()
            
            await self._log_event(
                canary_id=canary_id,
                event_type="promoted",
                message="Canary deployment promoted to full rollout",
                details={"promoted_by": promoted_by}
            )
            
            logger.info(f"Promoted canary deployment: {canary_id}")
            return canary
    
    async def rollback_deployment(
        self,
        canary_id: str,
        reason: str,
        trigger: str = "manual"
    ) -> Optional[CanaryDeployment]:
        """Rollback canary deployment."""
        async with self._lock:
            canary = self.deployments.get(canary_id)
            if not canary:
                return None
            
            canary.status = CanaryStatus.ROLLING_BACK
            
            # Create rollback config
            rollback_id = f"rollback_{secrets.token_hex(8)}"
            rollback = RollbackConfig(
                rollback_id=rollback_id,
                canary_id=canary_id,
                trigger=trigger,
                reason=reason
            )
            self.rollbacks[rollback_id] = rollback
            
            # Set 100% traffic to baseline
            canary.canary_weight = 0
            canary.baseline_weight = 100
            
            canary.status = CanaryStatus.ROLLED_BACK
            canary.completed_at = datetime.utcnow()
            canary.failure_reason = reason
            
            rollback.status = "completed"
            rollback.completed_at = datetime.utcnow()
            
            await self._log_event(
                canary_id=canary_id,
                event_type="rolled_back",
                message=f"Canary deployment rolled back: {reason}",
                details={"reason": reason, "trigger": trigger},
                severity="warning"
            )
            
            logger.warning(f"Rolled back canary deployment: {canary_id} - {reason}")
            return canary
    
    # Event Logging
    
    async def _log_event(
        self,
        canary_id: str,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ):
        """Log a deployment event."""
        event = DeploymentEvent(
            event_id=f"evt_{secrets.token_hex(8)}",
            canary_id=canary_id,
            event_type=event_type,
            message=message,
            details=details or {},
            severity=severity
        )
        
        self.events.append(event)
        
        # Keep only last 10,000 events
        if len(self.events) > 10000:
            self.events = self.events[-10000:]
    
    async def get_events(
        self,
        canary_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[DeploymentEvent]:
        """Query deployment events."""
        events = self.events
        
        if canary_id:
            events = [e for e in events if e.canary_id == canary_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get canary deployment statistics."""
        deployments = list(self.deployments.values())
        
        return {
            "deployments": {
                "total": len(deployments),
                "active": len([d for d in deployments if d.status == CanaryStatus.RUNNING]),
                "promoted": len([d for d in deployments if d.status == CanaryStatus.PROMOTED]),
                "rolled_back": len([d for d in deployments if d.status == CanaryStatus.ROLLED_BACK]),
                "failed": len([d for d in deployments if d.status == CanaryStatus.FAILED])
            },
            "by_strategy": {
                strategy.value: len([d for d in deployments if d.strategy == strategy])
                for strategy in RolloutStrategy
            },
            "rollbacks": len(self.rollbacks),
            "events": len(self.events)
        }


# Global manager instance
_canary_manager: Optional[CanaryDeploymentManager] = None


async def get_canary_manager() -> CanaryDeploymentManager:
    """Get or create the global canary manager."""
    global _canary_manager
    if _canary_manager is None:
        _canary_manager = CanaryDeploymentManager()
        await _canary_manager.initialize()
    return _canary_manager


def reset_canary_manager():
    """Reset the global canary manager (for testing)."""
    global _canary_manager
    _canary_manager = None
