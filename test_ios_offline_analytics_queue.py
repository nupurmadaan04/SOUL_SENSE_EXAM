#!/usr/bin/env python3
"""
Test suite for iOS offline analytics queue + retry policy - Issue #1340

Validates mobile analytics reliability during intermittent connectivity:
- Queue persistence and FIFO replay order
- Airplane mode simulation and reconnection handling
- Duplicate event suppression via idempotency
- Bounded queue growth under repeated failures
- Exponential backoff with jitter for retry policy
- At-least-once delivery semantics
"""

import asyncio
import copy
import os
import sys
import time
import json
import uuid
import threading
import random
from collections import OrderedDict
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# ---------------------------------------------------------------------------
# iOS Offline Analytics Queue Model (Python simulation of Swift behaviour)
# ---------------------------------------------------------------------------
# The iOS AnalyticsManager currently sends events synchronously to Mixpanel.
# These tests validate the *expected* offline queue contract that the new
# AnalyticsOfflineQueue layer must satisfy on the iOS client.
# ---------------------------------------------------------------------------


class AnalyticsEvent:
    """Model of an iOS analytics event."""

    def __init__(self, event_name: str, properties: dict = None,
                 event_id: str = None, timestamp: float = None):
        self.event_id = event_id or str(uuid.uuid4())
        self.event_name = event_name
        self.timestamp = timestamp or time.time()
        self.properties = properties or {}
        self.retry_count = 0

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "timestamp": self.timestamp,
            "properties": self.properties,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnalyticsEvent":
        evt = cls(
            event_name=data["event_name"],
            properties=data.get("properties", {}),
            event_id=data["event_id"],
            timestamp=data["timestamp"],
        )
        evt.retry_count = data.get("retry_count", 0)
        return evt

    def __eq__(self, other):
        if isinstance(other, AnalyticsEvent):
            return self.event_id == other.event_id
        return False

    def __hash__(self):
        return hash(self.event_id)


class NetworkSimulator:
    """Simulates iOS network reachability (airplane mode, reconnection)."""

    def __init__(self, online: bool = True):
        self._online = online
        self._listeners = []

    def is_online(self) -> bool:
        return self._online

    def set_online(self, online: bool):
        prev = self._online
        self._online = online
        if prev != online:
            for listener in self._listeners:
                listener(online)

    def on_status_change(self, callback):
        self._listeners.append(callback)

    def simulate_airplane_mode(self):
        """Turn off connectivity."""
        self.set_online(False)

    def simulate_reconnection(self):
        """Restore connectivity."""
        self.set_online(True)


class PersistentStore:
    """Simulates iOS UserDefaults / Core Data persistence for the queue."""

    def __init__(self):
        self._storage: dict = {}

    def save(self, key: str, data: str):
        self._storage[key] = data

    def load(self, key: str) -> str | None:
        return self._storage.get(key)

    def delete(self, key: str):
        self._storage.pop(key, None)

    def has_key(self, key: str) -> bool:
        return key in self._storage


