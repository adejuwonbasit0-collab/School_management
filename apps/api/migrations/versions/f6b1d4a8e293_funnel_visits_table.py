"""funnel_visits table — real analytics (visits over time, device, referrer)

Additive only — new table, no changes to existing ones.

Revision ID: f6b1d4a8e293
Revises: e5a9c3f7b012
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6b1d4a8e293'
down_revision = 'e5a9c3f7b012'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'funnel_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('funnel_id', sa.Integer(), nullable=False),
        sa.Column('page_id', sa.Integer(), nullable=True),
        sa.Column('referrer', sa.String(length=512), nullable=True),
        sa.Column('device', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['funnel_id'], ['user_funnels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['page_id'], ['funnel_pages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_funnel_visits_funnel_id', 'funnel_visits', ['funnel_id'])
    op.create_index('ix_funnel_visits_created_at', 'funnel_visits', ['created_at'])


def downgrade():
    op.drop_index('ix_funnel_visits_created_at', table_name='funnel_visits')
    op.drop_index('ix_funnel_visits_funnel_id', table_name='funnel_visits')
    op.drop_table('funnel_visits')
