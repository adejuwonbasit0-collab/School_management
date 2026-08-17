"""add prompt templates library

Revision ID: a1c7e5b2f904
Revises: d4e6a9c1f038
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
import datetime

revision = 'a1c7e5b2f904'
down_revision = 'd4e6a9c1f038'
branch_labels = None
depends_on = None


STARTER_TEMPLATES = [
    ("UI Design", "Redesign a component", "Redesign the {component_name} component to feel more premium and modern. Keep its existing props/behavior. Improve spacing, typography, hover states, and responsiveness. Show before/after."),
    ("UI Design", "New landing section", "Design a new {section_name} section for the homepage. Match the existing design system (fonts, colors, spacing). Include mobile layout."),
    ("Backend", "New API endpoint", "Add a REST endpoint for {resource_name}: list, create, update, delete. Include validation, auth checks, and consistent JSON error responses matching the rest of the API."),
    ("Backend", "Background job", "Add a scheduled/background job that {job_description}. Explain how it's triggered (cron, on-demand) and what happens if it fails partway through."),
    ("Database", "New model + migration", "Add a new database model for {model_name} with fields: {fields_list}. Generate the Alembic migration, and note any relationships to existing tables."),
    ("Database", "Query optimization", "Review the query/queries used in {page_or_feature} for N+1 problems or missing indexes. Propose the fix and explain the before/after query cost."),
    ("Bug Fixes", "Root-cause a bug", "Something is broken: {bug_description}. Find the actual root cause (not just where the symptom shows) before proposing a fix. Explain what you found."),
    ("Bug Fixes", "Fix responsive layout", "The {page_name} page breaks on {breakpoint} (describe: {what_breaks}). Find the CSS/markup cause and fix it without affecting desktop layout."),
    ("Refactoring", "Extract reusable logic", "This code is duplicated in {locations}: {code_or_description}. Extract it into one reusable place and update all call sites."),
    ("Testing", "Write tests for a feature", "Write tests covering {feature_name}: happy path, at least one edge case, and one failure case."),
    ("Content", "Blog post", "Write a blog post about {topic} for a {audience} audience. Include an SEO title, meta description, and 3-5 relevant tags."),
    ("Marketing", "Feature announcement", "Write a short announcement for a new feature: {feature_name}. What it does, who it's for, one sentence on why it matters. Tone: {tone}."),
    ("SEO", "Page SEO review", "Review {page_name} for SEO: title tag, meta description, heading structure, image alt text, internal linking. List concrete fixes."),
    ("Security", "Review an endpoint", "Review {endpoint_name} for security issues: auth/authorization gaps, input validation, injection risks, rate limiting. List what's missing."),
    ("Documentation", "Document a feature", "Write Site Guide documentation for {feature_name}: what it does, how to configure it, common issues, and one example."),
    ("Deployment", "Pre-launch checklist", "Give a pre-launch checklist for {feature_or_release}: what to verify (migrations run, env vars set, feature flags, rollback plan)."),
]


def upgrade():
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='General'),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=400)),
        sa.Column('is_builtin', sa.Boolean(), server_default=sa.false()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
        sa.Column('use_count', sa.Integer(), server_default='0'),
    )
    op.create_index('ix_prompt_templates_category', 'prompt_templates', ['category'])

    conn = op.get_bind()
    now = datetime.datetime.utcnow()
    table = sa.table(
        'prompt_templates',
        sa.column('title', sa.String), sa.column('category', sa.String),
        sa.column('body', sa.Text), sa.column('description', sa.String),
        sa.column('is_builtin', sa.Boolean), sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime), sa.column('use_count', sa.Integer),
    )
    conn.execute(table.insert(), [
        {"title": title, "category": category, "body": body, "description": None,
         "is_builtin": True, "created_at": now, "updated_at": now, "use_count": 0}
        for category, title, body in STARTER_TEMPLATES
    ])


def downgrade():
    op.drop_index('ix_prompt_templates_category', table_name='prompt_templates')
    op.drop_table('prompt_templates')
