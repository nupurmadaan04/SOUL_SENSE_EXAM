"""
Usage-Based Pricing Telemetry Foundations Module

This module provides usage tracking, metering, and telemetry collection
for usage-based pricing models. Supports event tracking, aggregation,
billing periods, and cost calculation.

Features:
- Usage event tracking and ingestion
- Metering and aggregation
- Billing period management
- Cost calculation
- Usage quotas and limits
- Real-time and batch processing
- Export to billing systems
"""

import asyncio
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import logging

# Configure logging
logger = logging.getLogger(__name__)


class UsageEventType(str, Enum):
    """Types of usage events."""
    API_CALL = "api_call"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    COMPUTE = "compute"
    DATABASE_QUERY = "database_query"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    REPORT_GENERATION = "report_generation"
    EMAIL_SENT = "email_sent"
    SMS_SENT = "sms_sent"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class AggregationType(str, Enum):
    """Types of aggregation."""
    SUM = "sum"
    COUNT = "count"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    UNIQUE_COUNT = "unique_count"


class BillingPeriodStatus(str, Enum):
    """Billing period status."""
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    INVOICED = "invoiced"
    PAID = "paid"


class PricingTierType(str, Enum):
    """Pricing tier types."""
    FLAT = "flat"
    VOLUME = "volume"
    TIERED = "tiered"
    STAIRSTEP = "stairstep"


@dataclass
class UsageEvent:
    """Individual usage event."""
    event_id: str
    event_type: UsageEventType
    customer_id: str
    timestamp: datetime
    quantity: Decimal
    unit: str
    properties: Dict[str, Any] = field(default_factory=dict)
    meter_name: Optional[str] = None
    resource_id: Optional[str] = None
    region: Optional[str] = None
    environment: Optional[str] = None
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    received_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    checksum: Optional[str] = None


@dataclass
class Meter:
    """Usage meter definition."""
    meter_id: str
    name: str
    description: str
    event_type: UsageEventType
    aggregation_type: AggregationType
    unit: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    properties_filter: Dict[str, Any] = field(default_factory=dict)
    custom_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PricingTier:
    """Pricing tier for a meter."""
    tier_id: str
    meter_id: str
    tier_type: PricingTierType
    unit_price: Decimal
    currency: str = "USD"
    min_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    flat_fee: Optional[Decimal] = None
    is_active: bool = True


@dataclass
class BillingPeriod:
    """Billing period for a customer."""
    period_id: str
    customer_id: str
    start_date: datetime
    end_date: datetime
    status: BillingPeriodStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    invoiced_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    total_amount: Decimal = field(default_factory=lambda: Decimal("0.00"))
    currency: str = "USD"
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageAggregation:
    """Aggregated usage data."""
    aggregation_id: str
    meter_id: str
    customer_id: str
    billing_period_id: str
    start_time: datetime
    end_time: datetime
    aggregation_type: AggregationType
    total_quantity: Decimal
    unit: str
    event_count: int
    calculated_cost: Optional[Decimal] = None
    currency: Optional[str] = None


@dataclass
class UsageQuota:
    """Usage quota/limit for a customer."""
    quota_id: str
    customer_id: str
    meter_id: str
    limit_quantity: Decimal
    period_type: str  # daily, weekly, monthly, yearly
    current_usage: Decimal = field(default_factory=lambda: Decimal("0"))
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    is_hard_limit: bool = False
    alert_threshold: Optional[Decimal] = None  # Percentage (0-100)
    alert_triggered: bool = False


@dataclass
class TelemetryBatch:
    """Batch of telemetry events for processing."""
    batch_id: str
    events: List[UsageEvent]
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None


