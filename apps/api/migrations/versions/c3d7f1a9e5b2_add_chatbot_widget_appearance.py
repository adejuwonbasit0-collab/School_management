"""add widget appearance settings (logo, position, animation, icon...) to user_chatbots

Extends both WhatsApp Bot and AI Chatbot's chat bubble/widget with the
same appearance customization UserWhatsAppWidget already has —
logo/avatar, position, brand color, icon, animation, button label,
desktop/mobile visibility — instead of the previous fixed, hardcoded
bubble (green, bottom-right, generic icon, no logo, no config at all).

Revision ID: c3d7f1a9e5b2
Revises: b1f4d7a9c2e5
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d7f1a9e5b2'
down_revision = 'b1f4d7a9c2e5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_chatbots', schema=None) as batch_op:
        batch_op.add_column(sa.Column('logo_url', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('widget_settings', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_chatbots', schema=None) as batch_op:
        batch_op.drop_column('widget_settings')
        batch_op.drop_column('logo_url')
