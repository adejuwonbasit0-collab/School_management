"""allow project_meetings to originate from a proposal request

Revision ID: d68f2a7c5e91
Revises: c47e9b3d1a58
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'd68f2a7c5e91'
down_revision = 'c47e9b3d1a58'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('project_meetings') as batch_op:
        batch_op.alter_column('project_id', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('request_id', sa.Integer(), sa.ForeignKey('project_requests.id', name='fk_project_meetings_request_id'), nullable=True))


def downgrade():
    with op.batch_alter_table('project_meetings') as batch_op:
        batch_op.drop_column('request_id')
        batch_op.alter_column('project_id', existing_type=sa.Integer(), nullable=False)
