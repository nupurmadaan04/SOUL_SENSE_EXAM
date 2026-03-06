from datetime import timezone, datetime, timedelta
UTC = timezone.utc

from api.utils.timestamps import normalize_utc_iso, utc_now_iso


def test_normalize_utc_iso_from_naive_datetime():
    value = datetime(2026, 3, 1, 10, 0, 0)
    normalized = normalize_utc_iso(value)

    assert normalized == "2026-03-01T10:00:00+00:00"


def test_normalize_utc_iso_from_offset_datetime():
    value = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    normalized = normalize_utc_iso(value)

    assert normalized == "2026-03-01T04:30:00+00:00"


def test_normalize_utc_iso_from_zulu_string():
    normalized = normalize_utc_iso("2026-03-01T10:00:00Z")

    assert normalized == "2026-03-01T10:00:00+00:00"


def test_normalize_utc_iso_from_naive_iso_string():
    normalized = normalize_utc_iso("2026-03-01T10:00:00")

    assert normalized == "2026-03-01T10:00:00+00:00"


def test_normalize_utc_iso_fallback_now_for_invalid_values():
    normalized = normalize_utc_iso("not-a-date", fallback_now=True)

    assert normalized is not None
    assert normalized.endswith("+00:00")


def test_utc_now_iso_is_utc():
    ts = utc_now_iso()
    parsed = datetime.fromisoformat(ts)

    assert parsed.tzinfo == UTC
