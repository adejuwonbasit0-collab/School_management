"""free credit refill — add free_credits_available, last_free_credit_refill

Backs the 12-hour free-credit refill system. users.credits stays the
single total balance every AI tool already deducts from; these two new
columns are just bookkeeping for how much of that total is the free
allotment (max 2, refills every 12h) vs purchased. Both nullable so
existing rows aren't touched at migration time — app/utils/credits.py
treats NULL as "never refilled, eligible now" and backfills on first
check, so existing users get their free allotment the next time their
balance is touched rather than needing a data migration.

Revision ID: e2b6d4a8f1c3
Revises: f8a1c5d9e3b7
Create Date: 2026-08-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e2b6d4a8f1c3'
down_revision = 'f8a1c5d9e3b7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('free_credits_available', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('last_free_credit_refill', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('last_free_credit_refill')
        batch_op.drop_column('free_credits_available')
