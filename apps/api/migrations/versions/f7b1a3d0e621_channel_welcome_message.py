"""add welcome_message to social_channels

Revision ID: f7b1a3d0e621
Revises: a1a1a1a1a1a1
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7b1a3d0e621'
down_revision = 'a1a1a1a1a1a1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('social_channels', sa.Column('welcome_message', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('social_channels', 'welcome_message')
