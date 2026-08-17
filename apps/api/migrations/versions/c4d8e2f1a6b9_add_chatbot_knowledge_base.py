"""add knowledge base fields to user_chatbots

Revision ID: c4d8e2f1a6b9
Revises: 9a1c2e7f5b03
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d8e2f1a6b9'
down_revision = '9a1c2e7f5b03'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_chatbots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('faqs', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('knowledge_text', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('unknown_reply', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_chatbots', schema=None) as batch_op:
        batch_op.drop_column('unknown_reply')
        batch_op.drop_column('knowledge_text')
        batch_op.drop_column('faqs')
