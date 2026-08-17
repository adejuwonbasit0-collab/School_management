"""user preferences — add email_notifications, timezone

Backs the new fields on the Settings page (separate from the new Billing
page — see the app.dashboard.billing route). Both nullable/defaulted so
existing users aren't affected.

Revision ID: c3e8f1a5b7d9
Revises: b1f4d7a9c2e5
Create Date: 2026-08-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3e8f1a5b7d9'
down_revision = 'c6e3f8a2b915'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email_notifications', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('timezone', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('timezone')
        batch_op.drop_column('email_notifications')
