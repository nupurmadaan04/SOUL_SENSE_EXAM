# Infrastructure Cost Anomaly Alerts

## Overview

The Cost Anomaly Alert system monitors infrastructure costs in real-time and detects unusual spending patterns before they become a problem. It uses a 3-tier detection strategy to identify cost anomalies and generate actionable alerts.

### Why This Matters
- **Close DevOps gaps**: Catch cost regressions before they impact the budget
- **Reduce risk**: Early warning system for cost explosions
- **Observable**: Metrics and logs for dashboards and alerting systems
- **Safe rollout**: Feature flags and gradual staging deployment

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cost Anomaly Alert System                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CostTrendAnalyzer          CostAnomalyDetector                 │
│  ├─ record_cost()            ├─ detect_anomaly()                │
│  ├─ get_baseline()           ├─ Tier 1: Baseline Comparison     │
│  └─ get_rate_of_change()     ├─ Tier 2: Rate of Change         │
│                              └─ Tier 3: Absolute Limits         │
│                                                                   │
│  CostAnomalyAlertManager                                        │
│  ├─ add_alert()                                                 │
│  ├─ get_alerts()                                                │
│  └─ clear_alerts_before()                                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Detection Strategy

The system uses three tiers of detection:

#### Tier 1: Baseline Comparison
Compares current cost against a rolling 7-day average.

- **WARNING**: Cost exceeds baseline by 20-49%
- **CRITICAL**: Cost exceeds baseline by 50%+

Example:
```
Baseline cost (7-day avg): $20.00
Current cost: $24.00
Deviation: +20% → WARNING alert
```

#### Tier 2: Rate of Change
Detects cost acceleration (abnormal velocity).

Compares current hour's average against previous hour's average.

- **WARNING**: Cost acceleration > 2x normal rate

Example:
```
Previous hour avg: $10.00
Current hour avg: $25.00
Rate of change: +150% → WARNING alert
```

#### Tier 3: Absolute Limits
Hard budget cap per service (configured).

- **CRITICAL**: Cost exceeds daily budget cap

Example:
```
Daily budget: $50.00
Current cost: $75.00
Status: Over budget → CRITICAL alert
```

---

## Configuration

Cost monitoring is configured in `config.json`:

```json
{
  "cost_monitoring": {
    "enabled": true,
    "alert_on_anomaly": true,
    "baseline_days": 7,
    "services": {
      "api_compute": {
        "daily_budget_usd": 50.0,
        "spike_threshold_percent": 20,
        "rate_of_change_multiplier": 2.0
      },
      "ml_endpoints": {
        "daily_budget_usd": 100.0,
        "spike_threshold_percent": 25,
        "rate_of_change_multiplier": 2.0
      },
      "database": {
        "daily_budget_usd": 30.0,
        "spike_threshold_percent": 15,
        "rate_of_change_multiplier": 1.5
      }
    }
  }
}
```

### Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `enabled` | bool | Enable/disable cost monitoring globally |
| `alert_on_anomaly` | bool | Emit alerts when anomalies detected |
| `baseline_days` | int | Number of days to include in rolling average (default 7) |
| `daily_budget_usd` | float | Maximum cost per service per day (USD) |
| `spike_threshold_percent` | int | Percentage above baseline to trigger WARNING (default 20%) |
| `rate_of_change_multiplier` | float | Velocity multiple to trigger WARNING (default 2.0x) |

---

## Usage Examples

### Basic Cost Recording

```python
from app.infra.cost_trend_analyzer import CostTrendAnalyzer

analyzer = CostTrendAnalyzer()

# Record cost for API compute service
analyzer.record_cost("api_compute", 25.50)

# Record with explicit timestamp
from datetime import datetime, timedelta
analyzer.record_cost(
    "ml_endpoints",
    50.00,
    timestamp=datetime.utcnow() - timedelta(hours=1)
)
```

### Detecting Anomalies

```python
from app.infra.cost_anomaly_detector import CostAnomalyDetector
import json

# Load configuration
with open("config.json") as f:
    config = json.load(f)

# Create detector
detector = CostAnomalyDetector()

# Detect anomalies for a service
alerts = detector.detect_anomaly(
    "api_compute",
    current_cost=30.0,
    config=config["cost_monitoring"]
)

# Process alerts
for alert in alerts:
    print(alert)  # [WARNING] api_compute: $30.00 vs baseline $20.00 (+50%) - ...
```

### Managing Alerts