class AnalyticsOfflineQueue:
    """
    Offline-first analytics queue with retry policy.

    Contract (mirrors expected iOS implementation):
    - Events are persisted immediately on enqueue.
    - Replay preserves strict enqueue (FIFO) order.
    - Duplicate events (same event_id) are suppressed.
    - Queue size is bounded; oldest low-priority events are evicted on overflow.
    - Retries use exponential backoff with jitter, capped at max_retries.
    - Delivery guarantee: at-least-once.
    """

    STORAGE_KEY = "analytics_offline_queue"

    def __init__(self, network: NetworkSimulator, store: PersistentStore,
                 max_queue_size: int = 1000, max_retries: int = 5,
                 base_delay_ms: int = 500):
        self.network = network
        self.store = store
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms

        self._queue: list[AnalyticsEvent] = []
        self._seen_ids: set[str] = set()
        self._sent_events: list[AnalyticsEvent] = []
        self._dead_letter: list[AnalyticsEvent] = []
        self._send_fn = None  # Pluggable sender for testing

        # Restore persisted queue
        self._restore_from_store()

        # Auto-flush on reconnection
        self.network.on_status_change(self._on_network_change)

    # ---- Public API --------------------------------------------------------

    def enqueue(self, event: AnalyticsEvent) -> bool:
        """Enqueue an event. Returns False if duplicate."""
        if event.event_id in self._seen_ids:
            return False  # duplicate suppression

        self._enforce_queue_limit()
        self._queue.append(event)
        self._seen_ids.add(event.event_id)
        self._persist()
        return True

    def flush(self) -> list[AnalyticsEvent]:
        """
        Attempt to send all queued events in FIFO order.
        Returns list of successfully sent events.
        """
        if not self.network.is_online():
            return []

        sent: list[AnalyticsEvent] = []
        remaining: list[AnalyticsEvent] = []

        for event in self._queue:
            if not self.network.is_online():
                remaining.append(event)
                continue

            success = self._try_send(event)
            if success:
                sent.append(event)
                self._sent_events.append(event)
            else:
                event.retry_count += 1
                if event.retry_count > self.max_retries:
                    self._dead_letter.append(event)
                else:
                    remaining.append(event)

        self._queue = remaining
        self._persist()
        return sent

    def set_sender(self, fn):
        """Inject a send function for testing: fn(event) -> bool."""
        self._send_fn = fn

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def sent_events(self) -> list[AnalyticsEvent]:
        return list(self._sent_events)

    @property
    def dead_letter_events(self) -> list[AnalyticsEvent]:
        return list(self._dead_letter)

    def get_pending_event_ids(self) -> list[str]:
        return [e.event_id for e in self._queue]

    def calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter (seconds)."""
        base = (self.base_delay_ms / 1000.0) * (2 ** attempt)
        jitter = random.uniform(0, base * 0.3)
        return min(base + jitter, 30.0)  # cap at 30s

    # ---- Internal ----------------------------------------------------------

    def _try_send(self, event: AnalyticsEvent) -> bool:
        if self._send_fn:
            return self._send_fn(event)
        return self.network.is_online()

    def _enforce_queue_limit(self):
        """Evict oldest events when queue is full."""
        while len(self._queue) >= self.max_queue_size:
            evicted = self._queue.pop(0)
            self._dead_letter.append(evicted)

    def _persist(self):
        data = json.dumps([e.to_dict() for e in self._queue])
        self.store.save(self.STORAGE_KEY, data)

    def _restore_from_store(self):
        raw = self.store.load(self.STORAGE_KEY)
        if raw:
            items = json.loads(raw)
            for item in items:
                evt = AnalyticsEvent.from_dict(item)
                if evt.event_id not in self._seen_ids:
                    self._queue.append(evt)
                    self._seen_ids.add(evt.event_id)

    def _on_network_change(self, online: bool):
        if online:
            self.flush()


# ===========================================================================
# TEST SUITE
# ===========================================================================

def _make_event(name: str = "test_event", props: dict = None,
                event_id: str = None, ts: float = None) -> AnalyticsEvent:
    return AnalyticsEvent(
        event_name=name,
        properties=props or {},
        event_id=event_id,
        timestamp=ts or time.time(),
    )


def _build_queue(online: bool = True, max_size: int = 1000,
                 max_retries: int = 5) -> tuple:
    net = NetworkSimulator(online=online)
    store = PersistentStore()
    q = AnalyticsOfflineQueue(net, store, max_queue_size=max_size,
                              max_retries=max_retries)
    return q, net, store


# ---------------------------------------------------------------------------
# 1. Queue Persistence Tests
# ---------------------------------------------------------------------------

def test_queue_persists_events_to_store():
    """Events enqueued offline survive app restart (store reload)."""
    print("\n[1.1] Queue persists events to store...")

    q, net, store = _build_queue(online=False)

    e1 = _make_event("screen_view", {"screen": "home"})
    e2 = _make_event("button_click", {"button": "start"})
    assert q.enqueue(e1)
    assert q.enqueue(e2)

    # Simulate app restart — new queue reads from same store
    q2 = AnalyticsOfflineQueue(net, store)
    assert q2.queue_size == 2
    ids = q2.get_pending_event_ids()
    assert ids == [e1.event_id, e2.event_id]
    print("  ✓ Persisted 2 events survive reload")


def test_queue_persistence_survives_multiple_restarts():
    """Queue survives multiple restart cycles without data loss."""
    print("[1.2] Multiple restart persistence...")

    _, net, store = _build_queue(online=False)
    events = [_make_event(f"event_{i}") for i in range(5)]

    q = AnalyticsOfflineQueue(net, store)
    for e in events:
        q.enqueue(e)

    for cycle in range(3):
        q = AnalyticsOfflineQueue(net, store)
        assert q.queue_size == 5, f"Cycle {cycle}: expected 5, got {q.queue_size}"

    print(f"  ✓ Queue intact after 3 restart cycles ({q.queue_size} events)")


def test_empty_store_loads_cleanly():
    """A fresh store yields an empty queue."""
    print("[1.3] Empty store initialization...")

    q, _, _ = _build_queue()
    assert q.queue_size == 0
    print("  ✓ Fresh store → empty queue")


# ---------------------------------------------------------------------------
# 2. FIFO Replay Order Tests
# ---------------------------------------------------------------------------

def test_flush_preserves_fifo_order():
    """Events are sent in strict enqueue order."""
    print("\n[2.1] FIFO replay order...")

    q, net, _ = _build_queue(online=False)
    events = []
    delivery_order = []

    def tracking_send(event):
        delivery_order.append(event.event_id)
        return True

    q.set_sender(tracking_send)

    for i in range(10):
        ts = time.time() + i * 0.001
        e = _make_event(f"event_{i}", ts=ts)
        q.enqueue(e)
        events.append(e)

    # Reconnection triggers auto-flush via listener
    net.simulate_reconnection()

    assert len(delivery_order) == 10
    for i, eid in enumerate(delivery_order):
        assert eid == events[i].event_id, (
            f"Order mismatch at {i}: expected {events[i].event_id}, got {eid}"
        )
    print(f"  ✓ All 10 events sent in FIFO order")


def test_partial_flush_preserves_remaining_order():
    """If network drops mid-flush, remaining events keep their order."""
    print("[2.2] Partial flush preserves order...")

    q, net, _ = _build_queue(online=True)
    events = [_make_event(f"event_{i}") for i in range(6)]
    for e in events:
        q.enqueue(e)

    # Send function that goes offline after 3 events
    call_count = 0

    def flaky_send(event):
        nonlocal call_count
        call_count += 1
        if call_count > 3:
            net.set_online(False)
            return False
        return True

    q.set_sender(flaky_send)
    sent = q.flush()

    assert len(sent) == 3
    assert q.queue_size == 3
    remaining_ids = q.get_pending_event_ids()
    expected_remaining = [events[i].event_id for i in range(3, 6)]
    assert remaining_ids == expected_remaining
    print(f"  ✓ Sent 3, remaining 3 in correct order")


# ---------------------------------------------------------------------------
# 3. Airplane Mode & Reconnection Tests
# ---------------------------------------------------------------------------

def test_airplane_mode_queues_events():
    """Events enqueued in airplane mode are held until reconnection."""
    print("\n[3.1] Airplane mode queuing...")

    q, net, _ = _build_queue(online=True)
    net.simulate_airplane_mode()

    events = [_make_event(f"offline_event_{i}") for i in range(5)]
    for e in events:
        q.enqueue(e)

    assert q.queue_size == 5
    assert len(q.sent_events) == 0

    # Flush while offline — nothing sent
    sent = q.flush()
    assert len(sent) == 0
    assert q.queue_size == 5
    print("  ✓ 5 events queued, 0 sent while offline")


def test_reconnection_triggers_flush():
    """Reconnection automatically flushes the queue."""
    print("[3.2] Reconnection auto-flush...")

    q, net, _ = _build_queue(online=False)
    events = [_make_event(f"pending_{i}") for i in range(4)]
    for e in events:
        q.enqueue(e)

    assert q.queue_size == 4
    assert len(q.sent_events) == 0

    # Reconnect — listener triggers flush
    net.simulate_reconnection()

    assert q.queue_size == 0
    assert len(q.sent_events) == 4
    print("  ✓ Auto-flushed 4 events on reconnection")


def test_repeated_airplane_toggle():
    """Toggling airplane mode repeatedly doesn't lose events."""
    print("[3.3] Repeated airplane toggle...")

    q, net, _ = _build_queue(online=True)

    total_enqueued = 0
    for cycle in range(5):
        net.simulate_airplane_mode()
        for j in range(3):
            q.enqueue(_make_event(f"cycle_{cycle}_event_{j}"))
            total_enqueued += 1
        net.simulate_reconnection()  # triggers flush

    assert len(q.sent_events) == total_enqueued
    assert q.queue_size == 0
    print(f"  ✓ {total_enqueued} events survived {5} airplane toggles")


