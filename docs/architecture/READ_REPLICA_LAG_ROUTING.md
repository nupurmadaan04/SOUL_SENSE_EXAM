# Read-Replica Lag Aware Routing

## Overview

Read-replica lag aware routing is a database optimization feature that intelligently routes read queries based on replication lag between primary and read-replica databases. This prevents reading stale data when replica lag exceeds acceptable thresholds.

## Problem Statement

Without lag-aware routing, applications face several issues:

1. **Stale Data**: Reads from heavily lagged replicas return outdated information
2. **Consistency Violations**: Users may not see their recent writes (read-your-own-writes problem)
3. **Data Integrity**: Business logic relying on fresh data may make incorrect decisions
4. **Regression Risk**: Database topology changes can silently introduce lag-related bugs

## Solution

This implementation provides:

✅ **Automatic Lag Detection**: Periodically measures replication lag using database-native queries  
✅ **Smart Routing**: Routes reads to replica when healthy, falls back to primary when lag exceeds threshold  
✅ **Safe Defaults**: Conservative thresholds and failsafe behavior prevent data consistency issues  
✅ **Observability**: Comprehensive metrics and health endpoints for monitoring  
✅ **Feature Flags**: Granular control over lag detection and routing behavior

## Architecture

### Components

1. **ReplicaLagMonitor** (`replica_lag_monitor.py`)
   - Measures replication lag using database-specific queries
   - Caches lag measurements to avoid query overhead
   - Provides health status based on configurable thresholds
   - Runs background monitoring task

2. **Database Router** (`db_router.py`)
   - Integration point for lag-aware routing
   - Checks replica health before routing reads
   - Falls back to primary when replica unhealthy
   - Works with existing read-your-own-writes guard

3. **Health Endpoints** (`routers/health.py`)
   - `/health` - Includes replica lag in overall health check
   - `/replica-lag` - Detailed lag metrics
   - `/replica-lag/check` - Manual lag check trigger

4. **Configuration** (`config.py`)
   - Feature flags for enabling/disabling lag detection
   - Tunable thresholds and intervals
   - Timeout and fallback behavior controls

### Data Flow

```
┌─────────────────┐
│  HTTP Request   │
│   (GET/READ)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   db_router.get_db()            │
│  - Check method type            │
│  - Check read-your-own-writes   │
│  - Check replica lag            │
└────────┬──────────────┬─────────┘
         │              │
    Healthy         Unhealthy
         │              │
         ▼              ▼
┌────────────┐   ┌─────────────┐
│  Replica   │   │   Primary   │
│   Engine   │   │   Engine    │
└────────────┘   └─────────────┘
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Read-Replica Lag Detection Configuration
ENABLE_REPLICA_LAG_DETECTION=true          # Enable/disable lag detection
REPLICA_LAG_THRESHOLD_MS=5000              # Maximum acceptable lag (ms)
REPLICA_LAG_CHECK_INTERVAL_SECONDS=10      # How often to check lag
REPLICA_LAG_CACHE_TTL_SECONDS=5            # Cache lag measurements
REPLICA_LAG_TIMEOUT_SECONDS=2.0            # Query timeout for lag checks
REPLICA_LAG_FALLBACK_ON_ERROR=true         # Fallback to primary on errors
```

### Configuration Options

| Setting                              | Default | Description                        |
| ------------------------------------ | ------- | ---------------------------------- |
| `enable_replica_lag_detection`       | `true`  | Master switch for lag detection    |
| `replica_lag_threshold_ms`           | `5000`  | Max acceptable lag in milliseconds |
| `replica_lag_check_interval_seconds` | `10`    | Background check interval          |
| `replica_lag_cache_ttl_seconds`      | `5`     | TTL for cached lag measurements    |
| `replica_lag_timeout_seconds`        | `2.0`   | Timeout for lag check queries      |
| `replica_lag_fallback_on_error`      | `true`  | Route to primary on check errors   |

## Database-Specific Implementation

### PostgreSQL

Uses `pg_last_wal_receive_lsn()` and `pg_last_wal_replay_lsn()` to measure replication lag:

```sql
SELECT CASE
    WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()
    THEN 0
    ELSE EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) * 1000
END AS lag_ms
```

### MySQL/MariaDB

Uses `SHOW SLAVE STATUS` to get `Seconds_Behind_Master`:

```sql
SHOW SLAVE STATUS
-- Returns Seconds_Behind_Master in result set
```

### SQLite

