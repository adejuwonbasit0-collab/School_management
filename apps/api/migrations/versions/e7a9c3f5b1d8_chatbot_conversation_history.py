"""add user_chatbot_messages table (real conversation history)

Both WhatsApp Bot and AI Chatbot only ever had a raw message_count
counter — no way to see what was actually said. This adds a real,
shared conversation log (grouped by session_id) that both tools'
dashboard pages can show, distinctly, since each queries only its own
bots' messages.

Revision ID: e7a9c3f5b1d8
Revises: d4f8a2c6e1b9
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa


revision = 'e7a9c3f5b1d8'
down_revision = 'd4f8a2c6e1b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_chatbot_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bot_id', sa.Integer(), sa.ForeignKey('user_chatbots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('sender', sa.String(length=8), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_chatbot_messages_bot_session', 'user_chatbot_messages', ['bot_id', 'session_id'])


def downgrade():
    op.drop_index('ix_user_chatbot_messages_bot_session', table_name='user_chatbot_messages')
    op.drop_table('user_chatbot_messages')