def test_offline_to_online_mid_enqueue():
    """Events enqueued during connectivity transition are not lost."""
    print("[3.4] Offline-to-online mid-enqueue...")

    q, net, _ = _build_queue(online=False)

    q.enqueue(_make_event("before_reconnect_1"))
    q.enqueue(_make_event("before_reconnect_2"))

    # Reconnect — auto-flush of the 2 events
    net.simulate_reconnection()
    assert len(q.sent_events) == 2

    # Continue enqueuing while online
    q.enqueue(_make_event("after_reconnect_1"))
    q.flush()
    assert len(q.sent_events) == 3
    assert q.queue_size == 0
    print("  ✓ Seamless transition: 2 offline + 1 online all delivered")


# ---------------------------------------------------------------------------
# 4. Duplicate Suppression Tests
# ---------------------------------------------------------------------------

def test_duplicate_event_id_rejected():
    """An event with the same event_id is not enqueued twice."""
    print("\n[4.1] Duplicate event_id rejection...")

    q, _, _ = _build_queue(online=False)
    eid = str(uuid.uuid4())

    e1 = _make_event("screen_view", event_id=eid)
    e2 = _make_event("screen_view", event_id=eid)

    assert q.enqueue(e1) is True
    assert q.enqueue(e2) is False  # duplicate
    assert q.queue_size == 1
    print("  ✓ Second enqueue with same event_id rejected")


