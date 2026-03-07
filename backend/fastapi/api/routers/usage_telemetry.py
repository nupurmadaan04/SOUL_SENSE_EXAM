"""
Usage Telemetry API Router

Provides REST API endpoints for usage tracking, metering, and billing including:
- Usage event ingestion
- Meter management
- Pricing configuration
- Billing period management
- Usage aggregation and reporting
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.fastapi.api.utils.usage_telemetry import (
    UsageTelemetryManager,
    get_telemetry_manager,
    UsageEventType,
    AggregationType,
    BillingPeriodStatus,
    PricingTierType,
    Meter,
    PricingTier,
    BillingPeriod,
    UsageQuota,
    TelemetryBatch,
    QuotaExceededError
)

router = APIRouter(prefix="/usage-telemetry", tags=["usage-telemetry"])


# Pydantic Models

class MeterCreate(BaseModel):
    name: str
    description: str
    event_type: UsageEventType
    aggregation_type: AggregationType
    unit: str
    properties_filter: Dict[str, Any] = Field(default_factory=dict)


class MeterResponse(BaseModel):
    meter_id: str
    name: str
    description: str
    event_type: str
    aggregation_type: str
    unit: str
    is_active: bool
    created_at: datetime


class PricingTierCreate(BaseModel):
    tier_type: PricingTierType
    unit_price: float
    currency: str = "USD"
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    flat_fee: Optional[float] = None


class PricingTierResponse(BaseModel):
    tier_id: str
    meter_id: str
    tier_type: str
    unit_price: float
    currency: str
    min_quantity: Optional[float]
    max_quantity: Optional[float]
    flat_fee: Optional[float]
    is_active: bool


class UsageEventCreate(BaseModel):
    event_type: UsageEventType
    customer_id: str
    quantity: float
    unit: str
    timestamp: Optional[datetime] = None
    meter_name: Optional[str] = None
    resource_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    region: Optional[str] = None
    environment: Optional[str] = None


class UsageEventResponse(BaseModel):
    event_id: str
    event_type: str
    customer_id: str
    timestamp: datetime
    quantity: float
    unit: str
    received_at: datetime


class BatchIngestRequest(BaseModel):
    events: List[Dict[str, Any]]


class BatchIngestResponse(BaseModel):
    batch_id: str
    processed: int
    errors: int
    status: str


class QuotaCreate(BaseModel):
    meter_id: str
    limit_quantity: float
    period_type: str  # daily, weekly, monthly, yearly
    is_hard_limit: bool = False
    alert_threshold: Optional[float] = None  # 0-100


class QuotaResponse(BaseModel):
    quota_id: str
    customer_id: str
    meter_id: str
    limit_quantity: float
    current_usage: float
    period_type: str
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    is_hard_limit: bool
    alert_threshold: Optional[float]
    alert_triggered: bool


class BillingPeriodCreate(BaseModel):
    customer_id: str
    start_date: datetime
    end_date: datetime


class BillingPeriodResponse(BaseModel):
    period_id: str
    customer_id: str
    start_date: datetime
    end_date: datetime
    status: str
    total_amount: float
    currency: str
    line_items: List[Dict[str, Any]]


class UsageSummaryRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    group_by: str = "meter"


# Meter Management Endpoints

@router.post("/meters", response_model=MeterResponse, status_code=status.HTTP_201_CREATED)
async def create_meter(
    data: MeterCreate,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Create a new usage meter."""
    meter = await manager.create_meter(
        name=data.name,
        description=data.description,
        event_type=data.event_type,
        aggregation_type=data.aggregation_type,
        unit=data.unit,
        properties_filter=data.properties_filter
    )
    return _meter_to_response(meter)


