"""add referral system and lead pipeline stage/value

Revision ID: f3b7d0e5c214
Revises: e8a4c1f92b56
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3b7d0e5c214'
down_revision = 'e8a4c1f92b56'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'referral_codes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=True),
        sa.Column('owner_email', sa.String(length=256), nullable=True),
        sa.Column('reward_note', sa.String(length=256), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('code', name='uq_referral_codes_code')
    )
    op.create_index('ix_referral_codes_code', 'referral_codes', ['code'])

    op.create_table(
        'referral_signups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('referral_code_id', sa.Integer(), sa.ForeignKey('referral_codes.id'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('email', sa.String(length=256), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=True),
        sa.Column('converted', sa.Boolean(), nullable=True),
        sa.Column('reward_paid', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.add_column('leads', sa.Column('deal_stage', sa.String(length=16), nullable=True))
    op.add_column('leads', sa.Column('deal_value', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('leads', 'deal_value')
    op.drop_column('leads', 'deal_stage')
    op.drop_table('referral_signups')
    op.drop_index('ix_referral_codes_code', table_name='referral_codes')
    op.drop_table('referral_codes')