```python
from app.infra.cost_alert_manager import CostAnomalyAlertManager
from app.infra.cost_anomaly_detector import AlertLevel

manager = CostAnomalyAlertManager()

# Add alerts from detector
manager.add_alerts(alerts)

# Get all critical alerts
critical = manager.get_alerts(alert_level=AlertLevel.CRITICAL)

# Get all alerts for a specific service
api_alerts = manager.get_alerts(service_name="api_compute")

# Get summary stats
summary = manager.get_summary()
# {'total': 5, 'critical': 2, 'warning': 3, 'info': 0, 'services': ['api_compute', 'ml_endpoints']}

# Clear old alerts (older than 1 hour)
from datetime import timedelta
manager.clear_alerts_before(datetime.utcnow() - timedelta(hours=1))
```

---

## Alert Types & Severity

### INFO Level
Informational alerts for monitoring purposes.

**Never generated by this system (reserved for future).**

### WARNING Level
Cost anomaly detected but not critical.

- Cost spike of 20-49% above baseline
- Cost acceleration 2x normal velocity
- Not exceeding absolute budget

**Action**: Review cost changes, investigate root cause

### CRITICAL Level
Immediate cost control required.

- Cost spike of 50%+ above baseline
- Exceeds daily service budget
- Potential runaway costs

**Action**: URGENT - Stop new deployments, scale down, investigate immediately

---

## Example Scenarios

### Scenario 1: Normal Operation
```
Service: api_compute
Baseline (7-day): $20.00
Current cost: $19.50
Alerts: None ✓

Reason: Cost within 5% of baseline
```

### Scenario 2: Cost Spike Detection
```
Service: ml_endpoints
Baseline (7-day): $100.00
Current cost: $130.00
Deviation: +30%

Alerts:
  [WARNING] ml_endpoints: $130.00 vs baseline $100.00 (+30%) -
  Cost spike 30% above baseline
```

### Scenario 3: Budget Breach
```
Service: database
Daily budget: $30.00
Current cost: $45.00
Exceeded by: $15.00 (+50%)

Alerts:
  [CRITICAL] database: Exceeded daily budget ($30.00) by $15.00 (50%) -
  CRITICAL: Exceeded daily budget
```

### Scenario 4: Cost Acceleration
```
Service: api_compute
Previous hour avg: $5.00
Current hour avg: $12.00
Rate: +140%

Alerts:
  [WARNING] api_compute: Cost acceleration detected: +140% change rate
```

---

## Troubleshooting

### No Alerts Being Generated

**Check enabled flag:**
```python
config = json.load(open("config.json"))
if not config["cost_monitoring"]["enabled"]:
    print("Cost monitoring is disabled!")
```

**Check service is in config:**
```python
services = config["cost_monitoring"]["services"].keys()
if "your_service" not in services:
    print("Service not configured!")
```

**Check baseline has historical data:**
```python
analyzer = CostTrendAnalyzer()
baseline = analyzer.get_baseline("api_compute", days=7)
if baseline is None:
    print("Insufficient historical data (< 1 record in 7 days)")
```

### False Positive Storm (Too Many Alerts)

**Adjust spike threshold** in config.json:
```json
"api_compute": {
  "spike_threshold_percent": 30  // Increase from 20 to 30
}
```

**Increase baseline window:**
```json
"baseline_days": 14  // Change from 7 to 14 for smoother average
```

### Alerts Not Persisting

The system stores alerts in memory. To persist:
1. Implement custom `CostAnomalyAlertManager` with DB backend
2. Or call `get_alerts()` periodically to export

### Performance Issues with Large Datasets

Current implementation keeps all records in memory. If you have > 100k records:
1. Implement periodic **alert archive** to move old records to DB
2. Use `clear_alerts_before()` to prune old alerts
3. Add pagination to `get_records()`

---

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest tests/test_cost_anomaly_detector.py -v

# Specific test class
pytest tests/test_cost_anomaly_detector.py::TestCostAnomalyDetector -v

# Tests with output
pytest tests/test_cost_anomaly_detector.py -v -s

# Coverage report
pytest tests/test_cost_anomaly_detector.py --cov=app.infra
```

### Test Categories

| Category | Count | Purpose |
|----------|-------|---------|
| Trend Analyzer | 12 | Recording costs, baseline computation, rate calculation |
| Anomaly Detector | 9 | Detection logic across 3 tiers |
| Alert Manager | 8 | Alert lifecycle (create, retrieve, filter) |
| Integration | 1 | End-to-end workflow |
| Edge Cases | 5 | Zero baselines, invalid inputs, concurrency |

---

## Monitoring & Metrics

### Suggested Prometheus Metrics

```python
# Counter: Total anomalies detected
cost_anomalies_total{service="api_compute", level="warning"}

