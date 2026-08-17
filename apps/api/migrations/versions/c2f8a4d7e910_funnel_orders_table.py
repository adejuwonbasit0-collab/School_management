"""funnel checkout — add funnel_orders table

Additive only: creates one new table for orders placed through a
funnel's Checkout-type page. Does not touch any existing table, so it
carries none of the SQLite batch-ALTER risk that migrations altering
existing tables do.

Revision ID: c2f8a4d7e910
Revises: b7d4e1a2c8f0
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c2f8a4d7e910'
down_revision = 'd2e8f1a5c9b3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'funnel_orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('funnel_id', sa.Integer(), sa.ForeignKey('user_funnels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_id', sa.Integer(), sa.ForeignKey('funnel_pages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('customer_name', sa.String(length=256), nullable=True),
        sa.Column('customer_email', sa.String(length=256), nullable=True),
        sa.Column('product_name', sa.String(length=256), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('gateway', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('gateway_reference', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('funnel_orders') as batch_op:
        batch_op.create_index('ix_funnel_orders_funnel_id', ['funnel_id'])
        batch_op.create_index('ix_funnel_orders_user_id', ['user_id'])


def downgrade():
    op.drop_table('funnel_orders')
