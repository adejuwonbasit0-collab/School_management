"""add payment links

Revision ID: f3a8c1d92b47
Revises: c1d9f4a3e826
Create Date: 2026-08-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3a8c1d92b47'
down_revision = 'c1d9f4a3e826'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'payment_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=512), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('allowed_methods', sa.JSON(), nullable=True),
        sa.Column('wave_instructions', sa.Text(), nullable=True),
        sa.Column('payoneer_instructions', sa.Text(), nullable=True),
        sa.Column('thank_you_message', sa.Text(), nullable=True),
        sa.Column('redirect_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_payment_links_slug'), 'payment_links', ['slug'], unique=True)

    op.create_table(
        'payment_link_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_link_id', sa.Integer(), nullable=False),
        sa.Column('payer_name', sa.String(length=200), nullable=True),
        sa.Column('payer_email', sa.String(length=200), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('gateway', sa.String(length=24), nullable=True),
        sa.Column('gateway_ref', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('sender_reference', sa.String(length=256), nullable=True),
        sa.Column('proof_image', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['payment_link_id'], ['payment_links.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('payment_link_payments')
    op.drop_index(op.f('ix_payment_links_slug'), table_name='payment_links')
    op.drop_table('payment_links')
