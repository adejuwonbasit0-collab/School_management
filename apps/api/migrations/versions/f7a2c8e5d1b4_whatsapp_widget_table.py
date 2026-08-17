"""whatsapp widget — add user_whatsapp_widgets table

Additive only: one new table for the WhatsApp Chat Widget product
(separate from the existing user_chatbots table, which backs the
WhatsApp Business Bot / AI chatbot product).

Revision ID: f7a2c8e5d1b4
Revises: e4f6a9c1b2d3
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7a2c8e5d1b4'
down_revision = 'a3c7f1e9b5d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_whatsapp_widgets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('business_name', sa.String(length=128), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('default_message', sa.Text(), nullable=True),
        sa.Column('profile_image', sa.String(length=512), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('click_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('user_whatsapp_widgets') as batch_op:
        batch_op.create_index('ix_user_whatsapp_widgets_slug', ['slug'], unique=True)


def downgrade():
    with op.batch_alter_table('user_whatsapp_widgets') as batch_op:
        batch_op.drop_index('ix_user_whatsapp_widgets_slug')
    op.drop_table('user_whatsapp_widgets')
