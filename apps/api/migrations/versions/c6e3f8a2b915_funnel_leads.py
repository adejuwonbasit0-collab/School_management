"""funnel leads — add funnel_leads table for Form block submissions

Additive only, no ALTERs on existing tables.

Revision ID: c6e3f8a2b915
Revises: f8a1c5d9e3b7
Create Date: 2026-08-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c6e3f8a2b915'
down_revision = 'f8a1c5d9e3b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'funnel_leads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('funnel_id', sa.Integer(), sa.ForeignKey('user_funnels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_id', sa.Integer(), sa.ForeignKey('funnel_pages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('block_id', sa.String(length=64), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('source_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('funnel_leads') as batch_op:
        batch_op.create_index('ix_funnel_leads_funnel_id', ['funnel_id'])
        batch_op.create_index('ix_funnel_leads_user_id', ['user_id'])


def downgrade():
    op.drop_table('funnel_leads')
