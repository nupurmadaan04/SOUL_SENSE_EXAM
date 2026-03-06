from __future__ import annotations

from datetime import timezone, datetime
UTC = timezone.utc
from typing import Optional, Union


TimestampLike = Union[datetime, str]


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_timestamp(value: TimestampLike) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        if candidate.endswith("Z"):
            candidate = f"{candidate[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            parsed = None
            formats = (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
            )
            for fmt in formats:
                try:
                    parsed = datetime.strptime(candidate, fmt)
                    break
                except ValueError:
                    continue

            if parsed is None:
                return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_utc_iso(value: Optional[TimestampLike], *, fallback_now: bool = False) -> Optional[str]:
    parsed = parse_timestamp(value) if value is not None else None
    if parsed is None:
        if fallback_now:
            return utc_now_iso()
        return None
    return parsed.isoformat()
