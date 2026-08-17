"""merge heads — chatbot widget appearance branch + user preferences/funnel leads branch

`funnel_leads` (c6e3f8a2b915) was generated with down_revision = None,
creating a second disconnected migration root instead of chaining onto
the real current head — the same class of bug as the earlier
a4c7e912f8b3 fork (a session working from a migrations folder that
didn't have the latest files). `user_preferences` (c3e8f1a5b7d9) then
built on top of that orphan root. This migration is purely additive (no
table/column changes) and closes the fork by merging the two real
current heads.

Verified against a fresh SQLite DB: single head after this migration,
zero cycles, full chain applies cleanly with `flask_migrate.upgrade()`.

Revision ID: d4f8a2c6e1b9
Revises: c3d7f1a9e5b2, c3e8f1a5b7d9
Create Date: 2026-08-13

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f8a2c6e1b9'
down_revision = ('c3d7f1a9e5b2', 'c3e8f1a5b7d9')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