No native replication support, always returns 0 lag.

## Usage

### Basic Setup

1. Configure replica database URL:

```python
# In .env or config
REPLICA_DATABASE_URL=postgresql://replica:5432/soulsense
```

2. Enable lag detection (enabled by default):

```python
ENABLE_REPLICA_LAG_DETECTION=true
```

3. The system will automatically:
   - Initialize lag monitor on startup
   - Start background monitoring
   - Route reads based on replica health

### Monitoring

#### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Response includes replica lag status:

```json
{
  "status": "healthy",
  "services": {
    "database": { "status": "healthy" },
    "replica_lag": {
      "status": "healthy",
      "latency_ms": 1234.5,
      "message": "Replica lag: 1234.50ms"
    }
  }
}
```

#### Detailed Lag Metrics

```bash
curl http://localhost:8000/replica-lag
```

Response:

```json
{
  "enabled": true,
  "replica_configured": true,
  "metrics": {
    "last_lag_ms": 1234.5,
    "last_check_time": "2026-03-07T10:30:00Z",
    "cache_age_seconds": 2.1,
    "replica_healthy": true,
    "error_count": 0,
    "threshold_ms": 5000,
    "check_interval_seconds": 10
  },
  "configuration": {
    "threshold_ms": 5000,
    "check_interval_seconds": 10,
    "cache_ttl_seconds": 5,
    "timeout_seconds": 2.0,
    "fallback_on_error": true
  }
}
```

#### Manual Lag Check

```bash
curl -X POST http://localhost:8000/replica-lag/check
```

Response:

```json
{
  "success": true,
  "lag_ms": 1234.5,
  "replica_healthy": true,
  "threshold_ms": 5000,
  "within_threshold": true
}
```

## Observability

### Logging

The system logs important events at appropriate levels:

- **INFO**: Lag within threshold, routine health checks
- **WARNING**: Lag exceeds threshold, routing to primary
- **ERROR**: Lag check failures, consecutive errors

Examples:

```
[INFO] Replica lag monitoring active: threshold=5000ms, interval=10s
[WARNING] Replica lag (8000.00ms) exceeds threshold (5000ms) - routing reads to primary
[ERROR] Replica lag check timed out after 2.0s
```

### Metrics

Key metrics exposed via health endpoints:

- `last_lag_ms`: Most recent lag measurement
- `replica_healthy`: Boolean health status
- `error_count`: Consecutive check failures
- `cache_age_seconds`: Age of cached measurement
- `check_interval_seconds`: Configured check interval
- `threshold_ms`: Configured lag threshold

## Edge Cases and Error Handling

### Degraded Dependencies

**Scenario**: Replica database unreachable  
**Behavior**: After 3 consecutive failures, mark replica unhealthy and route to primary  
**Recovery**: Successful check resets error count

### Invalid Inputs

**Scenario**: Lag query returns NULL or invalid data  
**Behavior**: Treat as check failure, increment error count

### Concurrency Races

**Scenario**: Multiple concurrent requests check lag simultaneously  
**Behavior**: Serialized by async lock, only one check executes at a time

### Timeouts

**Scenario**: Lag check query hangs  
**Behavior**: Timeout after `replica_lag_timeout_seconds` (default 2s), mark as error

### Rollback Scenarios

**Scenario**: Need to disable lag detection quickly  
**Behavior**: Set `ENABLE_REPLICA_LAG_DETECTION=false`, all reads immediately use replica

## Testing

### Run Unit Tests

```bash
pytest test_replica_lag_routing.py -v -s
```

### Test Coverage

- ✅ PostgreSQL lag detection
- ✅ MySQL lag detection
- ✅ SQLite (no-op) handling
- ✅ Lag threshold enforcement
- ✅ Caching behavior
- ✅ Error handling and recovery
- ✅ Background monitoring
- ✅ Concurrent access
- ✅ Timeout handling
- ✅ Metrics and observability

### Integration Testing

```bash
# 1. Start application with replica configured
python backend/fastapi/api/main.py

# 2. Check health endpoint
curl http://localhost:8000/health

# 3. Monitor lag metrics
curl http://localhost:8000/replica-lag

# 4. Simulate high lag (in database)
# PostgreSQL: pg_sleep(10) on replica
# MySQL: STOP SLAVE; sleep 10; START SLAVE;

# 5. Verify routing to primary
# Check logs for "routing reads to primary" messages
```

## Performance Impact

### Overhead

