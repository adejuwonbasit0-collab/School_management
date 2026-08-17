"""add workflow_templates table

Revision ID: b25d8f4e9a67
Revises: a91c5e2f7d43
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'b25d8f4e9a67'
down_revision = 'a91c5e2f7d43'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'workflow_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(length=64), nullable=False),
        sa.Column('actions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )


def downgrade():
    op.drop_table('workflow_templates')
