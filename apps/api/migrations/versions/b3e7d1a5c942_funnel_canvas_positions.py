"""user_funnels — add canvas_positions for Flow Builder node layout

Additive-only, nullable JSON column. Uses _add_column_if_missing so this
is safe to re-run on a DB that somehow already has the column.

Revision ID: b3e7d1a5c942
Revises: d2e6f9a4c8b1
Create Date: 2026-08-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3e7d1a5c942'
down_revision = 'd2e6f9a4c8b1'
branch_labels = None
depends_on = None


def _add_column_if_missing(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = [c["name"] for c in insp.get_columns(table)]
    if column.name not in existing:
        op.add_column(table, column)


def upgrade():
    _add_column_if_missing('user_funnels', sa.Column('canvas_positions', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_funnels') as batch_op:
        batch_op.drop_column('canvas_positions')
