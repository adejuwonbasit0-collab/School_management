"""funnel license keys — add funnel_license_keys table, merge heads

This does two things in one migration:

1. Creates funnel_license_keys (additive only, new table, no ALTERs on
   any existing table — carries none of the SQLite batch-ALTER risk).
2. Merges the 4 divergent heads that existed before this migration
   (f6b1d4a8e293, b8d3f6a1c407, 9a1c2e7f5b03, a1b2c3d4e5f7) back into a
   single chain via a multi-parent down_revision, same pattern as the
   earlier a1b2c3d4e5f7 merge. Without this, `flask db upgrade` cannot
   complete and this new table would never reach the database — this is
   the exact failure mode flagged in earlier work on this codebase.
   Verified against a fresh SQLite file with `seen`-set cycle detection
   before packaging (see notes at bottom of this file).

Revision ID: a4c7e912f8b3
Revises: f6b1d4a8e293, b8d3f6a1c407, 9a1c2e7f5b03, a1b2c3d4e5f7
Create Date: 2026-08-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a4c7e912f8b3'
down_revision = ('f6b1d4a8e293', 'b8d3f6a1c407', '9a1c2e7f5b03', 'a1b2c3d4e5f7')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'funnel_license_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('funnel_id', sa.Integer(), sa.ForeignKey('user_funnels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('domain', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('check_count', sa.Integer(), nullable=False, server_default='0'),
    )
    with op.batch_alter_table('funnel_license_keys') as batch_op:
        batch_op.create_index('ix_funnel_license_keys_funnel_id', ['funnel_id'])
        batch_op.create_index('ix_funnel_license_keys_user_id', ['user_id'])
        batch_op.create_unique_constraint('uq_funnel_license_keys_key', ['key'])


def downgrade():
    op.drop_table('funnel_license_keys')


# ── Verification notes (per this codebase's established practice) ──
# 1. Traced migrations/versions/ with a `seen` set from every head back
#    to the initial_schema revision — no cycles found, one clean DAG
#    once this merge lands.
# 2. `flask db upgrade` was run against a fresh throwaway SQLite file
#    (not the dev DB) up through this revision to confirm it completes
#    without error before this file was included in the batch.
