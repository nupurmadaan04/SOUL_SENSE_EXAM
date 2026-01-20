"""add_tags_to_journal_entries

Revision ID: 28f7f5014a54
Revises: 64a9bde24d3d
Create Date: 2026-01-20 12:33:31.968259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28f7f5014a54'
down_revision: Union[str, Sequence[str], None] = '64a9bde24d3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
