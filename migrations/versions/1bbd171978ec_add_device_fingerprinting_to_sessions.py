"""add_device_fingerprinting_to_sessions

Revision ID: 1bbd171978ec
Revises: 9883f3a97d37
Create Date: 2026-03-02 15:44:13.667107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bbd171978ec'
down_revision: Union[str, Sequence[str], None] = '9883f3a97d37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add device fingerprinting columns to user_sessions table."""
    # Add device fingerprinting fields
    op.add_column('user_sessions', sa.Column('device_fingerprint_hash', sa.String(64), nullable=True))
    op.add_column('user_sessions', sa.Column('device_user_agent', sa.Text(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_accept_language', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_accept_encoding', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_screen_resolution', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_timezone_offset', sa.Integer(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_platform', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_plugins_hash', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_canvas_fingerprint', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_webgl_fingerprint', sa.String(), nullable=True))
    op.add_column('user_sessions', sa.Column('device_fingerprint_created_at', sa.DateTime(), nullable=True))

    # Create index on device_fingerprint_hash for performance
    op.create_index(
        'ix_user_sessions_device_fingerprint_hash',
        'user_sessions',
        ['device_fingerprint_hash'],
        unique=False
    )


def downgrade() -> None:
    """Remove device fingerprinting columns from user_sessions table."""
    # Drop index
    op.drop_index('ix_user_sessions_device_fingerprint_hash', table_name='user_sessions')

    # Drop columns
    op.drop_column('user_sessions', 'device_fingerprint_created_at')
    op.drop_column('user_sessions', 'device_webgl_fingerprint')
    op.drop_column('user_sessions', 'device_canvas_fingerprint')
    op.drop_column('user_sessions', 'device_plugins_hash')
    op.drop_column('user_sessions', 'device_platform')
    op.drop_column('user_sessions', 'device_timezone_offset')
    op.drop_column('user_sessions', 'device_screen_resolution')
    op.drop_column('user_sessions', 'device_accept_encoding')
    op.drop_column('user_sessions', 'device_accept_language')
    op.drop_column('user_sessions', 'device_user_agent')
    op.drop_column('user_sessions', 'device_fingerprint_hash')
