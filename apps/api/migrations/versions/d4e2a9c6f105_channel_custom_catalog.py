"""add custom_catalog to social_channels for per-customer bot product lists

Revision ID: d4e2a9c6f105
Revises: c9f1e7b4a382
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e2a9c6f105'
down_revision = 'c9f1e7b4a382'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('social_channels', sa.Column('custom_catalog', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('social_channels', 'custom_catalog')
