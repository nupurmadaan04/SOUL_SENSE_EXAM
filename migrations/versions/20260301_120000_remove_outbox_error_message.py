"""Remove legacy error_message column from outbox_events

Revision ID: 20260301_120000
Revises: 20260301_093000
Create Date: 2026-03-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260301_120000'
down_revision: Union[str, Sequence[str], None] = '20260301_093000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove legacy error_message column, use last_error instead."""
    # SQLite doesn't support DROP COLUMN directly, so we need to check if the column exists
    # and handle it gracefully
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if outbox_events table exists
    if 'outbox_events' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('outbox_events')]
        
        # Only drop if error_message exists
        if 'error_message' in columns:
            # For SQLite, we need to recreate the table without the column
            with op.batch_alter_table('outbox_events', schema=None) as batch_op:
                batch_op.drop_column('error_message')


def downgrade() -> None:
    """Restore error_message column for rollback compatibility."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'outbox_events' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('outbox_events')]
        
        # Only add if error_message doesn't exist
        if 'error_message' not in columns:
            with op.batch_alter_table('outbox_events', schema=None) as batch_op:
                batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))
