"""add_emotion_tags_support

Revision ID: 1334_emotion_tags
Revises: 1330_journal_edit
Create Date: 2026-03-07 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1334_emotion_tags'
down_revision: Union[str, Sequence[str], None] = '1330_journal_edit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add index for efficient tag-based filtering (Issue #1334)."""
    
    # Add index on tags column for efficient tag-based filtering
    with op.batch_alter_table('journal_entries') as batch_op:
        # Create index for tag filtering (Issue #1334)
        try:
            batch_op.create_index('idx_journal_tags', ['tags'])
        except Exception:
            # Index might already exist
            pass


def downgrade() -> None:
    """Downgrade schema: Remove tag index."""
    
    with op.batch_alter_table('journal_entries') as batch_op:
        try:
            batch_op.drop_index('idx_journal_tags')
        except Exception:
            # Index might not exist
            pass
