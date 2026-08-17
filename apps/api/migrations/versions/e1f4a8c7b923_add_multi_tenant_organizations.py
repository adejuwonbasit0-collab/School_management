"""add multi-tenant organizations

Revision ID: e1f4a8c7b923
Revises: d68f2a7c5e91
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = 'e1f4a8c7b923'
down_revision = 'd68f2a7c5e91'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('plan', sa.String(length=32), server_default='free'),
        sa.Column('active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    op.create_table(
        'organization_members',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(),
                   sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_role', sa.String(length=32), server_default='owner'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
    )

    # Tenant-scope the modules clients were actually blocked on: bots,
    # workflows, broadcasts, and settings (AI keys / integration credentials).
    with op.batch_alter_table('social_channels') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(),
            sa.ForeignKey('organizations.id', name='fk_social_channels_organization_id'), nullable=True))
    with op.batch_alter_table('automation_workflows') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(),
            sa.ForeignKey('organizations.id', name='fk_automation_workflows_organization_id'), nullable=True))
    with op.batch_alter_table('scheduled_broadcasts') as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(),
            sa.ForeignKey('organizations.id', name='fk_scheduled_broadcasts_organization_id'), nullable=True))
    with op.batch_alter_table('site_settings') as batch_op:
        # NULL organization_id = a platform-level/global setting (used as the
        # fallback default); a non-null value is that org's own override —
        # e.g. its own Anthropic/Gemini key, its own Google service account.
        batch_op.add_column(sa.Column('organization_id', sa.Integer(),
            sa.ForeignKey('organizations.id', name='fk_site_settings_organization_id'), nullable=True))

    # `key` used to be globally unique — that breaks multi-tenancy (two
    # orgs both needing their own "anthropic_api_key" row). Replace the
    # single-column uniqueness with a per-organization one.
    # NOTE: SQLite can't ALTER a constraint directly ("No support for ALTER
    # of constraints in SQLite dialect") — it has to go through batch mode
    # (copy-and-move), same as the add_column calls above. The original
    # version of this migration called op.create_unique_constraint() bare,
    # which works on Postgres/MySQL but silently blocks every migration
    # after it on SQLite. Fixed by moving it into batch mode.
    with op.batch_alter_table('site_settings') as batch_op:
        try:
            batch_op.drop_index('ix_site_settings_key')
        except Exception:
            pass
        batch_op.create_index('ix_site_settings_key', ['key'])
        batch_op.create_unique_constraint('uq_setting_org_key', ['organization_id', 'key'])

    # ── Backfill: everything that already existed becomes Organization #1,
    # owned by whichever user has the 'admin' role — so nothing that was
    # working before this migration breaks or goes invisible.
    conn = op.get_bind()
    now = datetime.utcnow()
    result = conn.execute(sa.text(
        "SELECT u.id FROM users u JOIN roles r ON u.role_id = r.id WHERE r.name = 'admin' ORDER BY u.id LIMIT 1"
    )).fetchone()
    admin_user_id = result[0] if result else None

    conn.execute(sa.text(
        "INSERT INTO organizations (name, slug, plan, active, created_at) "
        "VALUES (:name, :slug, 'pro', 1, :created_at)"
    ), {"name": "My Studio", "slug": "my-studio", "created_at": now})

    org_id_row = conn.execute(sa.text("SELECT id FROM organizations WHERE slug = 'my-studio'")).fetchone()
    org_id = org_id_row[0]

    if admin_user_id:
        conn.execute(sa.text(
            "INSERT INTO organization_members (organization_id, user_id, org_role, created_at) "
            "VALUES (:org_id, :user_id, 'owner', :created_at)"
        ), {"org_id": org_id, "user_id": admin_user_id, "created_at": now})

    conn.execute(sa.text("UPDATE social_channels SET organization_id = :org_id"), {"org_id": org_id})
    conn.execute(sa.text("UPDATE automation_workflows SET organization_id = :org_id"), {"org_id": org_id})
    conn.execute(sa.text("UPDATE scheduled_broadcasts SET organization_id = :org_id"), {"org_id": org_id})
    conn.execute(sa.text("UPDATE site_settings SET organization_id = :org_id"), {"org_id": org_id})


def downgrade():
    with op.batch_alter_table('site_settings') as batch_op:
        batch_op.drop_constraint('uq_setting_org_key', type_='unique')
        try:
            batch_op.drop_index('ix_site_settings_key')
        except Exception:
            pass
        batch_op.create_index('ix_site_settings_key', ['key'], unique=True)
        batch_op.drop_column('organization_id')
    with op.batch_alter_table('scheduled_broadcasts') as batch_op:
        batch_op.drop_column('organization_id')
    with op.batch_alter_table('automation_workflows') as batch_op:
        batch_op.drop_column('organization_id')
    with op.batch_alter_table('social_channels') as batch_op:
        batch_op.drop_column('organization_id')
    op.drop_table('organization_members')
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')