# Gauge: Current service cost
cost_current_usd{service="api_compute"} 25.50

# Gauge: Service baseline cost
cost_baseline_usd{service="api_compute"} 20.00

# Gauge: Deviation from baseline
cost_deviation_percent{service="api_compute"} 27.5

# Gauge: Days of historical data available
cost_history_days{service="api_compute"} 7
```

### Grafana Dashboard Panels

**Panel 1: Cost Trend by Service**
- X-axis: Time (hourly)
- Y-axis: Cost (USD)
- Lines: One per service
- View last 7 days

**Panel 2: Anomaly Alert Rate**
- Bar chart by service
- Separate bars for CRITICAL, WARNING
- Time range: Last 24 hours

**Panel 3: Budget Utilization**
- Service | Budget | Current | % Used
- Highlight cells > 80% in yellow, > 100% in red

**Panel 4: Baseline vs Current**
- Comparison table
- Shows deviation % for each service

---

## Safe Rollout Strategy

### Stage 1: Development (Days 1-3)
- [ ] Run tests locally: `pytest tests/test_cost_anomaly_detector.py`
- [ ] Enable in dev config
- [ ] Record mock costs
- [ ] Verify alerts generated correctly

### Stage 2: Staging (Days 4-7)
- [ ] Deploy to staging environment
- [ ] Enable with verbose logging
- [ ] Monitor for false positives
- [ ] Collect baseline (at least 24 hours of costs)
- [ ] After 24h: Run detector, review alerts

### Stage 3: Canary (Week 2)
- [ ] Enable for 5% of services
- [ ] Alerts are **read-only** (no auto-scaling)
- [ ] Monitor false positive rate < 5%
- [ ] Tune thresholds based on data

### Stage 4: Gradual Rollout (Week 3)
- [ ] 25% of services → Warnings enable auto-scaling
- [ ] 50% of services → Warnings + escalations
- [ ] 100% of services → Full rollout

### Rollback Criteria
- False positive rate > 10%
- Performance degradation > 5%
- Any unhandled exceptions in detector

---

## API Reference

### CostTrendAnalyzer

```python
class CostTrendAnalyzer:
    def record_cost(service_name: str, cost_amount: float, 
                    timestamp: Optional[datetime] = None) -> None
    
    def get_baseline(service_name: str, days: int = 7) -> Optional[float]
    
    def get_rate_of_change(service_name: str, 
                          window_hours: int = 1) -> Optional[float]
    
    def get_records(service_name: Optional[str] = None) -> List[CostRecord]
    
    def clear() -> None
```

### CostAnomalyDetector

```python
class CostAnomalyDetector:
    def detect_anomaly(service_name: str, current_cost: float,
                      config: Dict[str, Any]) -> List[CostAnomalyAlert]
```

### CostAnomalyAlertManager

```python
class CostAnomalyAlertManager:
    def add_alert(alert: CostAnomalyAlert) -> None
    
    def add_alerts(alerts: List[CostAnomalyAlert]) -> None
    
    def get_alerts(service_name: Optional[str] = None,
                   alert_level: Optional[AlertLevel] = None) -> List[CostAnomalyAlert]
    
    def clear_alerts_before(timestamp: datetime) -> int
    
    def get_summary() -> dict
```

---

## Contributing

When adding new detection tiers:

1. Add new method to `CostAnomalyDetector` (e.g., `_check_custom_metric()`)
2. Call it from `detect_anomaly()`
3. Add corresponding tests
4. Document in this file

---

## FAQ

**Q: How far back do baselines go?**
A: Configurable, default 7 days. Older records are not removed automatically.

**Q: Can I have different thresholds per service?**
A: Yes! Each service has independent `spike_threshold_percent` and budgets in config.

**Q: Does this support multi-tenant costs?**
A: Current implementation is service-based. For tenant costs, use service names like `tenant_123_api`.

**Q: What happens if baseline has no data?**
A: Detector skips Tier 1 (baseline) checks and only checks Tiers 2 & 3.

**Q: Are alerts persisted to database?**
A: Currently in-memory only. Implement custom AlertManager with DB backend for persistence.

**Q: Can I export alerts?**
A: Yes, use `manager.get_alerts()` to retrieve and serialize as JSON.

---

## License

Same as main project.
