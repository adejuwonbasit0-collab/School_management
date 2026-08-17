"""add_automation_and_content_fields

Revision ID: 4ab5ce443d46
Revises: e6f2a9c4d135
Create Date: 2026-07-24 11:39:51.334862

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ab5ce443d46'
down_revision = 'e6f2a9c4d135'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('scheduled_broadcasts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('platform_meta', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('approval_status', sa.String(length=32), nullable=True))


def downgrade():
    with op.batch_alter_table('scheduled_broadcasts', schema=None) as batch_op:
        batch_op.drop_column('approval_status')
        batch_op.drop_column('platform_meta')