@router.get("/meters", response_model=List[MeterResponse])
async def list_meters(
    event_type: Optional[UsageEventType] = None,
    active_only: bool = True,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """List usage meters."""
    meters = await manager.list_meters(
        event_type=event_type,
        active_only=active_only
    )
    return [_meter_to_response(m) for m in meters]


@router.get("/meters/{meter_id}", response_model=MeterResponse)
async def get_meter(
    meter_id: str,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get a meter by ID."""
    meter = await manager.get_meter(meter_id)
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    return _meter_to_response(meter)


@router.get("/meters/{meter_id}/pricing", response_model=List[PricingTierResponse])
async def get_meter_pricing(
    meter_id: str,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get pricing tiers for a meter."""
    if meter_id not in manager.meters:
        raise HTTPException(status_code=404, detail="Meter not found")
    
    tiers = await manager.get_pricing_tiers(meter_id)
    return [_tier_to_response(t) for t in tiers]


@router.post("/meters/{meter_id}/pricing", response_model=PricingTierResponse)
async def create_pricing_tier(
    meter_id: str,
    data: PricingTierCreate,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Create a pricing tier for a meter."""
    tier = await manager.create_pricing_tier(
        meter_id=meter_id,
        tier_type=data.tier_type,
        unit_price=Decimal(str(data.unit_price)),
        currency=data.currency,
        min_quantity=Decimal(str(data.min_quantity)) if data.min_quantity else None,
        max_quantity=Decimal(str(data.max_quantity)) if data.max_quantity else None,
        flat_fee=Decimal(str(data.flat_fee)) if data.flat_fee else None
    )
    
    if not tier:
        raise HTTPException(status_code=404, detail="Meter not found")
    
    return _tier_to_response(tier)


# Event Ingestion Endpoints

@router.post("/events", response_model=UsageEventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    data: UsageEventCreate,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Ingest a usage event."""
    try:
        event = await manager.ingest_event(
            event_type=data.event_type,
            customer_id=data.customer_id,
            quantity=Decimal(str(data.quantity)),
            unit=data.unit,
            timestamp=data.timestamp,
            meter_name=data.meter_name,
            resource_id=data.resource_id,
            properties=data.properties,
            region=data.region,
            environment=data.environment
        )
        return _event_to_response(event)
    except QuotaExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.post("/events/batch", response_model=BatchIngestResponse)
async def ingest_batch(
    data: BatchIngestRequest,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Ingest a batch of usage events."""
    batch = await manager.ingest_batch(data.events)
    
    return {
        "batch_id": batch.batch_id,
        "processed": len(batch.events),
        "errors": len([e for e in data.events if e not in [ev.__dict__ for ev in batch.events]]),
        "status": batch.status
    }


# Quota Management Endpoints

@router.post("/quotas", response_model=QuotaResponse, status_code=status.HTTP_201_CREATED)
async def create_quota(
    customer_id: str,
    data: QuotaCreate,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Create a usage quota."""
    quota = await manager.create_quota(
        customer_id=customer_id,
        meter_id=data.meter_id,
        limit_quantity=Decimal(str(data.limit_quantity)),
        period_type=data.period_type,
        is_hard_limit=data.is_hard_limit,
        alert_threshold=Decimal(str(data.alert_threshold)) if data.alert_threshold else None
    )
    
    if not quota:
        raise HTTPException(status_code=404, detail="Meter not found")
    
    return _quota_to_response(quota)


@router.get("/customers/{customer_id}/quotas", response_model=List[QuotaResponse])
async def get_customer_quotas(
    customer_id: str,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get quotas for a customer."""
    quotas = await manager.get_customer_quotas(customer_id)
    return [_quota_to_response(q) for q in quotas]


# Billing Period Endpoints

@router.post("/billing-periods", response_model=BillingPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_period(
    data: BillingPeriodCreate,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Create a billing period."""
    period = await manager.create_billing_period(
        customer_id=data.customer_id,
        start_date=data.start_date,
        end_date=data.end_date
    )
    return _period_to_response(period)


@router.get("/billing-periods/{period_id}", response_model=BillingPeriodResponse)
async def get_billing_period(
    period_id: str,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get a billing period."""
    period = await manager.get_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found")
    return _period_to_response(period)


@router.get("/customers/{customer_id}/billing-periods", response_model=List[BillingPeriodResponse])
async def get_customer_billing_periods(
    customer_id: str,
    status: Optional[BillingPeriodStatus] = None,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get billing periods for a customer."""
    periods = await manager.get_customer_billing_periods(customer_id, status)
    return [_period_to_response(p) for p in periods]


@router.post("/billing-periods/{period_id}/close")
async def close_billing_period(
    period_id: str,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Close a billing period and calculate charges."""
    period = await manager.close_billing_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Billing period not found or already closed")
    return _period_to_response(period)


# Usage Summary Endpoints

@router.post("/customers/{customer_id}/usage-summary")
async def get_usage_summary(
    customer_id: str,
    data: UsageSummaryRequest,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get usage summary for a customer."""
    summary = await manager.get_usage_summary(
        customer_id=customer_id,
        start_time=data.start_time,
        end_time=data.end_time,
        group_by=data.group_by
    )
    return summary


@router.get("/customers/{customer_id}/current-usage")
async def get_current_usage(
    customer_id: str,
    meter_id: Optional[str] = None,
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get current usage for a customer."""
    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    summary = await manager.get_usage_summary(
        customer_id=customer_id,
        start_time=start_of_month,
        end_time=now,
        group_by="meter"
    )
    
    return {
        "customer_id": customer_id,
        "period": "current_month",
        "usage": summary.get("by_meter", {})
    }


# Statistics Endpoints

@router.get("/statistics")
async def get_telemetry_statistics(
    manager: UsageTelemetryManager = Depends(get_telemetry_manager)
):
    """Get telemetry statistics."""
    stats = await manager.get_statistics()
    return stats


@router.get("/event-types")
async def list_event_types():
    """List supported usage event types."""
    return {
        "event_types": [
            {"id": et.value, "name": et.value.replace("_", " ").title()}
            for et in UsageEventType
        ]
    }


@router.get("/aggregation-types")
async def list_aggregation_types():
    """List supported aggregation types."""
    return {
        "aggregation_types": [
            {"id": at.value, "name": at.value.replace("_", " ").title()}
            for at in AggregationType
        ]
    }


# Helper Functions

def _meter_to_response(meter: Meter) -> Dict[str, Any]:
    """Convert Meter to response dict."""
    return {
        "meter_id": meter.meter_id,
        "name": meter.name,
        "description": meter.description,
        "event_type": meter.event_type.value,
        "aggregation_type": meter.aggregation_type.value,
        "unit": meter.unit,
        "is_active": meter.is_active,
        "created_at": meter.created_at
    }


def _tier_to_response(tier: PricingTier) -> Dict[str, Any]:
    """Convert PricingTier to response dict."""
    return {
        "tier_id": tier.tier_id,
        "meter_id": tier.meter_id,
        "tier_type": tier.tier_type.value,
        "unit_price": float(tier.unit_price),
        "currency": tier.currency,
        "min_quantity": float(tier.min_quantity) if tier.min_quantity else None,
        "max_quantity": float(tier.max_quantity) if tier.max_quantity else None,
        "flat_fee": float(tier.flat_fee) if tier.flat_fee else None,
        "is_active": tier.is_active
    }


def _event_to_response(event) -> Dict[str, Any]:
    """Convert UsageEvent to response dict."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "customer_id": event.customer_id,
        "timestamp": event.timestamp,
        "quantity": float(event.quantity),
        "unit": event.unit,
        "received_at": event.received_at
    }


def _quota_to_response(quota: UsageQuota) -> Dict[str, Any]:
    """Convert UsageQuota to response dict."""
    return {
        "quota_id": quota.quota_id,
        "customer_id": quota.customer_id,
        "meter_id": quota.meter_id,
        "limit_quantity": float(quota.limit_quantity),
        "current_usage": float(quota.current_usage),
        "period_type": quota.period_type,
        "period_start": quota.period_start,
        "period_end": quota.period_end,
        "is_hard_limit": quota.is_hard_limit,
        "alert_threshold": float(quota.alert_threshold) if quota.alert_threshold else None,
        "alert_triggered": quota.alert_triggered
    }


def _period_to_response(period: BillingPeriod) -> Dict[str, Any]:
    """Convert BillingPeriod to response dict."""
    return {
        "period_id": period.period_id,
        "customer_id": period.customer_id,
        "start_date": period.start_date,
        "end_date": period.end_date,
        "status": period.status.value,
        "total_amount": float(period.total_amount),
        "currency": period.currency,
        "line_items": period.line_items
    }
