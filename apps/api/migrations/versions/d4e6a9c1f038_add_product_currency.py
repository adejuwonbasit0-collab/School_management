"""add currency to products

Revision ID: d4e6a9c1f038
Revises: b3d8f2a1e657
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e6a9c1f038'
down_revision = 'b3d8f2a1e657'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('currency', sa.String(length=8), nullable=True))
    # Backfill existing products with the site's current default currency so
    # nothing ends up with a blank currency after this migration runs.
    op.execute("UPDATE products SET currency = 'USD' WHERE currency IS NULL")


def downgrade():
    op.drop_column('products', 'currency')
