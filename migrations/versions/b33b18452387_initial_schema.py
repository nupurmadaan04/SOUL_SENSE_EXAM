"""Initial schema

Revision ID: b33b18452387
Revises: 
Create Date: 2026-01-07 12:03:39.917326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b33b18452387'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # --- JOURNAL ENTRIES ---
    if 'journal_entries' not in tables:
        op.create_table('journal_entries',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('username', sa.String(), nullable=True),
            sa.Column('entry_date', sa.String(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('sentiment_score', sa.Float(), nullable=True),
            sa.Column('emotional_patterns', sa.Text(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    # --- USERS ---
    if 'users' not in tables:
        op.create_table('users',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('username', sa.String(), nullable=False, unique=True),
            sa.Column('password_hash', sa.String(), nullable=False),
            sa.Column('created_at', sa.String(), nullable=True),
            sa.Column('last_login', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        # Apply legacy fixes if table exists
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('username', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=False)
            batch_op.alter_column('password_hash', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=False)
            batch_op.alter_column('created_at', existing_type=sa.TEXT(), type_=sa.String(), nullable=True)
            batch_op.alter_column('last_login', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)


    # --- SCORES ---
    if 'scores' not in tables:
        op.create_table('scores',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('username', sa.String(), nullable=True),
            sa.Column('total_score', sa.Integer(), nullable=True),
            sa.Column('age', sa.Integer(), nullable=True),
            sa.Column('detailed_age_group', sa.String(), nullable=True),
            sa.Column('timestamp', sa.String(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        with op.batch_alter_table('scores') as batch_op:
            batch_op.alter_column('username', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.alter_column('detailed_age_group', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            # Add FK if missing is tricky in sqlite, assuming batch mode handles it or it's fine
            batch_op.create_foreign_key("fk_scores_users", 'users', ['user_id'], ['id'])


    # --- RESPONSES ---
    if 'responses' not in tables:
        op.create_table('responses',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('username', sa.String(), nullable=True),
            sa.Column('question_id', sa.Integer(), nullable=True),
            sa.Column('response_value', sa.Integer(), nullable=True),
            sa.Column('age_group', sa.String(), nullable=True),
            sa.Column('detailed_age_group', sa.String(), nullable=True),
            sa.Column('timestamp', sa.String(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        with op.batch_alter_table('responses') as batch_op:
            batch_op.alter_column('username', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.alter_column('age_group', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.alter_column('detailed_age_group', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.alter_column('timestamp', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.create_foreign_key("fk_responses_users", 'users', ['user_id'], ['id'])


    # --- QUESTION CATEGORY ---
    if 'question_category' not in tables:
         op.create_table('question_category',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        with op.batch_alter_table('question_category') as batch_op:
            batch_op.alter_column('name', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=False)


    # --- QUESTION BANK ---
    if 'question_bank' not in tables:
        op.create_table('question_bank',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('question_text', sa.Text(), nullable=False),
            sa.Column('category_id', sa.Integer(), default=0),
            sa.Column('difficulty', sa.Integer(), default=1),
            sa.Column('min_age', sa.Integer(), default=0),
            sa.Column('max_age', sa.Integer(), default=120),
            sa.Column('weight', sa.Float(), default=1.0),
            sa.Column('is_active', sa.Integer(), default=1),
            sa.Column('tooltip', sa.Text(), nullable=True),
            sa.Column('created_at', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        # Legacy fixes
        with op.batch_alter_table('question_bank') as batch_op:
            batch_op.alter_column('weight', existing_type=sa.REAL(), type_=sa.Float(), existing_nullable=True, existing_server_default=sa.text('(1.0)'))
            batch_op.alter_column('created_at', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)


    # --- QUESTION METADATA ---
    if 'question_metadata' not in tables:
        op.create_table('question_metadata',
            sa.Column('question_id', sa.Integer(), nullable=False), # Primary key in model
            sa.Column('source', sa.String(), nullable=True),
            sa.Column('version', sa.String(), nullable=True),
            sa.Column('tags', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('question_id')
        )
    else:
        with op.batch_alter_table('question_metadata') as batch_op:
            batch_op.alter_column('source', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.alter_column('version', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)
            batch_op.alter_column('tags', existing_type=sa.TEXT(), type_=sa.String(), existing_nullable=True)



def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('last_login', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('created_at', existing_type=sa.String(), type_=sa.TEXT(), nullable=False)
        batch_op.alter_column('password_hash', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=False)
        batch_op.alter_column('username', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=False)
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)

    with op.batch_alter_table('scores') as batch_op:
        batch_op.drop_constraint("fk_scores_users", type_='foreignkey')
        batch_op.alter_column('detailed_age_group', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('username', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)

    with op.batch_alter_table('responses') as batch_op:
        batch_op.drop_constraint("fk_responses_users", type_='foreignkey')
        batch_op.alter_column('timestamp', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('detailed_age_group', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('age_group', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('username', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)

    with op.batch_alter_table('question_metadata') as batch_op:
        batch_op.create_foreign_key("fk_metadata_bank", 'question_bank', ['question_id'], ['id'])
        batch_op.alter_column('tags', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)

        batch_op.alter_column('version', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('source', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('question_id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)

    with op.batch_alter_table('question_category') as batch_op:
        batch_op.alter_column('name', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=False)
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)

    with op.batch_alter_table('question_bank') as batch_op:
        batch_op.create_foreign_key("fk_bank_category", 'question_category', ['category_id'], ['id'])
        batch_op.alter_column('created_at', existing_type=sa.String(), type_=sa.TEXT(), existing_nullable=True)
        batch_op.alter_column('weight', existing_type=sa.Float(), type_=sa.REAL(), existing_nullable=True, existing_server_default=sa.text('(1.0)'))
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)

    op.drop_table('journal_entries')
    # ### end Alembic commands ###