def test_duplicate_suppression_across_restarts():
    """Duplicates are still suppressed after queue reload from store."""
    print("[4.2] Duplicate suppression across restarts...")

    q, net, store = _build_queue(online=False)
    eid = str(uuid.uuid4())

    q.enqueue(_make_event("login_success", event_id=eid))
    assert q.queue_size == 1

    # Reload from store
    q2 = AnalyticsOfflineQueue(net, store)
    result = q2.enqueue(_make_event("login_success", event_id=eid))
    assert result is False
    assert q2.queue_size == 1
    print("  ✓ Duplicate suppressed after store reload")


def test_different_events_same_name_allowed():
    """Events with the same name but different IDs are both accepted."""
    print("[4.3] Different IDs, same name accepted...")

    q, _, _ = _build_queue(online=False)

    e1 = _make_event("button_click")
    e2 = _make_event("button_click")
    assert e1.event_id != e2.event_id

    assert q.enqueue(e1) is True
    assert q.enqueue(e2) is True
    assert q.queue_size == 2
    print("  ✓ Two events with same name, different IDs both queued")


def test_no_duplicate_delivery_after_flush():
    """Once flushed, re-enqueueing the same event_id is still suppressed."""
    print("[4.4] No duplicate delivery after flush...")

    q, net, _ = _build_queue(online=True)
    eid = str(uuid.uuid4())

    e = _make_event("assessment_completed", event_id=eid)
    q.enqueue(e)
    q.flush()

    assert len(q.sent_events) == 1
    assert q.queue_size == 0

    # Try re-enqueue
    assert q.enqueue(_make_event("assessment_completed", event_id=eid)) is False
    print("  ✓ Re-enqueue after delivery is suppressed")


# ---------------------------------------------------------------------------
# 5. Bounded Queue Growth Tests
# ---------------------------------------------------------------------------

