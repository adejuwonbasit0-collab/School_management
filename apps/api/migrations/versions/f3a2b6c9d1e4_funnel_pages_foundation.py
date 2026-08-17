"""funnel builder foundation — real FunnelPage table + data migration

Replaces the old UserFunnel.steps JSON blob with a proper funnel_pages
table (one row per page) so the Flow Builder can connect, reorder, and
branch pages individually. Existing funnels' `steps` JSON is migrated
into real FunnelPage rows automatically; `steps` itself is left in
place (unused going forward) so nothing is destroyed if this needs to
be inspected later.

Revision ID: f3a2b6c9d1e4
Revises: a1c7e9f04d3b
Create Date: 2026-08-07 00:00:00.000000
"""
import json
import re
from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3a2b6c9d1e4'
down_revision = 'a1c7e9f04d3b'
branch_labels = None
depends_on = None


# Old free-text step "type" values -> canonical FUNNEL_PAGE_TYPES slugs.
LEGACY_TYPE_MAP = {
    "landing": "landing", "sales": "sales", "checkout": "checkout",
    "thankyou": "thank_you", "thank_you": "thank_you",
    "upsell": "upsell", "downsell": "downsell",
    "webinar": "webinar_registration", "webinar_registration": "webinar_registration",
    "webinar_replay": "webinar_replay", "booking": "booking",
    "lead_capture": "lead_capture", "survey": "survey", "quiz": "quiz",
    "application": "application", "membership_login": "membership_login",
    "membership_registration": "membership_registration",
    "order_confirmation": "order_confirmation",
}


def _slugify(value, fallback):
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug or fallback


def upgrade():
    op.create_table(
        'funnel_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('funnel_id', sa.Integer(), nullable=False),
        sa.Column('page_type', sa.String(length=32), nullable=False, server_default='custom'),
        sa.Column('title', sa.String(length=256), nullable=False, server_default='Untitled Page'),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('next_page_id', sa.Integer(), nullable=True),
        sa.Column('branch_yes_id', sa.Integer(), nullable=True),
        sa.Column('branch_no_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['funnel_id'], ['user_funnels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['next_page_id'], ['funnel_pages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['branch_yes_id'], ['funnel_pages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['branch_no_id'], ['funnel_pages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('funnel_id', 'slug', name='uq_funnel_page_slug'),
    )
    op.create_index('ix_funnel_pages_funnel_id', 'funnel_pages', ['funnel_id'])

    with op.batch_alter_table('user_funnels') as batch_op:
        batch_op.add_column(sa.Column('entry_page_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_user_funnels_entry_page_id', 'funnel_pages', ['entry_page_id'], ['id'], ondelete='SET NULL'
        )

    # ── Data migration: legacy `steps` JSON -> real funnel_pages rows ──
    bind = op.get_bind()
    metadata = sa.MetaData()
    funnel_pages_t = sa.Table('funnel_pages', metadata, autoload_with=bind)
    user_funnels_t = sa.Table('user_funnels', metadata, autoload_with=bind)

    rows = bind.execute(sa.select(user_funnels_t.c.id, user_funnels_t.c.steps)).fetchall()
    now = datetime.utcnow()

    for funnel_id, steps_raw in rows:
        if not steps_raw:
            continue
        try:
            steps = json.loads(steps_raw) if isinstance(steps_raw, str) else (steps_raw or [])
        except (TypeError, ValueError):
            continue
        if not steps:
            continue

        prev_page_id = None
        first_page_id = None
        used_slugs = set()

        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            raw_type = (step.get("type") or "custom").strip().lower()
            page_type = LEGACY_TYPE_MAP.get(raw_type, "custom")
            title = step.get("title") or raw_type.replace("_", " ").title() or f"Page {idx + 1}"
            base_slug = _slugify(f"{raw_type}-{idx + 1}", f"page-{idx + 1}")
            slug = base_slug
            n = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{n}"
                n += 1
            used_slugs.add(slug)

            result = bind.execute(
                funnel_pages_t.insert().values(
                    funnel_id=funnel_id,
                    page_type=page_type,
                    title=title,
                    slug=slug,
                    order_index=idx,
                    html_content=step.get("html") or "",
                    settings={},
                    created_at=now,
                    updated_at=now,
                )
            )
            new_id = result.inserted_primary_key[0]

            if prev_page_id is not None:
                bind.execute(
                    funnel_pages_t.update()
                    .where(funnel_pages_t.c.id == prev_page_id)
                    .values(next_page_id=new_id)
                )
            else:
                first_page_id = new_id
            prev_page_id = new_id

        if first_page_id is not None:
            bind.execute(
                user_funnels_t.update()
                .where(user_funnels_t.c.id == funnel_id)
                .values(entry_page_id=first_page_id)
            )


def downgrade():
    with op.batch_alter_table('user_funnels') as batch_op:
        batch_op.drop_constraint('fk_user_funnels_entry_page_id', type_='foreignkey')
        batch_op.drop_column('entry_page_id')
    op.drop_index('ix_funnel_pages_funnel_id', table_name='funnel_pages')
    op.drop_table('funnel_pages')
