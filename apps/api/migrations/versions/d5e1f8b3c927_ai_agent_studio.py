"""add AI agent studio (agents + agent_messages)

Revision ID: d5e1f8b3c927
Revises: c4d9e2f6a813
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e1f8b3c927'
down_revision = 'c4d9e2f6a813'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('avatar_emoji', sa.String(length=8), server_default='🤖'),
        sa.Column('role', sa.String(length=128)),
        sa.Column('department', sa.String(length=64)),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    op.create_table(
        'agent_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('agent_id', sa.Integer(), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_agent_messages_agent_id', 'agent_messages', ['agent_id'])


def downgrade():
    op.drop_index('ix_agent_messages_agent_id', table_name='agent_messages')
    op.drop_table('agent_messages')
    op.drop_table('agents')