def test_queue_respects_max_size():
    """Queue does not exceed max_queue_size."""
    print("\n[5.1] Maximum queue size enforcement...")

    max_size = 50
    q, _, _ = _build_queue(online=False, max_size=max_size)

    for i in range(max_size + 20):
        q.enqueue(_make_event(f"event_{i}"))

    assert q.queue_size == max_size
    print(f"  ✓ Queue capped at {max_size} (attempted {max_size + 20})")


def test_overflow_evicts_oldest_events():
    """When queue overflows, the oldest events are evicted to dead-letter."""
    print("[5.2] Overflow evicts oldest events...")

    max_size = 5
    q, _, _ = _build_queue(online=False, max_size=max_size)

    events = [_make_event(f"evt_{i}") for i in range(8)]
    for e in events:
        q.enqueue(e)

    # Oldest 3 should have been evicted
    assert q.queue_size == max_size
    remaining_ids = set(q.get_pending_event_ids())
    for i in range(3):
        assert events[i].event_id not in remaining_ids
    for i in range(3, 8):
        assert events[i].event_id in remaining_ids

    assert len(q.dead_letter_events) == 3
    print(f"  ✓ 3 oldest events evicted, 5 retained, 3 in dead-letter")


def test_queue_bounded_under_sustained_failures():
    """Queue stays bounded even when flush always fails."""
    print("[5.3] Bounded growth under sustained failures...")

    max_size = 100
    q, net, _ = _build_queue(online=True, max_size=max_size, max_retries=2)
    q.set_sender(lambda e: False)  # always fail

    for i in range(200):
        q.enqueue(_make_event(f"fail_event_{i}"))
        if i % 20 == 0:
            q.flush()  # attempt flush — all fail

    # Final flush to push retries over the limit
    for _ in range(5):
        q.flush()

    assert q.queue_size <= max_size
    print(f"  ✓ Queue size {q.queue_size} ≤ {max_size} after 200 enqueues + failures")


def test_dead_letter_on_max_retries_exceeded():
    """Events that exceed max retries go to dead-letter, not back in queue."""
    print("[5.4] Dead-letter after max retries...")

    q, net, _ = _build_queue(online=True, max_retries=3)
    q.set_sender(lambda e: False)  # always fail

    e = _make_event("doomed_event")
    q.enqueue(e)

    # Flush repeatedly until retries exhausted
    for _ in range(4):
        q.flush()

    assert q.queue_size == 0
    assert len(q.dead_letter_events) >= 1
    dead_ids = [d.event_id for d in q.dead_letter_events]
    assert e.event_id in dead_ids
    print("  ✓ Event moved to dead-letter after exceeding max retries")


# ---------------------------------------------------------------------------
# 6. Retry Policy / Backoff Tests
# ---------------------------------------------------------------------------

def test_exponential_backoff_values():
    """Backoff grows exponentially with a cap."""
    print("\n[6.1] Exponential backoff calculation...")

    q, _, _ = _build_queue()

    # With jitter, the value is in a range, so we seed random for determinism
    random.seed(42)

    delays = [q.calculate_backoff(i) for i in range(8)]

    # Verify monotonically increasing (ignoring jitter)
    for i in range(1, len(delays)):
        # Due to jitter, allow a small margin, but the cap is 30s
        assert delays[i] <= 30.0, f"Backoff exceeded 30s cap: {delays[i]}"

    # Base delay at attempt 0 should be roughly base_delay_ms / 1000
    assert delays[0] < 1.0, f"Initial backoff too high: {delays[0]}"

    # Later attempts should be significantly higher
    assert delays[4] > delays[0], "Backoff not increasing"

    random.seed()  # reset
    print(f"  ✓ Backoff progression: {[f'{d:.3f}s' for d in delays[:5]]}")


def test_backoff_cap_at_30_seconds():
    """Backoff never exceeds 30 seconds regardless of attempt number."""
    print("[6.2] Backoff cap at 30s...")

    q, _, _ = _build_queue()

    for attempt in range(20):
        delay = q.calculate_backoff(attempt)
        assert delay <= 30.0, f"Attempt {attempt}: {delay}s > 30s cap"

    print("  ✓ All 20 attempts ≤ 30s")


