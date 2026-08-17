"""payment links — add user_payment_link_orders table

Additive only: creates one new table for real, individual transactions
against a UserPaymentLink (previously only aggregate payment_count/
total_collected counters existed on the link itself, with no per-order
or per-customer record at all). Does not touch any existing table, so
it carries none of the SQLite batch-ALTER risk that migrations altering
existing tables do.

Revision ID: e4f6a9c1b2d3
Revises: c2f8a4d7e910
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f6a9c1b2d3'
down_revision = 'c2f8a4d7e910'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_payment_link_orders',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('payment_link_id', sa.Integer(), sa.ForeignKey('user_payment_links.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('buyer_name', sa.String(length=256), nullable=True),
        sa.Column('buyer_email', sa.String(length=256), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('gateway', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False, server_default='pending'),
        sa.Column('reference', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('user_payment_link_orders') as batch_op:
        batch_op.create_index('ix_user_payment_link_orders_payment_link_id', ['payment_link_id'])
        batch_op.create_index('ix_user_payment_link_orders_user_id', ['user_id'])
        batch_op.create_index('ix_user_payment_link_orders_buyer_email', ['buyer_email'])
        batch_op.create_index('ix_user_payment_link_orders_status', ['status'])
        batch_op.create_index('ix_user_payment_link_orders_reference', ['reference'])
        batch_op.create_index('ix_user_payment_link_orders_created_at', ['created_at'])


def downgrade():
    with op.batch_alter_table('user_payment_link_orders') as batch_op:
        batch_op.drop_index('ix_user_payment_link_orders_created_at')
        batch_op.drop_index('ix_user_payment_link_orders_reference')
        batch_op.drop_index('ix_user_payment_link_orders_status')
        batch_op.drop_index('ix_user_payment_link_orders_buyer_email')
        batch_op.drop_index('ix_user_payment_link_orders_user_id')
        batch_op.drop_index('ix_user_payment_link_orders_payment_link_id')
    op.drop_table('user_payment_link_orders')
