"""add_step_up_tokens_table

Revision ID: a1b2c3d4e5f6
Revises: 1bbd171978ec
Create Date: 2026-03-02 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '1bbd171978ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create step_up_tokens table for privileged action authentication."""
    # Create step_up_tokens table
    op.create_table(
        'step_up_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

    # Create indexes for performance
    op.create_index('idx_stepup_user_session', 'step_up_tokens', ['user_id', 'session_id'], unique=False)
    op.create_index('idx_stepup_expires', 'step_up_tokens', ['expires_at'], unique=False)
    op.create_index('idx_stepup_token_used', 'step_up_tokens', ['token', 'is_used'], unique=False)


def downgrade() -> None:
    """Drop step_up_tokens table."""
    # Drop indexes
    op.drop_index('idx_stepup_token_used', table_name='step_up_tokens')
    op.drop_index('idx_stepup_expires', table_name='step_up_tokens')
    op.drop_index('idx_stepup_user_session', table_name='step_up_tokens')

    # Drop table
    op.drop_table('step_up_tokens')