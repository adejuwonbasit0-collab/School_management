"""whatsapp bot display phone — add display_phone

The WhatsApp Bot builder's click-to-chat link / floating bubble generator
had a phone number input that was never actually sent to the backend
(UserChatbot had no matching column), so it reset every time the page
reloaded. This adds the column and the save/load wiring makes it stick.

Revision ID: d1a4c8f6b3e2
Revises: c7f3a9e2d5b1
Create Date: 2026-08-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd1a4c8f6b3e2'
down_revision = 'c7f3a9e2d5b1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_chatbots') as batch_op:
        batch_op.add_column(sa.Column('display_phone', sa.String(length=32), nullable=True))


def downgrade():
    with op.batch_alter_table('user_chatbots') as batch_op:
        batch_op.drop_column('display_phone')
