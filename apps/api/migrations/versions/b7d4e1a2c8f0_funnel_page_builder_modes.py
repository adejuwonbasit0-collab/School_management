"""funnel pages — add builder_mode + blocks columns (three build modes)

Adds the two columns FunnelPage needs to support three distinct editing
modes per page: AI Builder (existing), a real drag-and-drop Block Builder
(new — structured `blocks` JSON, rendered server-side), and a Code
Builder (existing raw-HTML editing, now explicitly tracked as a mode).

Revision ID: b7d4e1a2c8f0
Revises: f3a2b6c9d1e4
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7d4e1a2c8f0'
down_revision = 'f3a2b6c9d1e4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('funnel_pages') as batch_op:
        batch_op.add_column(sa.Column('builder_mode', sa.String(length=16), nullable=False, server_default='code'))
        batch_op.add_column(sa.Column('blocks', sa.JSON(), nullable=True))

    # Any page that already has HTML but no blocks was built via AI or
    # raw code — leave builder_mode at the 'code' default for those (AI
    # pages get re-tagged 'ai' below since we can tell them apart: pages
    # with content are most likely AI-generated in existing data, since
    # the raw code editor was a secondary/advanced option previously).
    bind = op.get_bind()
    bind.execute(sa.text(
        "UPDATE funnel_pages SET builder_mode = 'ai' WHERE html_content IS NOT NULL AND html_content != ''"
    ))


def downgrade():
    with op.batch_alter_table('funnel_pages') as batch_op:
        batch_op.drop_column('blocks')
        batch_op.drop_column('builder_mode')
