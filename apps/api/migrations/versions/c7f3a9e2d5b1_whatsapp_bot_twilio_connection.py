"""whatsapp bot per-user twilio connection — add whatsapp_credentials_encrypted

Lets each customer connect their OWN Twilio WhatsApp sender to their own
UserChatbot, instead of everyone sharing the single site-wide Admin ->
Settings -> Twilio config (which only ever answers with one global agent).
Additive only — one nullable column.

Revision ID: c7f3a9e2d5b1
Revises: b4d8e1a6c3f9
Create Date: 2026-08-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c7f3a9e2d5b1'
down_revision = 'b4d8e1a6c3f9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_chatbots') as batch_op:
        batch_op.add_column(sa.Column('whatsapp_credentials_encrypted', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('user_chatbots') as batch_op:
        batch_op.drop_column('whatsapp_credentials_encrypted')
