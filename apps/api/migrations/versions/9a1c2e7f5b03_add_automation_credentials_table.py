"""add automation_credentials table

Revision ID: 9a1c2e7f5b03
Revises: 7f7ff944034d
Create Date: 2026-08-10

"""
from alembic import op
import sqlalchemy as sa


revision = '9a1c2e7f5b03'
down_revision = '7f7ff944034d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'automation_credentials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False),
        sa.Column('encrypted_data', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('last_tested_at', sa.DateTime(), nullable=True),
        sa.Column('last_test_ok', sa.Boolean(), nullable=True),
        sa.Column('last_test_message', sa.String(length=256), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
    )


def downgrade():
    op.drop_table('automation_credentials')
