"""add columns that exist in models but were never migrated

A full audit (every db.Column in every model, checked against every
create_table/add_column across migration history) found 24 columns across
13 tables that exist in Python model code but were never actually added
to the database. Each one silently breaks the moment it's touched:
  - leads.phone / .website / .address — every CRM lead save has been
    dropping these three fields since they were added to the Lead model
  - site_settings.organization_id — could break any new setting being saved
  - agents.tools_permissions / .model_name / .temperature / .context_window
  - and 8 more scattered across projects, broadcasts, and automation

This is the same class of bug as b91e5f2a7c33 (missing tables) — models
edited without a matching migration ever being written — just column-level
instead of table-level.

Revision ID: c48d7a1e9f56
Revises: b91e5f2a7c33
Create Date: 2026-08-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c48d7a1e9f56'
down_revision = 'b91e5f2a7c33'
branch_labels = None
depends_on = None


def _cols(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _add_column_if_missing(bind, table, column):
    """Guard every add_column here — this migration's original audit
    missed that e1f4a8c7b923 (multi-tenant organizations) already added
    organization_id to social_channels/automation_workflows/
    scheduled_broadcasts/site_settings, and that analytics_events.metadata
    already existed in the initial schema (e93cfb58aeeb). Both produced
    "duplicate column name" errors that silently blocked every migration
    after this one — this guard makes the migration safe to run
    regardless of exactly which of these 24 columns already exist on a
    given database."""
    if column.name not in _cols(bind, table):
        op.add_column(table, column)


def _fk_exists(bind, table, fk_name):
    return any(fk.get("name") == fk_name for fk in sa.inspect(bind).get_foreign_keys(table))


def upgrade():
    bind = op.get_bind()

    # analytics_events — Python attribute is event_metadata, actual SQL column is "metadata"
    _add_column_if_missing(bind, 'analytics_events', sa.Column('metadata', sa.JSON(), nullable=True))

    _add_column_if_missing(bind, 'project_requests', sa.Column('currency', sa.String(length=8), nullable=True))

    _add_column_if_missing(bind, 'client_projects', sa.Column('currency', sa.String(length=8), nullable=True))
    _add_column_if_missing(bind, 'client_projects', sa.Column('completed_at', sa.DateTime(), nullable=True))

    _add_column_if_missing(bind, 'project_meetings', sa.Column('request_id', sa.Integer(), nullable=True))
    if not _fk_exists(bind, 'project_meetings', 'fk_project_meetings_request_id'):
        with op.batch_alter_table('project_meetings') as batch_op:
            batch_op.create_foreign_key('fk_project_meetings_request_id', 'project_requests', ['request_id'], ['id'])

    _add_column_if_missing(bind, 'scheduled_broadcasts', sa.Column('organization_id', sa.Integer(), nullable=True))
    _add_column_if_missing(bind, 'scheduled_broadcasts', sa.Column('platform_meta', sa.JSON(), nullable=True))
    _add_column_if_missing(bind, 'scheduled_broadcasts', sa.Column('approval_status', sa.String(length=32), nullable=True, server_default='approved'))
    if not _fk_exists(bind, 'scheduled_broadcasts', 'fk_scheduled_broadcasts_org_id'):
        with op.batch_alter_table('scheduled_broadcasts') as batch_op:
            batch_op.create_foreign_key('fk_scheduled_broadcasts_org_id', 'organizations', ['organization_id'], ['id'])

    _add_column_if_missing(bind, 'automation_workflows', sa.Column('organization_id', sa.Integer(), nullable=True))
    _add_column_if_missing(bind, 'automation_workflows', sa.Column('client_project_id', sa.Integer(), nullable=True))
    _add_column_if_missing(bind, 'automation_workflows', sa.Column('monthly_fee', sa.Float(), nullable=True))
    if not _fk_exists(bind, 'automation_workflows', 'fk_automation_workflows_org_id'):
        with op.batch_alter_table('automation_workflows') as batch_op:
            batch_op.create_foreign_key('fk_automation_workflows_org_id', 'organizations', ['organization_id'], ['id'])
    if not _fk_exists(bind, 'automation_workflows', 'fk_automation_workflows_client_project_id'):
        with op.batch_alter_table('automation_workflows') as batch_op:
            batch_op.create_foreign_key('fk_automation_workflows_client_project_id', 'client_projects', ['client_project_id'], ['id'])

    _add_column_if_missing(bind, 'automation_runs', sa.Column('metrics', sa.JSON(), nullable=True))

    _add_column_if_missing(bind, 'leads', sa.Column('phone', sa.String(length=64), nullable=True))
    _add_column_if_missing(bind, 'leads', sa.Column('website', sa.String(length=512), nullable=True))
    _add_column_if_missing(bind, 'leads', sa.Column('address', sa.Text(), nullable=True))

    _add_column_if_missing(bind, 'social_channels', sa.Column('organization_id', sa.Integer(), nullable=True))
    _add_column_if_missing(bind, 'social_channels', sa.Column('client_project_id', sa.Integer(), nullable=True))
    _add_column_if_missing(bind, 'social_channels', sa.Column('monthly_fee', sa.Float(), nullable=True))
    if not _fk_exists(bind, 'social_channels', 'fk_social_channels_org_id'):
        with op.batch_alter_table('social_channels') as batch_op:
            batch_op.create_foreign_key('fk_social_channels_org_id', 'organizations', ['organization_id'], ['id'])
    if not _fk_exists(bind, 'social_channels', 'fk_social_channels_client_project_id'):
        with op.batch_alter_table('social_channels') as batch_op:
            batch_op.create_foreign_key('fk_social_channels_client_project_id', 'client_projects', ['client_project_id'], ['id'])

    _add_column_if_missing(bind, 'bank_transfer_payments', sa.Column('proof_image', sa.String(length=512), nullable=True))

    _add_column_if_missing(bind, 'site_settings', sa.Column('organization_id', sa.Integer(), nullable=True))
    if not _fk_exists(bind, 'site_settings', 'fk_site_settings_org_id'):
        with op.batch_alter_table('site_settings') as batch_op:
            batch_op.create_foreign_key('fk_site_settings_org_id', 'organizations', ['organization_id'], ['id'])

    _add_column_if_missing(bind, 'agents', sa.Column('tools_permissions', sa.JSON(), nullable=True))
    _add_column_if_missing(bind, 'agents', sa.Column('model_name', sa.String(length=128), nullable=True, server_default='claude-3-5-sonnet'))
    _add_column_if_missing(bind, 'agents', sa.Column('temperature', sa.Float(), nullable=True, server_default='0.7'))
    _add_column_if_missing(bind, 'agents', sa.Column('context_window', sa.Integer(), nullable=True, server_default='4000'))


def downgrade():
    # Several of these columns/FKs are also owned by e1f4a8c7b923 (which
    # runs before this migration and may have added the same ones on a
    # database where this migration ended up being a no-op for them).
    # Blindly dropping here risks removing something that migration
    # still expects to exist. Downgrading this specific migration isn't
    # meaningfully separable from that one, so this is intentionally a
    # no-op — restore from a backup instead if you need to roll back
    # past this point.
    pass
