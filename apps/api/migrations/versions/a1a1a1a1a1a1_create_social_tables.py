"""create social_channels chat_contacts and chat_messages tables

Revision ID: a1a1a1a1a1a1
Revises: d4a6f023c9b5
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1a1a1a1a1a1'
down_revision = 'd4a6f023c9b5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'social_channels',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('platform', sa.String(length=16), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False),
        sa.Column('credentials', sa.JSON(), nullable=True),
        sa.Column('webhook_secret', sa.String(length=64), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True, default=True),
        sa.Column('connected', sa.Boolean(), nullable=True, default=False),
        sa.Column('connection_error', sa.Text(), nullable=True),
        sa.Column('fallback_reply', sa.Text(), nullable=True),
        sa.Column('human_takeover_keywords', sa.JSON(), nullable=True),
        sa.Column('auto_reply_rules', sa.JSON(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_social_channels_webhook_secret', 'social_channels', ['webhook_secret'], unique=True)

    op.create_table(
        'chat_contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('social_channels.id'), nullable=False),
        sa.Column('external_id', sa.String(length=128), nullable=False),
        sa.Column('display_name', sa.String(length=128), nullable=True),
        sa.Column('human_takeover', sa.Boolean(), nullable=True, default=False),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('channel_id', 'external_id', name='uq_channel_contact'),
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('chat_contacts.id'), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('sent_by', sa.String(length=16), nullable=True, default='bot'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('chat_messages')
    op.drop_table('chat_contacts')
    op.drop_index('ix_social_channels_webhook_secret', table_name='social_channels')
    op.drop_table('social_channels')
