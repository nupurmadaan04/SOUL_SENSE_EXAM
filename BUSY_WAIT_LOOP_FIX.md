# Busy-Wait Loop Fix for Event Processing (#1158)

## Issue Description
Event loop continuously polls without yielding, causing CPU starvation.

**Objective:** Prevent CPU starvation.

**Edge Cases:**
- Empty queue loops
- High-frequency polling

**Test Cases:**
- Observe CPU under idle state
- Profiling event loop activity

**Recommended Testing:**
- Use `top`, `htop`
- Async loop debug tools

**Technical Implementation:**
- Add `await asyncio.sleep()`
- Replace polling with event-driven triggers

## Solution Implemented

### Changes Made

1. **Added `subscribe()` and `unsubscribe()` methods to `KafkaProducerService`** (`backend/fastapi/api/services/kafka_producer.py`):
   - `subscribe()`: Returns the `live_events` asyncio.Queue for local event consumption
   - `unsubscribe()`: No-op for shared queue

2. **Added `await asyncio.sleep(0)` after event processing** in event consumers:
   - `cqrs_worker.py`: After processing CQRS events for Score entities
   - `audit_consumer.py`: After persisting audit snapshots

### How It Fixes the Issue

- **Prevents CPU Starvation:** `sleep(0)` yields control to the event loop after each event, allowing other async tasks to run during high-frequency processing.

- **Handles Empty Queues:** Existing `await q.get()` waits for events when queue is empty, preventing busy-waiting in idle states.

- **Addresses High-Frequency Polling:** Yields after each event to maintain responsiveness.

- **Event-Driven Design:** Maintains event-driven patterns with `await` on queue operations and Kafka consumer `getone()`.

### Files Modified
- `backend/fastapi/api/services/kafka_producer.py`
- `backend/fastapi/api/services/cqrs_worker.py`
- `backend/fastapi/api/services/audit_consumer.py`

### Testing
- Syntax validation passed
- Ready for profiling with `top`/`htop` to verify CPU usage reduction under load</content>
<parameter name="filePath">BUSY_WAIT_LOOP_FIX.md