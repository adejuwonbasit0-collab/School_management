"""website builder: chat history + github repo columns on user_websites

Adds the two columns the rebuilt Website Builder needs on UserWebsite:
  - chat_history: per-page conversation turns, so a follow-up prompt
    ("make the header sticky") edits the existing generated site instead
    of the AI starting over with no memory of what it already built.
  - github_repo: "owner/repo" once a site has been pushed, so the builder
    can show "View on GitHub" / push updates to the same repo instead of
    creating a new one every time.

pages[].css / pages[].js need no migration — they're just new keys in
the existing JSON `pages` column; old rows with html-only page dicts
keep working (css/js default to "" wherever they're read).

Revision ID: a9c3e7f2b154
Revises: e2b6d4a8f1c3
Create Date: 2026-08-12
"""
from alembic import op
import sqlalchemy as sa

revision = 'a9c3e7f2b154'
down_revision = 'e2b6d4a8f1c3'
branch_labels = None
depends_on = None


def _cols(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    existing = _cols(bind, "user_websites")
    with op.batch_alter_table("user_websites") as batch_op:
        if "chat_history" not in existing:
            batch_op.add_column(sa.Column("chat_history", sa.JSON(), nullable=True))
        if "github_repo" not in existing:
            batch_op.add_column(sa.Column("github_repo", sa.String(length=256), nullable=True))


def downgrade():
    bind = op.get_bind()
    existing = _cols(bind, "user_websites")
    with op.batch_alter_table("user_websites") as batch_op:
        if "github_repo" in existing:
            batch_op.drop_column("github_repo")
        if "chat_history" in existing:
            batch_op.drop_column("chat_history")
