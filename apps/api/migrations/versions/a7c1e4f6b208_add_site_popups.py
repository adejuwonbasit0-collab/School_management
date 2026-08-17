"""add site popups (website automation)

Revision ID: a7c1e4f6b208
Revises: f2a5c9e0d834
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7c1e4f6b208'
down_revision = 'f2a5c9e0d834'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'site_popups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('headline', sa.String(length=256), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('cta_text', sa.String(length=64), nullable=True),
        sa.Column('cta_url', sa.String(length=512), nullable=True),
        sa.Column('trigger_type', sa.String(length=16), server_default='delay'),
        sa.Column('trigger_value', sa.Integer(), server_default='5'),
        sa.Column('path_pattern', sa.String(length=256), nullable=True),
        sa.Column('frequency', sa.String(length=24), server_default='once_per_session'),
        sa.Column('active', sa.Boolean(), server_default=sa.true()),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('site_popups')
