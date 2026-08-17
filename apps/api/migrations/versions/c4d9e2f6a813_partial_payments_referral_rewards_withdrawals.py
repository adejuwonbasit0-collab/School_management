"""add partial payments, referral reward amount, withdrawal requests

Revision ID: c4d9e2f6a813
Revises: b8f3d1a6c250
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d9e2f6a813'
down_revision = 'b8f3d1a6c250'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invoices', sa.Column('amount_paid', sa.Numeric(10, 2), server_default='0'))
    op.execute("UPDATE invoices SET amount_paid = amount WHERE status = 'paid'")

    op.add_column('referral_codes', sa.Column('reward_amount', sa.Numeric(10, 2), nullable=True))

    op.create_table(
        'withdrawal_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8)),
        sa.Column('destination', sa.String(length=400), nullable=False),  # bank details client typed in, free text
        sa.Column('status', sa.String(length=32), server_default='pending'),  # pending, approved, rejected, paid
        sa.Column('admin_note', sa.String(length=400)),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('resolved_at', sa.DateTime()),
    )
    op.create_index('ix_withdrawal_requests_user_id', 'withdrawal_requests', ['user_id'])


def downgrade():
    op.drop_index('ix_withdrawal_requests_user_id', table_name='withdrawal_requests')
    op.drop_table('withdrawal_requests')
    op.drop_column('referral_codes', 'reward_amount')
    op.drop_column('invoices', 'amount_paid')
