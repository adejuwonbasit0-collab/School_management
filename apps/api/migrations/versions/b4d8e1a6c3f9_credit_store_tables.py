"""credit store — add credit_packages, credit_purchases, credit_transactions

Additive only: three new tables backing the AI Credit Store (admin-priced
purchasable credit packages) and the credit ledger. Does not touch the
existing users.credits column — purchases still top up that same balance,
just through a real ledger instead of an unrecorded overwrite.

Revision ID: b4d8e1a6c3f9
Revises: c4d8e2f1a6b9
Create Date: 2026-08-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b4d8e1a6c3f9'
down_revision = 'd5e9f3a2b7c1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'credit_packages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('is_popular', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('active', sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'credit_purchases',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('package_id', sa.Integer(), sa.ForeignKey('credit_packages.id'), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True, server_default='pending'),
        sa.Column('gateway', sa.String(length=32), nullable=True),
        sa.Column('gateway_ref', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('credit_purchases') as batch_op:
        batch_op.create_index('ix_credit_purchases_user_id', ['user_id'])
        batch_op.create_index('ix_credit_purchases_status', ['status'])

    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=256), nullable=True),
        sa.Column('reference', sa.String(length=128), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('credit_transactions') as batch_op:
        batch_op.create_index('ix_credit_transactions_user_id', ['user_id'])
        batch_op.create_index('ix_credit_transactions_created_at', ['created_at'])


def downgrade():
    with op.batch_alter_table('credit_transactions') as batch_op:
        batch_op.drop_index('ix_credit_transactions_created_at')
        batch_op.drop_index('ix_credit_transactions_user_id')
    op.drop_table('credit_transactions')

    with op.batch_alter_table('credit_purchases') as batch_op:
        batch_op.drop_index('ix_credit_purchases_status')
        batch_op.drop_index('ix_credit_purchases_user_id')
    op.drop_table('credit_purchases')

    op.drop_table('credit_packages')
