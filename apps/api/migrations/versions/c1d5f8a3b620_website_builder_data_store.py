"""website builder: data_store column for the JSON collections backend

Adds `data_store` (JSON, default {}) to user_websites — a generic
key-value store of named collections (e.g. "products", "orders") that a
generated site's own JS can read/write via the new
/dashboard/sites/<slug>/data/<collection> endpoints. Only populated when
a site's AI-generated pages actually call those endpoints (e-commerce,
bookings, listings...) — an ordinary marketing/portfolio site never
touches this column.

Revision ID: c1d5f8a3b620
Revises: a7c4f9b3e102
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d5f8a3b620'
down_revision = 'a7c4f9b3e102'
branch_labels = None
depends_on = None


def _cols(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    existing = _cols(bind, "user_websites")
    if "data_store" not in existing:
        with op.batch_alter_table("user_websites") as batch_op:
            batch_op.add_column(sa.Column("data_store", sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    existing = _cols(bind, "user_websites")
    if "data_store" in existing:
        with op.batch_alter_table("user_websites") as batch_op:
            batch_op.drop_column("data_store")
