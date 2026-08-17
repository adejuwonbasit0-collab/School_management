"""add real partners table

Revision ID: a2b4e7f9c103
Revises: f7a1b3c8d602
Create Date: 2026-07-26
"""
from alembic import op
import sqlalchemy as sa
import json

revision = 'a2b4e7f9c103'
down_revision = 'f7a1b3c8d602'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'partners',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('logo_url', sa.String(length=512), nullable=False),
        sa.Column('website', sa.String(length=512)),
        sa.Column('active', sa.Boolean(), server_default=sa.true()),
        sa.Column('order', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime()),
    )

    # Backfill: if the old site_partners_json setting has real (non-default
    # placeholder) entries, carry them over so nothing an admin actually
    # configured gets silently dropped.
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT value FROM site_settings WHERE key = 'site_partners_json' LIMIT 1")).fetchone()
    if row and row[0]:
        try:
            partners = json.loads(row[0])
        except Exception:
            partners = []
        table = sa.table('partners', sa.column('name', sa.String), sa.column('logo_url', sa.String),
                         sa.column('active', sa.Boolean), sa.column('order', sa.Integer))
        for i, p in enumerate(partners):
            if isinstance(p, dict) and p.get('name') and p.get('logo'):
                conn.execute(table.insert().values(name=p['name'], logo_url=p['logo'], active=True, order=i))


def downgrade():
    op.drop_table('partners')