class UsageEventValidator:
    """Validator for usage events."""
    
    REQUIRED_FIELDS = ["event_type", "customer_id", "quantity", "unit"]
    
    @classmethod
    def validate(cls, event_data: Dict[str, Any]) -> List[str]:
        """Validate usage event data."""
        errors = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in event_data or event_data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate quantity is positive
        if "quantity" in event_data:
            try:
                qty = Decimal(str(event_data["quantity"]))
                if qty < 0:
                    errors.append("Quantity must be non-negative")
            except Exception:
                errors.append("Invalid quantity format")
        
        # Validate event type
        if "event_type" in event_data:
            try:
                UsageEventType(event_data["event_type"])
            except ValueError:
                errors.append(f"Invalid event_type: {event_data['event_type']}")
        
        return errors
    
    @classmethod
    def calculate_checksum(cls, event: UsageEvent) -> str:
        """Calculate checksum for event integrity."""
        data = {
            "event_type": event.event_type.value,
            "customer_id": event.customer_id,
            "timestamp": event.timestamp.isoformat(),
            "quantity": str(event.quantity),
            "unit": event.unit,
            "meter_name": event.meter_name
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class CostCalculator:
    """Calculator for usage costs."""
    
    @staticmethod
    def calculate_flat_pricing(quantity: Decimal, unit_price: Decimal) -> Decimal:
        """Calculate cost with flat pricing."""
        return (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def calculate_volume_pricing(
        quantity: Decimal,
        tiers: List[PricingTier]
    ) -> Decimal:
        """Calculate cost with volume pricing (entire quantity at tier price)."""
        # Sort tiers by min_quantity
        sorted_tiers = sorted(tiers, key=lambda t: t.min_quantity or Decimal("0"))
        
        # Find applicable tier
        for tier in sorted_tiers:
            min_qty = tier.min_quantity or Decimal("0")
            max_qty = tier.max_quantity or Decimal("Infinity")
            
            if min_qty <= quantity <= max_qty:
                cost = quantity * tier.unit_price
                if tier.flat_fee:
                    cost += tier.flat_fee
                return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        # Default to highest tier
        if sorted_tiers:
            highest = sorted_tiers[-1]
            cost = quantity * highest.unit_price
            if highest.flat_fee:
                cost += highest.flat_fee
            return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return Decimal("0.00")
    
    @staticmethod
    def calculate_tiered_pricing(
        quantity: Decimal,
        tiers: List[PricingTier]
    ) -> Decimal:
        """Calculate cost with tiered pricing (progressive tiers)."""
        sorted_tiers = sorted(tiers, key=lambda t: t.min_quantity or Decimal("0"))
        
        total_cost = Decimal("0")
        remaining = quantity
        
        for tier in sorted_tiers:
            if remaining <= 0:
                break
            
            min_qty = tier.min_quantity or Decimal("0")
            max_qty = tier.max_quantity or Decimal("Infinity")
            
            tier_range = max_qty - min_qty
            tier_quantity = min(remaining, tier_range)
            
            tier_cost = tier_quantity * tier.unit_price
            if tier.flat_fee and tier_quantity > 0:
                tier_cost += tier.flat_fee
            
            total_cost += tier_cost
            remaining -= tier_quantity
        
        return total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class UsageTelemetryManager:
    """
    Central manager for usage telemetry operations.
    
    Provides functionality for:
    - Usage event ingestion
    - Meter management
    - Pricing configuration
    - Billing period management
    - Usage aggregation
    - Cost calculation
    - Quota management
    """
    
    def __init__(self):
        self.events: List[UsageEvent] = []
        self.meters: Dict[str, Meter] = {}
        self.pricing_tiers: Dict[str, List[PricingTier]] = defaultdict(list)
        self.billing_periods: Dict[str, BillingPeriod] = {}
        self.customer_periods: Dict[str, List[str]] = defaultdict(list)
        self.aggregations: Dict[str, UsageAggregation] = {}
        self.quotas: Dict[str, UsageQuota] = {}
        self.customer_quotas: Dict[str, List[str]] = defaultdict(list)
        self.batches: Dict[str, TelemetryBatch] = {}
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the telemetry manager."""
        async with self._lock:
            if self._initialized:
                return
            
            # Create default meters
            await self._create_default_meters()
            
            self._initialized = True
            logger.info("UsageTelemetryManager initialized successfully")
    
    async def _create_default_meters(self):
        """Create default usage meters."""
        default_meters = [
            {
                "name": "API Calls",
                "description": "Number of API calls made",
                "event_type": UsageEventType.API_CALL,
                "aggregation_type": AggregationType.COUNT,
                "unit": "requests"
            },
            {
                "name": "Storage",
                "description": "Storage space used",
                "event_type": UsageEventType.STORAGE,
                "aggregation_type": AggregationType.SUM,
                "unit": "GB"
            },
            {
                "name": "Bandwidth",
                "description": "Data transfer",
                "event_type": UsageEventType.BANDWIDTH,
                "aggregation_type": AggregationType.SUM,
                "unit": "GB"
            }
        ]
        
        for meter_data in default_meters:
            await self.create_meter(**meter_data)
    
    # Meter Management
    
    async def create_meter(
        self,
        name: str,
        description: str,
        event_type: UsageEventType,
        aggregation_type: AggregationType,
        unit: str,
        properties_filter: Optional[Dict[str, Any]] = None
    ) -> Meter:
        """Create a new usage meter."""
        async with self._lock:
            meter_id = f"meter_{uuid.uuid4().hex[:12]}"
            
            meter = Meter(
                meter_id=meter_id,
                name=name,
                description=description,
                event_type=event_type,
                aggregation_type=aggregation_type,
                unit=unit,
                properties_filter=properties_filter or {}
            )
            
            self.meters[meter_id] = meter
            logger.info(f"Created meter: {meter_id}")
            return meter
    
    async def get_meter(self, meter_id: str) -> Optional[Meter]:
        """Get a meter by ID."""
        return self.meters.get(meter_id)
    
    async def list_meters(
        self,
        event_type: Optional[UsageEventType] = None,
        active_only: bool = True
    ) -> List[Meter]:
        """List usage meters."""
        meters = list(self.meters.values())
        
        if event_type:
            meters = [m for m in meters if m.event_type == event_type]
        if active_only:
            meters = [m for m in meters if m.is_active]
        
        return meters
    
    # Pricing Management
    
    async def create_pricing_tier(
        self,
        meter_id: str,
        tier_type: PricingTierType,
        unit_price: Decimal,
        currency: str = "USD",
        min_quantity: Optional[Decimal] = None,
        max_quantity: Optional[Decimal] = None,
        flat_fee: Optional[Decimal] = None
    ) -> Optional[PricingTier]:
        """Create a pricing tier for a meter."""
        async with self._lock:
            if meter_id not in self.meters:
                return None
            
            tier_id = f"tier_{uuid.uuid4().hex[:12]}"
            
            tier = PricingTier(
                tier_id=tier_id,
                meter_id=meter_id,
                tier_type=tier_type,
                unit_price=unit_price,
                currency=currency,
                min_quantity=min_quantity,
                max_quantity=max_quantity,
                flat_fee=flat_fee
            )
            
            self.pricing_tiers[meter_id].append(tier)
            logger.info(f"Created pricing tier: {tier_id} for meter: {meter_id}")
            return tier
    
    async def get_pricing_tiers(self, meter_id: str) -> List[PricingTier]:
        """Get pricing tiers for a meter."""
        return [t for t in self.pricing_tiers.get(meter_id, []) if t.is_active]
    
    # Event Ingestion
    
    async def ingest_event(
        self,
        event_type: UsageEventType,
        customer_id: str,
        quantity: Decimal,
        unit: str,
        timestamp: Optional[datetime] = None,
        meter_name: Optional[str] = None,
        resource_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        region: Optional[str] = None,
        environment: Optional[str] = None
    ) -> UsageEvent:
        """Ingest a usage event."""
        async with self._lock:
            event_id = f"evt_{uuid.uuid4().hex[:16]}"
            
            event = UsageEvent(
                event_id=event_id,
                event_type=event_type,
                customer_id=customer_id,
                timestamp=timestamp or datetime.utcnow(),
                quantity=Decimal(str(quantity)),
                unit=unit,
                meter_name=meter_name,
                resource_id=resource_id,
                properties=properties or {},
                region=region,
                environment=environment
            )
            
            # Calculate checksum
            event.checksum = UsageEventValidator.calculate_checksum(event)
            
            # Check quota
            await self._check_quota(event)
            
            self.events.append(event)
            
            # Keep only last 100,000 events
            if len(self.events) > 100000:
                self.events = self.events[-100000:]
            
            logger.debug(f"Ingested event: {event_id}")
            return event
    
    async def ingest_batch(
        self,
        events_data: List[Dict[str, Any]]
    ) -> TelemetryBatch:
        """Ingest a batch of events."""
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        valid_events = []
        errors = []
        
        for idx, event_data in enumerate(events_data):
            # Validate
            validation_errors = UsageEventValidator.validate(event_data)
            if validation_errors:
                errors.append({"index": idx, "errors": validation_errors})
                continue
            
            # Create event
            try:
                event = await self.ingest_event(
                    event_type=UsageEventType(event_data["event_type"]),
                    customer_id=event_data["customer_id"],
                    quantity=Decimal(str(event_data["quantity"])),
                    unit=event_data["unit"],
                    timestamp=event_data.get("timestamp"),
                    meter_name=event_data.get("meter_name"),
                    resource_id=event_data.get("resource_id"),
                    properties=event_data.get("properties"),
                    region=event_data.get("region"),
                    environment=event_data.get("environment")
                )
                valid_events.append(event)
            except Exception as e:
                errors.append({"index": idx, "errors": [str(e)]})
        
        batch = TelemetryBatch(
            batch_id=batch_id,
            events=valid_events,
            status="completed" if not errors else "partial"
        )
        
        self.batches[batch_id] = batch
        
        logger.info(f"Batch {batch_id}: {len(valid_events)} events ingested, {len(errors)} errors")
        return batch
    
    async def _check_quota(self, event: UsageEvent):
        """Check if event exceeds quota."""
        customer_quotas = self.customer_quotas.get(event.customer_id, [])
        
        for quota_id in customer_quotas:
            quota = self.quotas.get(quota_id)
            if not quota or not quota.meter_id:
                continue
            
            # Get meter for this quota
            meter = self.meters.get(quota.meter_id)
            if not meter or meter.event_type != event.event_type:
                continue
            
            # Check if in current period
            now = datetime.utcnow()
            if quota.period_start and quota.period_end:
                if not (quota.period_start <= now <= quota.period_end):
                    # Reset period
                    await self._reset_quota_period(quota)
            
            # Update usage
            quota.current_usage += event.quantity
            
            # Check threshold
            if quota.alert_threshold and not quota.alert_triggered:
                usage_pct = (quota.current_usage / quota.limit_quantity) * 100
                if usage_pct >= quota.alert_threshold:
                    quota.alert_triggered = True
                    logger.warning(f"Quota alert for {event.customer_id}: {usage_pct:.1f}%")
            
            # Check limit
            if quota.is_hard_limit and quota.current_usage > quota.limit_quantity:
                logger.error(f"Quota exceeded for {event.customer_id}")
                raise QuotaExceededError(f"Usage quota exceeded for meter {quota.meter_id}")
    
    async def _reset_quota_period(self, quota: UsageQuota):
        """Reset quota period."""
        now = datetime.utcnow()
        quota.period_start = now
        quota.current_usage = Decimal("0")
        quota.alert_triggered = False
        
        if quota.period_type == "daily":
            quota.period_end = now + timedelta(days=1)
        elif quota.period_type == "weekly":
            quota.period_end = now + timedelta(weeks=1)
        elif quota.period_type == "monthly":
            quota.period_end = now + timedelta(days=30)
        elif quota.period_type == "yearly":
            quota.period_end = now + timedelta(days=365)
    
    # Quota Management
    
    async def create_quota(
        self,
        customer_id: str,
        meter_id: str,
        limit_quantity: Decimal,
        period_type: str,
        is_hard_limit: bool = False,
        alert_threshold: Optional[Decimal] = None
    ) -> Optional[UsageQuota]:
        """Create a usage quota."""
        async with self._lock:
            if meter_id not in self.meters:
                return None
            
            quota_id = f"quota_{uuid.uuid4().hex[:12]}"
            
            now = datetime.utcnow()
            quota = UsageQuota(
                quota_id=quota_id,
                customer_id=customer_id,
                meter_id=meter_id,
                limit_quantity=Decimal(str(limit_quantity)),
                period_type=period_type,
                period_start=now,
                is_hard_limit=is_hard_limit,
                alert_threshold=alert_threshold
            )
            
            # Set period end
            if period_type == "daily":
                quota.period_end = now + timedelta(days=1)
            elif period_type == "weekly":
                quota.period_end = now + timedelta(weeks=1)
            elif period_type == "monthly":
                quota.period_end = now + timedelta(days=30)
            elif period_type == "yearly":
                quota.period_end = now + timedelta(days=365)
            
            self.quotas[quota_id] = quota
            self.customer_quotas[customer_id].append(quota_id)
            
            logger.info(f"Created quota: {quota_id} for customer: {customer_id}")
            return quota
    
    async def get_customer_quotas(self, customer_id: str) -> List[UsageQuota]:
        """Get quotas for a customer."""
        quota_ids = self.customer_quotas.get(customer_id, [])
        return [self.quotas[qid] for qid in quota_ids if qid in self.quotas]
    
    # Billing Period Management
    
    async def create_billing_period(
        self,
        customer_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> BillingPeriod:
        """Create a billing period."""
        async with self._lock:
            period_id = f"period_{uuid.uuid4().hex[:12]}"
            
            period = BillingPeriod(
                period_id=period_id,
                customer_id=customer_id,
                start_date=start_date,
                end_date=end_date,
                status=BillingPeriodStatus.OPEN
            )
            
            self.billing_periods[period_id] = period
            self.customer_periods[customer_id].append(period_id)
            
            logger.info(f"Created billing period: {period_id}")
            return period
    
    async def get_billing_period(self, period_id: str) -> Optional[BillingPeriod]:
        """Get a billing period."""
        return self.billing_periods.get(period_id)
    
    async def get_customer_billing_periods(
        self,
        customer_id: str,
        status: Optional[BillingPeriodStatus] = None
    ) -> List[BillingPeriod]:
        """Get billing periods for a customer."""
        period_ids = self.customer_periods.get(customer_id, [])
        periods = [self.billing_periods[pid] for pid in period_ids if pid in self.billing_periods]
        
        if status:
            periods = [p for p in periods if p.status == status]
        
        return sorted(periods, key=lambda p: p.start_date, reverse=True)
    
    async def close_billing_period(self, period_id: str) -> Optional[BillingPeriod]:
        """Close a billing period and calculate charges."""
        async with self._lock:
            period = self.billing_periods.get(period_id)
            if not period:
                return None
            
            if period.status != BillingPeriodStatus.OPEN:
                return None
            
            period.status = BillingPeriodStatus.CLOSING
            
            # Aggregate usage and calculate costs
            await self._aggregate_period_usage(period)
            
            period.status = BillingPeriodStatus.CLOSED
            period.closed_at = datetime.utcnow()
            
            logger.info(f"Closed billing period: {period_id}")
            return period
    
    async def _aggregate_period_usage(self, period: BillingPeriod):
        """Aggregate usage for a billing period."""
        # Get events for period
        events = [
            e for e in self.events
            if e.customer_id == period.customer_id
            and period.start_date <= e.timestamp <= period.end_date
        ]
        
        # Group by meter
        events_by_meter: Dict[str, List[UsageEvent]] = defaultdict(list)
        for event in events:
            # Find matching meter
            for meter in self.meters.values():
                if meter.event_type == event.event_type:
                    events_by_meter[meter.meter_id].append(event)
                    break
        
        # Calculate costs per meter
        total_amount = Decimal("0")
        line_items = []
        
        for meter_id, meter_events in events_by_meter.items():
            meter = self.meters[meter_id]
            
            # Aggregate quantity
            if meter.aggregation_type == AggregationType.SUM:
                total_quantity = sum(e.quantity for e in meter_events)
            elif meter.aggregation_type == AggregationType.COUNT:
                total_quantity = Decimal(len(meter_events))
            else:
                total_quantity = sum(e.quantity for e in meter_events)
            
            # Get pricing tiers
            tiers = await self.get_pricing_tiers(meter_id)
            
            # Calculate cost
            if tiers:
                if tiers[0].tier_type == PricingTierType.TIERED:
                    cost = CostCalculator.calculate_tiered_pricing(total_quantity, tiers)
                elif tiers[0].tier_type == PricingTierType.VOLUME:
                    cost = CostCalculator.calculate_volume_pricing(total_quantity, tiers)
                else:
                    cost = CostCalculator.calculate_flat_pricing(total_quantity, tiers[0].unit_price)
            else:
                cost = Decimal("0")
            
            if cost > 0:
                line_items.append({
                    "meter_id": meter_id,
                    "meter_name": meter.name,
                    "quantity": str(total_quantity),
                    "unit": meter.unit,
                    "amount": str(cost),
                    "currency": period.currency
                })
                total_amount += cost
        
        period.line_items = line_items
        period.total_amount = total_amount.quantize(Decimal("0.01"))
    
    # Aggregation Queries
    
    async def get_usage_summary(
        self,
        customer_id: str,
        start_time: datetime,
        end_time: datetime,
        group_by: str = "meter"
    ) -> Dict[str, Any]:
        """Get usage summary for a customer."""
        # Filter events
        events = [
            e for e in self.events
            if e.customer_id == customer_id
            and start_time <= e.timestamp <= end_time
        ]
        
        summary = {
            "customer_id": customer_id,
            "start_time": start_time,
            "end_time": end_time,
            "total_events": len(events),
            "by_meter": {},
            "by_event_type": {}
        }
        
        # Group by meter
        for event in events:
            # Find meter
            meter = None
            for m in self.meters.values():
                if m.event_type == event.event_type:
                    meter = m
                    break
            
            meter_key = meter.name if meter else event.event_type.value
            
            if meter_key not in summary["by_meter"]:
                summary["by_meter"][meter_key] = {
                    "quantity": Decimal("0"),
                    "unit": event.unit,
                    "events": 0
                }
            
            summary["by_meter"][meter_key]["quantity"] += event.quantity
            summary["by_meter"][meter_key]["events"] += 1
            
            # By event type
            event_type = event.event_type.value
            if event_type not in summary["by_event_type"]:
                summary["by_event_type"][event_type] = {
                    "quantity": Decimal("0"),
                    "events": 0
                }
            
            summary["by_event_type"][event_type]["quantity"] += event.quantity
            summary["by_event_type"][event_type]["events"] += 1
        
        # Convert Decimal to string for JSON serialization
        for meter_data in summary["by_meter"].values():
            meter_data["quantity"] = str(meter_data["quantity"])
        
        for type_data in summary["by_event_type"].values():
            type_data["quantity"] = str(type_data["quantity"])
        
        return summary
    
    # Statistics
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get telemetry statistics."""
        return {
            "meters": {
                "total": len(self.meters),
                "active": len([m for m in self.meters.values() if m.is_active])
            },
            "events": {
                "total": len(self.events),
                "last_24h": len([
                    e for e in self.events
                    if e.timestamp > datetime.utcnow() - timedelta(hours=24)
                ])
            },
            "billing_periods": {
                "total": len(self.billing_periods),
                "open": len([p for p in self.billing_periods.values() if p.status == BillingPeriodStatus.OPEN]),
                "closed": len([p for p in self.billing_periods.values() if p.status == BillingPeriodStatus.CLOSED])
            },
            "quotas": {
                "total": len(self.quotas)
            },
            "batches": {
                "total": len(self.batches)
            }
        }


class QuotaExceededError(Exception):
    """Exception raised when usage quota is exceeded."""
    pass


# Global manager instance
_telemetry_manager: Optional[UsageTelemetryManager] = None


async def get_telemetry_manager() -> UsageTelemetryManager:
    """Get or create the global telemetry manager."""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = UsageTelemetryManager()
        await _telemetry_manager.initialize()
    return _telemetry_manager


def reset_telemetry_manager():
    """Reset the global telemetry manager (for testing)."""
    global _telemetry_manager
    _telemetry_manager = None
