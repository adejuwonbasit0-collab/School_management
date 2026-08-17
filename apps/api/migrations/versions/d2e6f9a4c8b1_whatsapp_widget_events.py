"""add user_whatsapp_widget_events table (real analytics trend data)

view_count/click_count on the widget were always just running totals —
no timestamps, so no way to show activity over time. This adds a real
per-event log the new Analytics page uses for a 14-day trend chart.

Revision ID: d2e6f9a4c8b1
Revises: c1d5f8a3b620
Create Date: 2026-08-15

"""
from alembic import op
import sqlalchemy as sa


revision = 'd2e6f9a4c8b1'
down_revision = 'c1d5f8a3b620'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_whatsapp_widget_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('widget_id', sa.Integer(), sa.ForeignKey('user_whatsapp_widgets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(length=8), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_whatsapp_widget_events_widget', 'user_whatsapp_widget_events', ['widget_id', 'event_type'])


def downgrade():
    op.drop_index('ix_user_whatsapp_widget_events_widget', table_name='user_whatsapp_widget_events')
    op.drop_table('user_whatsapp_widget_events')
