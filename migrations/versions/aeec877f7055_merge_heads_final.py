"""merge_heads_final

Revision ID: aeec877f7055
Revises: 1334_emotion_tags, a1b2c3d4e5f6
Create Date: 2026-08-21 19:23:50.064181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aeec877f7055'
down_revision: Union[str, Sequence[str], None] = ('1334_emotion_tags', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
