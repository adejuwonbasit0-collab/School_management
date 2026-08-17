"""merge heads — funnel_visits_table, whatsapp_widget_table

Pure merge, no schema changes. The real fork here was two independent
branches both descending from the funnel/payment-link work
(funnel_visits_table and whatsapp_widget_table) — reconciled into one
line. (A separate, more serious bug was fixed alongside this: two
earlier migrations, funnel_orders_table and add_funnel_page_view_count,
had been pointing at EACH OTHER as down_revision — a genuine cycle, not
just a fork — which is why the previous merge attempt at this same spot
was itself wrong and has been replaced by this one.)

Revision ID: a1b2c3d4e5f7
Revises: f6b1d4a8e293, f7a2c8e5d1b4
Create Date: 2026-08-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f7'
down_revision = ('f6b1d4a8e293', 'f7a2c8e5d1b4')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
