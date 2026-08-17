"""add ai console threads/messages

Revision ID: b3d8f2a1e657
Revises: a7c1e4f6b208
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3d8f2a1e657'
down_revision = 'a7c1e4f6b208'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_console_threads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=256), server_default='New Conversation'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        'ai_console_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('thread_id', sa.Integer(), sa.ForeignKey('ai_console_threads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('ai_console_messages')
    op.drop_table('ai_console_threads')