- **Lag Checks**: ~10-50ms per check (cached for 5s)
- **Routing Decision**: <1ms (cached health status)
- **Background Task**: Minimal CPU/memory usage

### Optimization

- Cache lag measurements to avoid query overhead
- Async background monitoring doesn't block requests
- Lock-free health status reads (only writes need lock)

## Production Deployment

### Recommended Settings

```bash
# Conservative thresholds for production
REPLICA_LAG_THRESHOLD_MS=3000              # 3 seconds
REPLICA_LAG_CHECK_INTERVAL_SECONDS=10      # Every 10 seconds
REPLICA_LAG_CACHE_TTL_SECONDS=5            # 5 second cache
REPLICA_LAG_TIMEOUT_SECONDS=2.0            # 2 second timeout
REPLICA_LAG_FALLBACK_ON_ERROR=true         # Always fail safe
```

### Monitoring Alerts

Set up alerts for:

1. **High Lag**: `replica_lag_ms > threshold` for > 5 minutes
2. **Check Failures**: `error_count > 3` consecutively
3. **Excessive Fallback**: Too many reads routed to primary

### Scaling Considerations

- **Read Replicas**: Add more replicas if primary becomes bottleneck
- **Geographic Distribution**: Use region-specific lag thresholds
- **Autoscaling**: Monitor primary load and scale replicas accordingly

## Troubleshooting

### Issue: All reads going to primary

**Diagnosis**:

```bash
curl http://localhost:8000/replica-lag
```

**Possible Causes**:

- Lag exceeds threshold
- Replica unreachable
- Recent writes (read-your-own-writes guard)

**Solution**:

- Check replica health
- Increase lag threshold if acceptable
- Verify replica replication status

### Issue: Lag detection not working

**Diagnosis**:

```bash
curl http://localhost:8000/health
# Check replica_lag service status
```

**Possible Causes**:

- `ENABLE_REPLICA_LAG_DETECTION=false`
- Replica not configured
- Database permissions insufficient

**Solution**:

- Verify configuration
- Grant replication monitoring permissions
- Check application logs

### Issue: Excessive lag check timeouts

**Diagnosis**: Check logs for "Replica lag check timed out" messages

**Possible Causes**:

- Network latency to replica
- Replica under heavy load
- Timeout too aggressive

**Solution**:

- Increase `REPLICA_LAG_TIMEOUT_SECONDS`
- Optimize replica performance
- Check network connectivity

## Security Considerations

1. **Database Permissions**: Lag checks require minimal read permissions
2. **Health Endpoints**: May expose system internals, consider authentication
3. **DoS Prevention**: Lag checks are rate-limited by cache and background task

## Acceptance Criteria

✅ **Technical Implementation**

- [x] Replica lag detection for PostgreSQL and MySQL
- [x] Lag-aware routing with primary fallback
- [x] Configuration via environment variables
- [x] Background monitoring task
- [x] Thread-safe concurrent access

✅ **Observability**

- [x] Health endpoint integration
- [x] Detailed metrics endpoint
- [x] Manual check trigger endpoint
- [x] Comprehensive logging

✅ **Safe Rollout Controls**

- [x] Feature flag for enabling/disabling
- [x] Configurable thresholds and intervals
- [x] Graceful degradation on errors

✅ **Testing**

- [x] Unit tests for lag detection
- [x] Integration tests for routing
- [x] Edge case coverage (timeouts, errors, concurrency)
- [x] CI verification support

✅ **Edge Cases**

- [x] Degraded dependencies (replica failures)
- [x] Invalid inputs (NULL lag, negative values)
- [x] Concurrency races (async lock protection)
- [x] Timeouts (configurable query timeout)
- [x] Rollback scenarios (feature flag)

✅ **Documentation**

- [x] Architecture documentation
- [x] Configuration guide
- [x] Monitoring and alerting guide
- [x] Troubleshooting guide

## Conclusion

Read-replica lag aware routing closes a critical gap in database practices by ensuring reads only use replicas when data freshness is acceptable. The implementation provides measurable improvements in data consistency while maintaining observability and safe rollout controls.

## References

- Issue: Read-replica lag aware routing
- Related: Database read/write splitting (#1050)
- Related: Connection pooling (#960, #1216)
- PostgreSQL Replication Lag: https://www.postgresql.org/docs/current/monitoring-stats.html
- MySQL Replication Status: https://dev.mysql.com/doc/refman/8.0/en/show-replica-status.html