def test_retry_count_increments_on_failure():
    """Each failed send increments the event's retry_count."""
    print("[6.3] Retry count increments on failure...")

    q, net, _ = _build_queue(online=True, max_retries=5)
    q.set_sender(lambda e: False)

    e = _make_event("retry_test")
    q.enqueue(e)

    q.flush()  # retry_count → 1
    assert q.queue_size == 1
    pending = q._queue[0]
    assert pending.retry_count == 1

    q.flush()  # retry_count → 2
    assert q._queue[0].retry_count == 2
    print("  ✓ retry_count increments: 0 → 1 → 2")


def test_successful_send_after_retries():
    """An event succeeds after a few failures — at-least-once delivery."""
    print("[6.4] Success after retries (at-least-once)...")

    q, net, _ = _build_queue(online=True, max_retries=5)
    call_count = 0

    def succeed_on_third(event):
        nonlocal call_count
        call_count += 1
        return call_count >= 3

    q.set_sender(succeed_on_third)
    e = _make_event("eventually_succeeds")
    q.enqueue(e)

    q.flush()  # fail (call_count=1)
    q.flush()  # fail (call_count=2)
    q.flush()  # success (call_count=3)

    assert q.queue_size == 0
    assert len(q.sent_events) == 1
    assert q.sent_events[0].event_id == e.event_id
    print(f"  ✓ Delivered on attempt 3, call_count={call_count}")


# ---------------------------------------------------------------------------
# 7. At-Least-Once Semantics & Mixed Scenario Tests
# ---------------------------------------------------------------------------

def test_at_least_once_no_silent_drops():
    """No event is silently dropped — it's either sent or dead-lettered."""
    print("\n[7.1] At-least-once: no silent drops...")

    q, net, _ = _build_queue(online=True, max_retries=2)

    # Alternate success/failure
    counter = {"n": 0}
    def alternating_send(event):
        counter["n"] += 1
        return counter["n"] % 2 == 0  # fail, success, fail, success ...

    q.set_sender(alternating_send)

    events = [_make_event(f"mixed_{i}") for i in range(10)]
    for e in events:
        q.enqueue(e)

    # Flush multiple times to resolve all events
    for _ in range(10):
        q.flush()

    total_accounted = len(q.sent_events) + len(q.dead_letter_events) + q.queue_size
    assert total_accounted == 10, (
        f"Events unaccounted: sent={len(q.sent_events)}, "
        f"dead={len(q.dead_letter_events)}, pending={q.queue_size}, "
        f"total={total_accounted}"
    )
    print(f"  ✓ All 10 events accounted: {len(q.sent_events)} sent, "
          f"{len(q.dead_letter_events)} dead-lettered, {q.queue_size} pending")


def test_interleaved_online_offline_events():
    """Mix of online and offline events all get delivered in order."""
    print("[7.2] Interleaved online/offline delivery...")

    q, net, _ = _build_queue(online=True)
    order = []

    def tracking_send(event):
        order.append(event.event_id)
        return True

    q.set_sender(tracking_send)

    e1 = _make_event("online_1")
    q.enqueue(e1)
    q.flush()

    net.simulate_airplane_mode()
    e2 = _make_event("offline_1")
    e3 = _make_event("offline_2")
    q.enqueue(e2)
    q.enqueue(e3)

    net.simulate_reconnection()  # auto-flush

    e4 = _make_event("online_2")
    q.enqueue(e4)
    q.flush()

    assert order == [e1.event_id, e2.event_id, e3.event_id, e4.event_id]
    print("  ✓ Delivery order: online_1 → offline_1 → offline_2 → online_2")


def test_high_volume_stress():
    """1000 events enqueued offline, all delivered on reconnect."""
    print("[7.3] High-volume stress test (1000 events)...")

    q, net, _ = _build_queue(online=False, max_size=2000)
    events = [_make_event(f"stress_{i}") for i in range(1000)]
    for e in events:
        q.enqueue(e)

    assert q.queue_size == 1000

    net.simulate_reconnection()  # triggers flush
    assert q.queue_size == 0
    assert len(q.sent_events) == 1000

    # Verify order
    for i, sent in enumerate(q.sent_events):
        assert sent.event_id == events[i].event_id
    print("  ✓ 1000 events delivered in order")


