"""add knowledge_sources (website/document ingestion) to user_chatbots

Revision ID: d5e9f3a2b7c1
Revises: c4d8e2f1a6b9
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'd5e9f3a2b7c1'
down_revision = 'c4d8e2f1a6b9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_chatbots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('knowledge_sources', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_chatbots', schema=None) as batch_op:
        batch_op.drop_column('knowledge_sources')
