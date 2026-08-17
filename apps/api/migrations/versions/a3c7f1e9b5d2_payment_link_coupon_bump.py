"""payment link orders — add coupon + order bump tracking

Revision ID: a3c7f1e9b5d2
Revises: f6b1d4a8e293
Create Date: 2026-08-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a3c7f1e9b5d2'
down_revision = 'e4f6a9c1b2d3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_payment_link_orders') as batch_op:
        batch_op.add_column(sa.Column('coupon_code', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('order_bump_applied', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_payment_link_orders') as batch_op:
        batch_op.drop_column('order_bump_applied')
        batch_op.drop_column('coupon_code')
