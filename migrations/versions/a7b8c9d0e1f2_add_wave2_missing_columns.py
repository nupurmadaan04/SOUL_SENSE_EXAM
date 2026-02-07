"""Add Wave 2 missing columns to personal_profiles, user_settings, user_strengths

Revision ID: a7b8c9d0e1f2
Revises: 026c42076d07
Create Date: 2026-02-07 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = '026c42076d07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing Wave 2 columns."""
    # personal_profiles: Wave 2 Phase 2.1 Lifestyle & Health
    with op.batch_alter_table('personal_profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('support_system', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('social_interaction_freq', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('exercise_freq', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('dietary_patterns', sa.String(), nullable=True))

    # user_settings: Wave 2 Phase 2.3 & 2.4 Calibration & Safety
    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('decision_making_style', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('risk_tolerance', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('readiness_for_change', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('advice_frequency', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('reminder_style', sa.String(), server_default='Gentle', nullable=True))
        batch_op.add_column(sa.Column('advice_boundaries', sa.Text(), server_default='[]', nullable=True))
        batch_op.add_column(sa.Column('ai_trust_level', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('data_usage_consent', sa.Boolean(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('emergency_disclaimer_accepted', sa.Boolean(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('crisis_support_preference', sa.Boolean(), server_default='1', nullable=True))

    # user_strengths: Wave 2 Phase 2.2 Goals & Vision + Calibration
    with op.batch_alter_table('user_strengths', schema=None) as batch_op:
        batch_op.add_column(sa.Column('short_term_goals', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('long_term_vision', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('primary_help_area', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('relationship_stress', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove Wave 2 columns."""
    with op.batch_alter_table('user_strengths', schema=None) as batch_op:
        batch_op.drop_column('relationship_stress')
        batch_op.drop_column('primary_help_area')
        batch_op.drop_column('long_term_vision')
        batch_op.drop_column('short_term_goals')

    with op.batch_alter_table('user_settings', schema=None) as batch_op:
        batch_op.drop_column('crisis_support_preference')
        batch_op.drop_column('emergency_disclaimer_accepted')
        batch_op.drop_column('data_usage_consent')
        batch_op.drop_column('ai_trust_level')
        batch_op.drop_column('advice_boundaries')
        batch_op.drop_column('reminder_style')
        batch_op.drop_column('advice_frequency')
        batch_op.drop_column('readiness_for_change')
        batch_op.drop_column('risk_tolerance')
        batch_op.drop_column('decision_making_style')

    with op.batch_alter_table('personal_profiles', schema=None) as batch_op:
        batch_op.drop_column('dietary_patterns')
        batch_op.drop_column('exercise_freq')
        batch_op.drop_column('social_interaction_freq')
        batch_op.drop_column('support_system')
