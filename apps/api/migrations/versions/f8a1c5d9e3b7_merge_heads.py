"""merge heads — funnel license keys / canvas positions branch + whatsapp bot / knowledge base branch

Two divergent chains had both been extending from 9a1c2e7f5b03 in
parallel (this codebase went through two separate sessions of work at
once): the funnel license keys / canvas positions branch
(a4c7e912f8b3 -> b5d8f1a3c706) and the chatbot knowledge base /
credit store / WhatsApp Twilio connection branch (c4d8e2f1a6b9 ->
d5e9f3a2b7c1 -> b4d8e1a6c3f9 -> c7f3a9e2d5b1 -> d1a4c8f6b3e2).

`a4c7e912f8b3` itself was ALSO an attempted head-merge, but it was
generated against a migrations folder that was missing the
c4d8e2f1a6b9/d5e9f3a2b7c1 revisions, so it only merged the OLD 4 heads
that existed before those were added — recreating a fork at
9a1c2e7f5b03 instead of actually resolving it. This migration is
purely additive (no table/column changes) and just closes that fork by
merging the two real current heads.

Verified against a fresh SQLite DB: single head after this migration,
zero cycles, full chain applies cleanly with `flask_migrate.upgrade()`.

Revision ID: f8a1c5d9e3b7
Revises: b5d8f1a3c706, d1a4c8f6b3e2
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa


revision = 'f8a1c5d9e3b7'
down_revision = ('b5d8f1a3c706', 'd1a4c8f6b3e2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
