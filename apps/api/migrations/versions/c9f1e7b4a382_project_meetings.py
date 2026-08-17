"""add project_meetings table for customer meeting scheduling

Revision ID: c9f1e7b4a382
Revises: b6d3f8a2e017
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9f1e7b4a382'
down_revision = 'b6d3f8a2e017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'project_meetings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('client_projects.id'), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=512), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('project_meetings')
