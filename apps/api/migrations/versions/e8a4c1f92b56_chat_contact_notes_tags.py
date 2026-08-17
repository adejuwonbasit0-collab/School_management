"""add internal_notes and tags to chat_contacts

Revision ID: e8a4c1f92b56
Revises: d4e2a9c6f105
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'e8a4c1f92b56'
down_revision = 'd4e2a9c6f105'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chat_contacts', sa.Column('internal_notes', sa.Text(), nullable=True))
    op.add_column('chat_contacts', sa.Column('tags', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('chat_contacts', 'tags')
    op.drop_column('chat_contacts', 'internal_notes')
