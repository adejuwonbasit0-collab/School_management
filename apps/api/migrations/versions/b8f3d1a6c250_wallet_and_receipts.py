"""add wallet and receipt system

Revision ID: b8f3d1a6c250
Revises: a1c7e5b2f904
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8f3d1a6c250'
down_revision = 'a1c7e5b2f904'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'wallets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('balance', sa.Numeric(10, 2), server_default='0'),
        sa.Column('pending_balance', sa.Numeric(10, 2), server_default='0'),
        sa.Column('currency', sa.String(length=8)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'wallet_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('wallet_id', sa.Integer(), sa.ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('note', sa.String(length=400)),
        sa.Column('reference', sa.String(length=128)),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_wallet_transactions_wallet_id', 'wallet_transactions', ['wallet_id'])

    op.create_table(
        'receipts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_id', sa.Integer(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('reference', sa.String(length=32), nullable=False, unique=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8)),
        sa.Column('payment_method', sa.String(length=64)),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_receipts_reference', 'receipts', ['reference'])


def downgrade():
    op.drop_index('ix_receipts_reference', table_name='receipts')
    op.drop_table('receipts')
    op.drop_index('ix_wallet_transactions_wallet_id', table_name='wallet_transactions')
    op.drop_table('wallet_transactions')
    op.drop_table('wallets')
