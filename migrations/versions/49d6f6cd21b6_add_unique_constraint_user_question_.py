"""add_unique_constraint_user_question_responses

Revision ID: 49d6f6cd21b6
Revises: 20260227_160145
Create Date: 2026-02-27 21:31:44.003324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49d6f6cd21b6'
down_revision: Union[str, Sequence[str], None] = '20260227_160145'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unique constraint on (user_id, question_id) for responses table
    op.create_unique_constraint(
        'uq_response_user_question',
        'responses',
        ['user_id', 'question_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the unique constraint
    op.drop_constraint('uq_response_user_question', 'responses', type_='unique')
