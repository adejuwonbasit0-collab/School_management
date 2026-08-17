"""add country to project_requests (Hire Me form country + currency selection)

Revision ID: c1d9f4a3e826
Revises: b8e1c4a2f715
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d9f4a3e826'
down_revision = 'b8e1c4a2f715'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('project_requests', sa.Column('country', sa.String(length=128), nullable=True))


def downgrade():
    op.drop_column('project_requests', 'country')
