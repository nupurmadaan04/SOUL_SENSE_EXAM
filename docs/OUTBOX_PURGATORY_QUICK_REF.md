# Outbox Purgatory - Quick Reference

## 🎯 What Was Implemented

This PR implements production-grade safeguards against the Transactional Outbox "purgatory" risk where failed events accumulate indefinitely.

## ✅ Implementation Checklist

- [x] **OutboxEvent Model**: Extended with `last_error` field for relay failure tracking
- [x] **Retry Policy**: Max 3 attempts with exponential backoff (30s → 60s → 120s)
- [x] **Dead-Letter Queue**: Events move to `dead_letter` status after 3 failures
- [x] **Purgatory Monitor**: Background job alerts when volume exceeds 10,000
- [x] **Admin Recovery API**: Endpoint to reset failed/dead-letter events to pending
- [x] **Admin Stats API**: Real-time queue health visibility
- [x] **Admin Dead-Letter API**: List and investigate stuck events
- [x] **Database Migration**: Remove legacy `error_message` column
- [x] **Comprehensive Tests**: Full test coverage for all features
- [x] **Documentation**: Complete implementation guide and runbook

## 🚀 Quick Start

### Check Queue Health

```bash
curl http://localhost:8000/api/v1/tasks/admin/outbox/stats \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "status_counts": {
    "pending": 45,
    "processed": 12543,
    "failed": 3,
    "dead_letter": 2
  },
  "total_unresolved": 50,
  "oldest_unresolved_age_seconds": 120,
  "purgatory_risk": "NORMAL",
  "purgatory_threshold": 10000,
  "message": "Queue health: NORMAL"
}
```

### Investigate Dead-Letter Events

```bash
curl http://localhost:8000/api/v1/tasks/admin/outbox/dead-letters?limit=10 \
  -H "Authorization: Bearer <admin_token>"
```

### Recover Failed Events

```bash
curl -X POST http://localhost:8000/api/v1/tasks/admin/outbox/retry \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "status": "success",
  "recovered_count": 5,
  "message": "Successfully reset 5 events to pending status."
}
```

## 📊 Monitoring

### Alert Thresholds

| Level | Volume | Action |
|-------|--------|--------|
| 🟢 Normal | < 1,000 | None |
| 🟡 Elevated | 1,000 - 4,999 | Monitor |
| 🟠 Warning | 5,000 - 9,999 | Investigate |
| 🔴 Critical | ≥ 10,000 | **Admin intervention required** |

### Log Messages

```bash
# Normal operation
[Outbox] Relayed 15 indexing events to Elasticsearch.

# Retry scheduled
[Outbox] Retry scheduled for event 123 in 30s (attempt 1/3)

# Dead-letter transition
[Outbox] Event 456 moved to DEAD_LETTER after 3 failed attempts.

# Purgatory alert
[CRITICAL ALERT] Outbox Purgatory Threshold Exceeded! Current Volume: 12,543.
```

## 🔧 Troubleshooting

### Problem: High Volume of Dead-Letter Events

**Diagnosis:**
```bash
curl http://localhost:8000/api/v1/tasks/admin/outbox/dead-letters?limit=50 \
  -H "Authorization: Bearer <admin_token>"
```

**Common Causes:**
- Elasticsearch service down
- Network connectivity issues
- Invalid payload format
- Permission errors

**Resolution:**
1. Fix root cause
2. Retry events: `POST /api/v1/tasks/admin/outbox/retry`
3. Monitor recovery progress

### Problem: Events Stuck in Pending

**Diagnosis:**
- Check relay worker is running: `ps aux | grep outbox_relay`
- Check logs: `tail -f logs/api.log | grep Outbox`
- Check stats: `GET /api/v1/tasks/admin/outbox/stats`

**Resolution:**
- Restart application to restart relay worker
- Check Elasticsearch connectivity
- Verify database connection pool

## 📁 Key Files

| File | Purpose |
|------|---------|
| `backend/fastapi/api/models/__init__.py` | OutboxEvent model definition |
| `backend/fastapi/api/services/outbox_relay_service.py` | Relay worker & monitor |
| `backend/fastapi/api/routers/tasks.py` | Admin recovery APIs |
| `backend/fastapi/api/main.py` | Worker startup integration |
| `migrations/versions/20260301_120000_*.py` | Database migration |
| `docs/OUTBOX_PURGATORY_IMPLEMENTATION.md` | Full documentation |
| `backend/fastapi/tests/test_outbox_purgatory_implementation.py` | Test suite |

## 🧪 Testing

### Run Tests

```bash
pytest backend/fastapi/tests/test_outbox_purgatory_implementation.py -v
```

### Manual Testing

```python
# Create a test event
from backend.fastapi.api.models import OutboxEvent
event = OutboxEvent(
    topic="search_indexing",
    payload={"journal_id": 999, "action": "upsert"},
    status="pending"
)
db.add(event)
db.commit()

# Watch it get processed
tail -f logs/api.log | grep "Outbox"
```

## 🔐 Security

- All admin endpoints require `is_admin = True`
- Unauthorized access returns `403 Forbidden`
- All recovery actions are audit logged
- Rate limiting recommended for admin endpoints

## 📈 Performance

- Relay worker: Processes 50 events per batch
- Monitor frequency: Every 5 minutes
- Relay polling: Every 2 seconds
- Indexes: `status`, `next_retry_at`, `created_at`

## 🎓 Architecture

```
┌─────────────────┐
│  Application    │
│  (Write Path)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OutboxEvent     │◄─── Transactional Write
│ (pending)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Relay Worker    │◄─── Polls every 2s
│ (Background)    │
└────────┬────────┘
         │
         ├─── Success ──► status = processed
         │
         └─── Failure ──► retry_count++
                          │
                          ├─── < 3 retries ──► Exponential backoff
                          │
                          └─── ≥ 3 retries ──► status = dead_letter
                                                │
                                                ▼
                                          ┌──────────────┐
                                          │ Purgatory    │
                                          │ Monitor      │
                                          └──────┬───────┘
                                                 │
                                                 ├─── < 10k ──► OK
                                                 │
                                                 └─── ≥ 10k ──► CRITICAL ALERT
                                                                │
                                                                ▼
                                                          ┌──────────────┐
                                                          │ Admin        │
                                                          │ Recovery API │
                                                          └──────────────┘
```

## 📝 Summary

This implementation provides:
- ✅ Automatic retry with exponential backoff
- ✅ Dead-letter queue for terminal failures
- ✅ Proactive monitoring and alerting
- ✅ Admin tools for manual recovery
- ✅ Complete observability into queue health
- ✅ Production-ready with comprehensive tests

**Status:** Ready for production deployment.

---

For detailed information, see [OUTBOX_PURGATORY_IMPLEMENTATION.md](./OUTBOX_PURGATORY_IMPLEMENTATION.md)
