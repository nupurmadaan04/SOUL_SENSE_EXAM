"""
Comprehensive tests for Usage Telemetry module.

Tests cover:
- Meter management
- Pricing configuration
- Event ingestion
- Billing periods
- Usage aggregation
- Quota management
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from backend.fastapi.api.utils.usage_telemetry import (
    UsageTelemetryManager,
    UsageEventType,
    AggregationType,
    BillingPeriodStatus,
    PricingTierType,
    Meter,
    PricingTier,
    BillingPeriod,
    UsageQuota,
    UsageEventValidator,
    CostCalculator,
    QuotaExceededError,
    get_telemetry_manager,
    reset_telemetry_manager
)


# Fixtures

def get_manager_sync():
    """Get telemetry manager synchronously."""
    reset_telemetry_manager()
    return asyncio.run(get_telemetry_manager())


@pytest.fixture
def telemetry_manager():
    """Fixture for telemetry manager."""
    manager = get_manager_sync()
    yield manager
    reset_telemetry_manager()


@pytest.fixture
def sample_meter_data():
    """Sample meter data for testing."""
    return {
        "name": "API Calls",
        "description": "Number of API calls",
        "event_type": UsageEventType.API_CALL,
        "aggregation_type": AggregationType.COUNT,
        "unit": "requests"
    }


# Unit Tests

class TestUsageEventTypes:
    """Test usage event type enums."""
    
    def test_event_type_values(self):
        """Test that all event types have correct values."""
        assert UsageEventType.API_CALL.value == "api_call"
        assert UsageEventType.STORAGE.value == "storage"
        assert UsageEventType.BANDWIDTH.value == "bandwidth"
        assert UsageEventType.CUSTOM.value == "custom"


class TestAggregationTypes:
    """Test aggregation type enums."""
    
    def test_aggregation_values(self):
        """Test that all aggregation types have correct values."""
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.COUNT.value == "count"
        assert AggregationType.AVERAGE.value == "average"
        assert AggregationType.UNIQUE_COUNT.value == "unique_count"


class TestBillingPeriodStatus:
    """Test billing period status enums."""
    
    def test_status_values(self):
        """Test that all billing period statuses have correct values."""
        assert BillingPeriodStatus.OPEN.value == "open"
        assert BillingPeriodStatus.CLOSED.value == "closed"
        assert BillingPeriodStatus.INVOICED.value == "invoiced"


class TestPricingTierTypes:
    """Test pricing tier type enums."""
    
    def test_tier_type_values(self):
        """Test that all pricing tier types have correct values."""
        assert PricingTierType.FLAT.value == "flat"
        assert PricingTierType.VOLUME.value == "volume"
        assert PricingTierType.TIERED.value == "tiered"
        assert PricingTierType.STAIRSTEP.value == "stairstep"


class TestUsageEventValidator:
    """Test usage event validator."""
    
    def test_validate_valid_event(self):
        """Test validating a valid event."""
        event_data = {
            "event_type": "api_call",
            "customer_id": "cust_123",
            "quantity": 10,
            "unit": "requests"
        }
        
        errors = UsageEventValidator.validate(event_data)
        assert len(errors) == 0
    
    def test_validate_missing_fields(self):
        """Test validating event with missing fields."""
        event_data = {
            "event_type": "api_call"
            # Missing customer_id, quantity, unit
        }
        
        errors = UsageEventValidator.validate(event_data)
        assert len(errors) == 3
        assert any("customer_id" in e for e in errors)
        assert any("quantity" in e for e in errors)
    
    def test_validate_invalid_quantity(self):
        """Test validating event with invalid quantity."""
        event_data = {
            "event_type": "api_call",
            "customer_id": "cust_123",
            "quantity": -5,
            "unit": "requests"
        }
        
        errors = UsageEventValidator.validate(event_data)
        assert any("non-negative" in e for e in errors)
    
    def test_validate_invalid_event_type(self):
        """Test validating event with invalid event type."""
        event_data = {
            "event_type": "invalid_type",
            "customer_id": "cust_123",
            "quantity": 10,
            "unit": "requests"
        }
        
        errors = UsageEventValidator.validate(event_data)
        assert any("Invalid event_type" in e for e in errors)


class TestCostCalculator:
    """Test cost calculator."""
    
    def test_flat_pricing(self):
        """Test flat pricing calculation."""
        cost = CostCalculator.calculate_flat_pricing(
            quantity=Decimal("100"),
            unit_price=Decimal("0.10")
        )
        assert cost == Decimal("10.00")
    
    def test_volume_pricing(self):
        """Test volume pricing calculation."""
        tiers = [
            PricingTier(
                tier_id="t1",
                meter_id="m1",
                tier_type=PricingTierType.VOLUME,
                unit_price=Decimal("0.10"),
                min_quantity=Decimal("0"),
                max_quantity=Decimal("1000")
            ),
            PricingTier(
                tier_id="t2",
                meter_id="m1",
                tier_type=PricingTierType.VOLUME,
                unit_price=Decimal("0.08"),
                min_quantity=Decimal("1001"),
                max_quantity=Decimal("10000")
            )
        ]
        
        cost = CostCalculator.calculate_volume_pricing(Decimal("500"), tiers)
        assert cost == Decimal("50.00")  # 500 * 0.10
        
        cost = CostCalculator.calculate_volume_pricing(Decimal("2000"), tiers)
        assert cost == Decimal("160.00")  # 2000 * 0.08
    
    def test_tiered_pricing(self):
        """Test tiered pricing calculation."""
        tiers = [
            PricingTier(
                tier_id="t1",
                meter_id="m1",
                tier_type=PricingTierType.TIERED,
                unit_price=Decimal("0.10"),
                min_quantity=Decimal("0"),
                max_quantity=Decimal("1000")
            ),
            PricingTier(
                tier_id="t2",
                meter_id="m1",
                tier_type=PricingTierType.TIERED,
                unit_price=Decimal("0.08"),
                min_quantity=Decimal("1001"),
                max_quantity=Decimal("10000")
            )
        ]
        
        cost = CostCalculator.calculate_tiered_pricing(Decimal("1500"), tiers)
        # First 1000 @ 0.10 = 100.00
        # Next 500 @ 0.08 = 40.00
        # Total = 140.00
        assert cost == Decimal("140.00")


class TestTelemetryManagerInitialization:
    """Test telemetry manager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, telemetry_manager):
        """Test that manager initializes correctly."""
        assert telemetry_manager._initialized is True
        assert len(telemetry_manager.meters) > 0  # Default meters created


