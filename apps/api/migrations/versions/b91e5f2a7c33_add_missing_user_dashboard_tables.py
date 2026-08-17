"""add missing user-dashboard premium tables

These 8 tables (user_websites, user_funnels, user_payment_links,
user_invoices, user_chatbots, premium_modules, todo_items,
user_product_access) had SQLAlchemy models defined but NO migration ever
written for them — meaning on any database that only ever ran
`flask db upgrade`, none of these tables exist. That's what was causing
the 500 error the moment anyone touched My Products, a locked product, or
any of the premium dashboard tools: the very first query against one of
these tables throws OperationalError: no such table.

Revision ID: b91e5f2a7c33
Revises: f3a8c1d92b47
Create Date: 2026-08-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b91e5f2a7c33'
down_revision = 'f3a8c1d92b47'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_websites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('slug', sa.String(length=256), nullable=True),
        sa.Column('pages', sa.JSON(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True),
        sa.Column('subdomain', sa.String(length=64), nullable=True),
        sa.Column('custom_domain', sa.String(length=256), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_websites_slug'), 'user_websites', ['slug'], unique=True)
    op.create_index(op.f('ix_user_websites_subdomain'), 'user_websites', ['subdomain'], unique=True)

    op.create_table(
        'user_funnels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('slug', sa.String(length=256), nullable=True),
        sa.Column('steps', sa.JSON(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True),
        sa.Column('subdomain', sa.String(length=64), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('conversion_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_funnels_slug'), 'user_funnels', ['slug'], unique=True)
    op.create_index(op.f('ix_user_funnels_subdomain'), 'user_funnels', ['subdomain'], unique=True)

    op.create_table(
        'user_payment_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True),
        sa.Column('payment_count', sa.Integer(), nullable=True),
        sa.Column('total_collected', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_payment_links_slug'), 'user_payment_links', ['slug'], unique=True)

    op.create_table(
        'user_invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=64), nullable=False),
        sa.Column('client_name', sa.String(length=256), nullable=True),
        sa.Column('client_email', sa.String(length=256), nullable=True),
        sa.Column('client_address', sa.Text(), nullable=True),
        sa.Column('client_phone', sa.String(length=64), nullable=True),
        sa.Column('items', sa.JSON(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tax_rate', sa.Float(), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('terms', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=512), nullable=True),
        sa.Column('business_name', sa.String(length=256), nullable=True),
        sa.Column('business_email', sa.String(length=256), nullable=True),
        sa.Column('business_address', sa.Text(), nullable=True),
        sa.Column('business_phone', sa.String(length=64), nullable=True),
        sa.Column('payment_link_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_link_id'], ['user_payment_links.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'user_chatbots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=True),
        sa.Column('greeting', sa.Text(), nullable=True),
        sa.Column('flows', sa.JSON(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('auto_replies', sa.JSON(), nullable=True),
        sa.Column('ai_enabled', sa.Boolean(), nullable=True),
        sa.Column('ai_instructions', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'premium_modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_premium_modules_slug'), 'premium_modules', ['slug'], unique=True)

    op.create_table(
        'todo_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('priority', sa.String(length=8), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('reminder_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'user_product_access',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_slug', sa.String(length=128), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'product_slug', name='uq_user_product'),
    )
    op.create_index(op.f('ix_user_product_access_product_slug'), 'user_product_access', ['product_slug'], unique=False)


def downgrade():
    op.drop_table('user_product_access')
    op.drop_table('todo_items')
    op.drop_table('premium_modules')
    op.drop_table('user_chatbots')
    op.drop_table('user_invoices')
    op.drop_table('user_payment_links')
    op.drop_table('user_funnels')
    op.drop_table('user_websites')
