"""user_funnels — add archived column (Duplicate/Archive funnel actions)

Additive only — one nullable-with-default column, safe on SQLite via
batch mode.

Revision ID: e5a9c3f7b012
Revises: c2f8a4d7e910
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5a9c3f7b012'
down_revision = 'c2f8a4d7e910'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_funnels') as batch_op:
        batch_op.add_column(sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('user_funnels') as batch_op:
        batch_op.drop_column('archived')
