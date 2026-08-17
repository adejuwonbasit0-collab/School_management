"""add scraped_site_items for website importer persistence

Revision ID: f7a1b3c8d602
Revises: 4ab5ce443d46
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7a1b3c8d602'
down_revision = '4ab5ce443d46'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scraped_site_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('client_projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('name', sa.String(length=256)),
        sa.Column('description', sa.Text()),
        sa.Column('price', sa.String(length=64)),
        sa.Column('image_url', sa.String(length=512)),
        sa.Column('video_url', sa.String(length=512)),
        sa.Column('link', sa.String(length=512)),
        sa.Column('kind', sa.String(length=32), server_default='product'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_scraped_site_items_project_id', 'scraped_site_items', ['project_id'])


def downgrade():
    op.drop_index('ix_scraped_site_items_project_id', table_name='scraped_site_items')
    op.drop_table('scraped_site_items')