class TestMeterManagement:
    """Test meter management."""
    
    @pytest.mark.asyncio
    async def test_create_meter(self, telemetry_manager, sample_meter_data):
        """Test creating a meter."""
        meter = await telemetry_manager.create_meter(
            name=sample_meter_data["name"],
            description=sample_meter_data["description"],
            event_type=sample_meter_data["event_type"],
            aggregation_type=sample_meter_data["aggregation_type"],
            unit=sample_meter_data["unit"]
        )
        
        assert meter.meter_id is not None
        assert meter.name == sample_meter_data["name"]
        assert meter.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_meter(self, telemetry_manager, sample_meter_data):
        """Test retrieving a meter."""
        created = await telemetry_manager.create_meter(
            name=sample_meter_data["name"],
            description=sample_meter_data["description"],
            event_type=sample_meter_data["event_type"],
            aggregation_type=sample_meter_data["aggregation_type"],
            unit=sample_meter_data["unit"]
        )
        
        retrieved = await telemetry_manager.get_meter(created.meter_id)
        assert retrieved is not None
        assert retrieved.meter_id == created.meter_id
    
    @pytest.mark.asyncio
    async def test_list_meters(self, telemetry_manager):
        """Test listing meters."""
        meters = await telemetry_manager.list_meters()
        assert isinstance(meters, list)
        assert len(meters) > 0


class TestPricingManagement:
    """Test pricing management."""
    
    @pytest.mark.asyncio
    async def test_create_pricing_tier(self, telemetry_manager, sample_meter_data):
        """Test creating a pricing tier."""
        meter = await telemetry_manager.create_meter(
            name=sample_meter_data["name"],
            description=sample_meter_data["description"],
            event_type=sample_meter_data["event_type"],
            aggregation_type=sample_meter_data["aggregation_type"],
            unit=sample_meter_data["unit"]
        )
        
        tier = await telemetry_manager.create_pricing_tier(
            meter_id=meter.meter_id,
            tier_type=PricingTierType.FLAT,
            unit_price=Decimal("0.10"),
            currency="USD"
        )
        
        assert tier is not None
        assert tier.meter_id == meter.meter_id
        assert tier.unit_price == Decimal("0.10")
    
    @pytest.mark.asyncio
    async def test_get_pricing_tiers(self, telemetry_manager, sample_meter_data):
        """Test getting pricing tiers."""
        meter = await telemetry_manager.create_meter(
            name=sample_meter_data["name"],
            description=sample_meter_data["description"],
            event_type=sample_meter_data["event_type"],
            aggregation_type=sample_meter_data["aggregation_type"],
            unit=sample_meter_data["unit"]
        )
        
        await telemetry_manager.create_pricing_tier(
            meter_id=meter.meter_id,
            tier_type=PricingTierType.FLAT,
            unit_price=Decimal("0.10")
        )
        
        tiers = await telemetry_manager.get_pricing_tiers(meter.meter_id)
        assert len(tiers) == 1


