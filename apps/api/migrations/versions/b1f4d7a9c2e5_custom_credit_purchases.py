"""custom credit purchases — make credit_purchases.package_id nullable

Backs the dashboard's "Buy Credits" quantity stepper (N x 10 credits at
an admin-set price per unit), which isn't tied to a fixed CreditPackage
row. package_id stays populated for purchases made from a package card;
NULL means the customer used the stepper instead. credits/amount are
still always snapshotted directly on the purchase row either way, so
this doesn't change how existing package purchases are read.

Revision ID: b1f4d7a9c2e5
Revises: a9c3e7f2b154
Create Date: 2026-08-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b1f4d7a9c2e5'
down_revision = 'a9c3e7f2b154'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('credit_purchases') as batch_op:
        batch_op.alter_column('package_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table('credit_purchases') as batch_op:
        batch_op.alter_column('package_id', existing_type=sa.Integer(), nullable=False)
