"""add email OTP as an alternative 2FA method

Revision ID: b8e1c4a2f715
Revises: a2b4e7f9c103
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8e1c4a2f715'
down_revision = 'a2b4e7f9c103'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email_2fa_enabled', sa.Boolean(), server_default=sa.false()))


def downgrade():
    op.drop_column('users', 'email_2fa_enabled')
