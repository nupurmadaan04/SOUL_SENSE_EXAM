"""Add environment separation columns for data hygiene

Revision ID: f0e1d2c3b4a5
Revises: 20260227_160145_add_performance_indexes
Create Date: 2026-02-28 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0e1d2c3b4a5'
down_revision: Union[str, Sequence[str], None] = '20260227_160145_add_performance_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add environment columns to analytics tables for strict environment separation."""
    
    # Add environment column to analytics_events table
    with op.batch_alter_table('analytics_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('environment', sa.String(), nullable=False, server_default='development'))
        batch_op.create_index('idx_analytics_env_timestamp', ['environment', 'timestamp'], unique=False)
        batch_op.create_index('idx_analytics_env_event', ['environment', 'event_name'], unique=False)
    
    # Add environment column to scores table
    with op.batch_alter_table('scores', schema=None) as batch_op:
        batch_op.add_column(sa.Column('environment', sa.String(), nullable=False, server_default='development'))
        batch_op.create_index('idx_score_env_timestamp', ['environment', 'timestamp'], unique=False)
    
    # Add environment column to journal_entries table
    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('environment', sa.String(), nullable=False, server_default='development'))
        batch_op.create_index('idx_journal_env_timestamp', ['environment', 'timestamp'], unique=False)


def downgrade() -> None:
    """Remove environment columns from analytics tables."""
    
    # Remove environment column from journal_entries table
    with op.batch_alter_table('journal_entries', schema=None) as batch_op:
        batch_op.drop_index('idx_journal_env_timestamp')
        batch_op.drop_column('environment')
    
    # Remove environment column from scores table
    with op.batch_alter_table('scores', schema=None) as batch_op:
        batch_op.drop_index('idx_score_env_timestamp')
        batch_op.drop_column('environment')
    
    # Remove environment column from analytics_events table
    with op.batch_alter_table('analytics_events', schema=None) as batch_op:
        batch_op.drop_index('idx_analytics_env_event')
        batch_op.drop_index('idx_analytics_env_timestamp')
        batch_op.drop_column('environment')