class TestEventIngestion:
    """Test event ingestion."""
    
    @pytest.mark.asyncio
    async def test_ingest_event(self, telemetry_manager):
        """Test ingesting a usage event."""
        event = await telemetry_manager.ingest_event(
            event_type=UsageEventType.API_CALL,
            customer_id="cust_123",
            quantity=Decimal("10"),
            unit="requests"
        )
        
        assert event.event_id is not None
        assert event.customer_id == "cust_123"
        assert event.quantity == Decimal("10")
        assert event.checksum is not None
    
    @pytest.mark.asyncio
    async def test_ingest_batch(self, telemetry_manager):
        """Test ingesting a batch of events."""
        events_data = [
            {
                "event_type": "api_call",
                "customer_id": "cust_123",
                "quantity": 10,
                "unit": "requests"
            },
            {
                "event_type": "storage",
                "customer_id": "cust_123",
                "quantity": 5.5,
                "unit": "GB"
            }
        ]
        
        batch = await telemetry_manager.ingest_batch(events_data)
        
        assert batch.batch_id is not None
        assert len(batch.events) == 2
        assert batch.status == "completed"


class TestBillingPeriods:
    """Test billing period management."""
    
    @pytest.mark.asyncio
    async def test_create_billing_period(self, telemetry_manager):
        """Test creating a billing period."""
        now = datetime.utcnow()
        period = await telemetry_manager.create_billing_period(
            customer_id="cust_123",
            start_date=now,
            end_date=now + timedelta(days=30)
        )
        
        assert period.period_id is not None
        assert period.customer_id == "cust_123"
        assert period.status == BillingPeriodStatus.OPEN
    
    @pytest.mark.asyncio
    async def test_close_billing_period(self, telemetry_manager):
        """Test closing a billing period."""
        now = datetime.utcnow()
        period = await telemetry_manager.create_billing_period(
            customer_id="cust_123",
            start_date=now - timedelta(days=30),
            end_date=now
        )
        
        # Add some events first
        await telemetry_manager.ingest_event(
            event_type=UsageEventType.API_CALL,
            customer_id="cust_123",
            quantity=Decimal("100"),
            unit="requests"
        )
        
        closed = await telemetry_manager.close_billing_period(period.period_id)
        
        assert closed is not None
        assert closed.status == BillingPeriodStatus.CLOSED
        assert closed.total_amount >= 0


class TestQuotaManagement:
    """Test quota management."""
    
    @pytest.mark.asyncio
    async def test_create_quota(self, telemetry_manager):
        """Test creating a quota."""
        meter = await telemetry_manager.create_meter(
            name="API Calls",
            description="Test",
            event_type=UsageEventType.API_CALL,
            aggregation_type=AggregationType.COUNT,
            unit="requests"
        )
        
        quota = await telemetry_manager.create_quota(
            customer_id="cust_123",
            meter_id=meter.meter_id,
            limit_quantity=Decimal("1000"),
            period_type="daily"
        )
        
        assert quota is not None
        assert quota.customer_id == "cust_123"
        assert quota.limit_quantity == Decimal("1000")
    
    @pytest.mark.asyncio
    async def test_quota_enforcement(self, telemetry_manager):
        """Test quota enforcement."""
        meter = await telemetry_manager.create_meter(
            name="API Calls",
            description="Test",
            event_type=UsageEventType.API_CALL,
            aggregation_type=AggregationType.COUNT,
            unit="requests"
        )
        
        await telemetry_manager.create_quota(
            customer_id="cust_limited",
            meter_id=meter.meter_id,
            limit_quantity=Decimal("5"),
            period_type="daily",
            is_hard_limit=True
        )
        
        # Ingest events up to limit
        for i in range(5):
            await telemetry_manager.ingest_event(
                event_type=UsageEventType.API_CALL,
                customer_id="cust_limited",
                quantity=Decimal("1"),
                unit="requests"
            )
        
        # Next event should exceed quota
        with pytest.raises(QuotaExceededError):
            await telemetry_manager.ingest_event(
                event_type=UsageEventType.API_CALL,
                customer_id="cust_limited",
                quantity=Decimal("1"),
                unit="requests"
            )


class TestUsageSummary:
    """Test usage summary generation."""
    
    @pytest.mark.asyncio
    async def test_get_usage_summary(self, telemetry_manager):
        """Test getting usage summary."""
        now = datetime.utcnow()
        
        # Create events
        await telemetry_manager.ingest_event(
            event_type=UsageEventType.API_CALL,
            customer_id="cust_summary",
            quantity=Decimal("100"),
            unit="requests"
        )
        await telemetry_manager.ingest_event(
            event_type=UsageEventType.STORAGE,
            customer_id="cust_summary",
            quantity=Decimal("10"),
            unit="GB"
        )
        
        summary = await telemetry_manager.get_usage_summary(
            customer_id="cust_summary",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1)
        )
        
        assert summary["customer_id"] == "cust_summary"
        assert summary["total_events"] == 2
        assert "by_meter" in summary
        assert "by_event_type" in summary


class TestStatistics:
    """Test statistics generation."""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, telemetry_manager):
        """Test getting telemetry statistics."""
        stats = await telemetry_manager.get_statistics()
        
        assert "meters" in stats
        assert "events" in stats
        assert "billing_periods" in stats
        assert "quotas" in stats


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
