"""Add badge system tables

Revision ID: 20260301_130000
Revises: 
Create Date: 2026-03-01 13:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = '20260301_130000'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('milestone_type', sa.String(length=50), nullable=False),
        sa.Column('milestone_value', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_badges_name'), 'badges', ['name'], unique=True)

    op.create_table(
        'user_badges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.Column('earned_at', sa.DateTime(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('unlocked', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['badge_id'], ['badges.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_badges_user_id'), 'user_badges', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_user_badges_user_id'), table_name='user_badges')
    op.drop_table('user_badges')
    op.drop_index(op.f('ix_badges_name'), table_name='badges')
    op.drop_table('badges')
