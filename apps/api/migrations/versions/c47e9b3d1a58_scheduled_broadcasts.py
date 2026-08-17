"""add scheduled_broadcasts table for Content Studio scheduling

Revision ID: c47e9b3d1a58
Revises: b25d8f4e9a67
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'c47e9b3d1a58'
down_revision = 'b25d8f4e9a67'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scheduled_broadcasts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('social_channels.id'), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('sent_count', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('scheduled_broadcasts')