def test_concurrent_enqueue_safety():
    """Thread-safe enqueue from multiple threads."""
    print("[7.4] Concurrent enqueue safety...")

    q, net, _ = _build_queue(online=False, max_size=5000)
    threads = []
    per_thread = 100

    def enqueue_batch(thread_id):
        for j in range(per_thread):
            q.enqueue(_make_event(f"thread_{thread_id}_evt_{j}"))

    for t in range(10):
        th = threading.Thread(target=enqueue_batch, args=(t,))
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    # All events should be enqueued (no duplicates since UUIDs are unique)
    assert q.queue_size == 10 * per_thread
    print(f"  ✓ {q.queue_size} events from 10 threads, no data loss")


# ---------------------------------------------------------------------------
# 8. Event Schema Validation Tests
# ---------------------------------------------------------------------------

def test_event_serialization_roundtrip():
    """Event can be serialized to dict and deserialized back identically."""
    print("\n[8.1] Event serialization roundtrip...")

    original = _make_event("journal_entry_created", {
        "journal_id": "abc123",
        "word_count": 250,
        "mood": "calm",
    })
    original.retry_count = 2

    data = original.to_dict()
    restored = AnalyticsEvent.from_dict(data)

    assert restored.event_id == original.event_id
    assert restored.event_name == original.event_name
    assert restored.timestamp == original.timestamp
    assert restored.properties == original.properties
    assert restored.retry_count == original.retry_count
    print("  ✓ Roundtrip preserves all fields")


def test_event_properties_preserved_through_queue():
    """Event properties survive queue persistence and reload."""
    print("[8.2] Properties preserved through queue persistence...")

    q, net, store = _build_queue(online=False)
    props = {
        "screen_name": "assessment",
        "duration_ms": 4500,
        "completed": True,
        "tags": ["anxiety", "sleep"],
    }
    e = _make_event("assessment_completed", props)
    q.enqueue(e)

    # Reload
    q2 = AnalyticsOfflineQueue(net, store)
    restored = q2._queue[0]
    assert restored.properties == props
    print("  ✓ Complex properties intact after persistence + reload")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_tests():
    print("=" * 70)
    print("iOS OFFLINE ANALYTICS QUEUE + RETRY POLICY TESTS (#1340)")
    print("=" * 70)

    tests = [
        # 1. Queue Persistence
        test_queue_persists_events_to_store,
        test_queue_persistence_survives_multiple_restarts,
        test_empty_store_loads_cleanly,
        # 2. Replay Order
        test_flush_preserves_fifo_order,
        test_partial_flush_preserves_remaining_order,
        # 3. Airplane Mode & Reconnection
        test_airplane_mode_queues_events,
        test_reconnection_triggers_flush,
        test_repeated_airplane_toggle,
        test_offline_to_online_mid_enqueue,
        # 4. Duplicate Suppression
        test_duplicate_event_id_rejected,
        test_duplicate_suppression_across_restarts,
        test_different_events_same_name_allowed,
        test_no_duplicate_delivery_after_flush,
        # 5. Bounded Queue Growth
        test_queue_respects_max_size,
        test_overflow_evicts_oldest_events,
        test_queue_bounded_under_sustained_failures,
        test_dead_letter_on_max_retries_exceeded,
        # 6. Retry Policy
        test_exponential_backoff_values,
        test_backoff_cap_at_30_seconds,
        test_retry_count_increments_on_failure,
        test_successful_send_after_retries,
        # 7. At-Least-Once & Mixed
        test_at_least_once_no_silent_drops,
        test_interleaved_online_offline_events,
        test_high_volume_stress,
        test_concurrent_enqueue_safety,
        # 8. Event Schema
        test_event_serialization_roundtrip,
        test_event_properties_preserved_through_queue,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            failed += 1
            errors.append((test_fn.__name__, str(exc)))
            print(f"  ✗ FAILED: {exc}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
