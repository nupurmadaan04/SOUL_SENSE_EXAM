"""add_updated_at_to_journal_entries

Revision ID: 1330_journal_edit
Revises: 679f6276cf18
Create Date: 2026-03-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

UTC = timezone.utc

# revision identifiers, used by Alembic.
revision: str = '1330_journal_edit'
down_revision: Union[str, Sequence[str], None] = '679f6276cf18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Add updated_at field to journal_entries table for tracking edits (Issue #1330)."""
    
    # Add updated_at column to journal_entries table
    with op.batch_alter_table('journal_entries') as batch_op:
        batch_op.add_column(
            sa.Column('updated_at', sa.String(), 
                     default=lambda: datetime.now(UTC).isoformat(), 
                     nullable=True)
        )
        # Add index for efficient sorting by updated_at
        batch_op.create_index('idx_journal_updated_at', ['updated_at'])


def downgrade() -> None:
    """Downgrade schema: Remove updated_at field from journal_entries table."""
    
    with op.batch_alter_table('journal_entries') as batch_op:
        batch_op.drop_index('idx_journal_updated_at')
        batch_op.drop_column('updated_at')
