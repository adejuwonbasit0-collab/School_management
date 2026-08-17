"""add funnel page view_count

Revision ID: d2e8f1a5c9b3
Revises: b7d4e1a2c8f0
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd2e8f1a5c9b3'
down_revision = 'b7d4e1a2c8f0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('funnel_pages', sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('funnel_pages', 'view_count')
