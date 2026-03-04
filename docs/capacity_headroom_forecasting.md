# Capacity Headroom Forecasting - Implementation Guide

**GitHub Issue:** #1314  
**Feature Flag:** `capacity_headroom_forecasting`  

---

## Overview

Predicts resource utilization during peak windows and provides capacity recommendations for proactive scaling. Collects CPU, memory, disk, and request metrics, analyzes patterns, and forecasts capacity 24 hours ahead.

### Key Features

- **Metrics Collection**: Background service collects system metrics every 300 seconds
- **Historical Analysis**: 30-day rolling window of capacity data
- **Peak Detection**: Statistical analysis identifies peak usage windows
- **Risk Levels**: LOW (>50%), MEDIUM (30-50%), HIGH (10-30%), CRITICAL (<10% headroom)
- **Recommendations**: Actionable scaling guidance based on risk level

---

## Configuration

### Environment Variables

```bash
SOULSENSE_CAPACITY_MONITORING_ENABLED=true
SOULSENSE_CAPACITY_COLLECTION_INTERVAL_SECONDS=300
SOULSENSE_CAPACITY_RETENTION_DAYS=30
SOULSENSE_CAPACITY_FORECAST_WINDOW_HOURS=24
SOULSENSE_CAPACITY_MIN_HISTORICAL_POINTS=10
SOULSENSE_CAPACITY_CRITICAL_THRESHOLD=90.0
SOULSENSE_CAPACITY_WARNING_THRESHOLD=75.0
SOULSENSE_CAPACITY_SAFETY_MARGIN=20.0
```

### Feature Flag Control

```python
from app.feature_flags import feature_flags

if feature_flags.is_enabled("capacity_headroom_forecasting"):
    metrics_service.start()
```

---

## Usage

### 1. Generate Forecast

```python
from app.ml.capacity_headroom_forecaster import CapacityHeadroomForecaster

forecaster = CapacityHeadroomForecaster(history_days=30)
forecast = forecaster.forecast_capacity()

print(f"Risk Level: {forecast.risk_level.value}")
print(f"Min Headroom: {forecast.current_headroom['min_headroom_pct']}%")
print(f"Time to Capacity: {forecast.time_to_capacity_minutes} minutes")
```

### 2. Collect Metrics

```python
from app.services.capacity_metrics_service import get_metrics_service

service = get_metrics_service(config)
service.start()  # Background collection

metrics = service.collect_all_metrics()
```

### 3. Export Metrics

```python
from app.utils.metrics_exporter import CapacityMetricsExporter

exporter = CapacityMetricsExporter()
prometheus_text = exporter.export_all_metrics_text(metrics, forecast)
json_export = exporter.export_json(metrics, forecast)
```

---

## Testing

```bash
# Run tests
pytest tests/test_capacity_headroom_forecaster.py -v

# With coverage
pytest tests/test_capacity_headroom_forecaster.py --cov
```

---

## Deployment

### Pre-Deployment

- [ ] Tests passing: `pytest tests/test_capacity_headroom_forecaster.py`
- [ ] Code coverage > 80%
- [ ] Database migration: `alembic upgrade head`

### Feature Flag Rollout

1. **Day 1**: Enable for 10% of users, monitor
2. **Day 2-3**: Enable for 50% of users, gather feedback
3. **Day 4+**: Full rollout (100% of users)

### Enable Feature

```bash
export SOULSENSE_FF_CAPACITY_HEADROOM_FORECASTING=true
```

### Monitor

```bash
tail -f logs/soulsense.log | grep capacity_
sqlite3 data/soulsense.db "SELECT COUNT(*) FROM capacity_metrics;"
```

### Rollback (if needed)

```bash
export SOULSENSE_FF_CAPACITY_HEADROOM_FORECASTING=false
metrics_service.stop()
```

---

## Database Tables

- **capacity_metrics**: System metrics (CPU, memory, disk, request rate, response time)
- **capacity_forecasts**: Forecast results with risk levels and recommendations

---

## Metrics Exported (Prometheus)

```
soulsense_capacity_cpu_usage_percent
soulsense_capacity_memory_usage_percent
soulsense_capacity_disk_usage_percent
soulsense_capacity_headroom_minimum_percent
soulsense_capacity_forecast_risk_level
soulsense_capacity_time_to_capacity_minutes
```

---

**Version:** 1.0 | **Status:** Ready for merge
