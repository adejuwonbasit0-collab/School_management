"""add canvas_positions to automation_workflows

Revision ID: a2c9e4f18b30
Revises: f7b1a3d0e621
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'a2c9e4f18b30'
down_revision = 'f7b1a3d0e621'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('automation_workflows', sa.Column('canvas_positions', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('automation_workflows', 'canvas_positions')
