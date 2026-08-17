"""add ai agent mode + inbox department/sentiment

Revision ID: a91c5e2f7d43
Revises: f3b7d0e5c214
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'a91c5e2f7d43'
down_revision = 'f3b7d0e5c214'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('social_channels', sa.Column('ai_agent_enabled', sa.Boolean(), nullable=True))
    op.add_column('social_channels', sa.Column('ai_agent_instructions', sa.Text(), nullable=True))
    op.add_column('social_channels', sa.Column('ai_agent_temperature', sa.Float(), nullable=True))
    op.add_column('chat_contacts', sa.Column('department', sa.String(length=32), nullable=True))
    op.add_column('chat_contacts', sa.Column('sentiment', sa.String(length=16), nullable=True))


def downgrade():
    op.drop_column('chat_contacts', 'sentiment')
    op.drop_column('chat_contacts', 'department')
    op.drop_column('social_channels', 'ai_agent_temperature')
    op.drop_column('social_channels', 'ai_agent_instructions')
    op.drop_column('social_channels', 'ai_agent_enabled')
