"""user_funnels — add smtp_credentials_encrypted for per-funnel SMTP

Additive-only, nullable Text column, no data touched.

Revision ID: d7f4a1c8e320
Revises: c6e3f8a2b915
Create Date: 2026-08-13 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7f4a1c8e320'
down_revision = 'e7a9c3f5b1d8'
branch_labels = None
depends_on = None


def _add_column_if_missing(table, column):
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = [c["name"] for c in insp.get_columns(table)]
    if column.name not in existing:
        op.add_column(table, column)


def upgrade():
    _add_column_if_missing('user_funnels', sa.Column('smtp_credentials_encrypted', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_funnels') as batch_op:
        batch_op.drop_column('smtp_credentials_encrypted')
