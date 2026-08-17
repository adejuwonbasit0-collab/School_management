"""add user payment gateways

Revision ID: a1c7e9f04d3b
Revises: c48d7a1e9f56
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1c7e9f04d3b'
down_revision = 'c48d7a1e9f56'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_payment_gateways',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('gateway', sa.String(length=32), nullable=False),
        sa.Column('mode', sa.String(length=16), nullable=True),
        sa.Column('credentials_encrypted', sa.Text(), nullable=True),
        sa.Column('last4', sa.String(length=8), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'gateway', name='uq_user_payment_gateway'),
    )


def downgrade():
    op.drop_table('user_payment_gateways')
