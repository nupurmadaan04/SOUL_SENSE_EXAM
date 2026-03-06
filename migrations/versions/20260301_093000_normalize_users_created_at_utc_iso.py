"""normalize_users_created_at_utc_iso

Revision ID: 20260301_093000
Revises: f0e1d2c3b4a5
Create Date: 2026-03-01 09:30:00.000000

"""
from datetime import timezone, datetime

# Python 3.10 compatibility
UTC = timezone.utc
from typing import Optional, Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260301_093000'
down_revision: Union[str, Sequence[str], None] = 'f0e1d2c3b4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_utc_iso(value: object) -> Optional[str]:
    if value is None:
        return None

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
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
            ):
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
        parsed = parsed.replace(tzinfo=UTC)
    else:
        parsed = parsed.astimezone(UTC)

    return parsed.isoformat()


def upgrade() -> None:
    """Normalize legacy users.created_at values to strict UTC ISO 8601."""
    conn = op.get_bind()

    rows = conn.execute(sa.text("SELECT id, created_at FROM users")).mappings().all()
    for row in rows:
        normalized = _normalize_utc_iso(row["created_at"])
        if normalized is None:
            normalized = datetime.now(UTC).isoformat()

        if normalized != row["created_at"]:
            conn.execute(
                sa.text("UPDATE users SET created_at = :created_at WHERE id = :id"),
                {"id": row["id"], "created_at": normalized},
            )


def downgrade() -> None:
    """No-op: data normalization is intentionally non-reversible."""
    pass
