"""merge_heads_before_device_fingerprinting

Revision ID: 9883f3a97d37
Revises: 20260301_093000, 49d6f6cd21b6
Create Date: 2026-03-02 15:43:39.970530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9883f3a97d37'
down_revision: Union[str, Sequence[str], None] = ('20260301_093000', '49d6f6cd21b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
