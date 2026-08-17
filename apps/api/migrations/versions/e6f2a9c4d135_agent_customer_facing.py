"""add customer_facing to agents

Revision ID: e6f2a9c4d135
Revises: d5e1f8b3c927
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'e6f2a9c4d135'
down_revision = 'd5e1f8b3c927'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('agents', sa.Column('customer_facing', sa.Boolean(), server_default=sa.false()))
    op.add_column('agents', sa.Column('public_greeting', sa.String(length=400)))


def downgrade():
    op.drop_column('agents', 'public_greeting')
    op.drop_column('agents', 'customer_facing')
