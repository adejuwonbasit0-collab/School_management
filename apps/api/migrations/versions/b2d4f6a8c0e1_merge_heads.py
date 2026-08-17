"""merge heads — voice_generations_table + (funnel_visits/whatsapp_widget/coupon_bump merge)

Revision ID: b2d4f6a8c0e1
Revises: b8d3f6a1c407, a1b2c3d4e5f7
Create Date: 2026-08-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2d4f6a8c0e1'
down_revision = ('b8d3f6a1c407', 'a1b2c3d4e5f7')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
