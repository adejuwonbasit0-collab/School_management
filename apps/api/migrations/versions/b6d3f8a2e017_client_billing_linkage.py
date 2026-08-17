"""add client billing linkage to social_channels and automation_workflows

Revision ID: b6d3f8a2e017
Revises: a2c9e4f18b30
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'b6d3f8a2e017'
down_revision = 'a2c9e4f18b30'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('social_channels') as batch_op:
        batch_op.add_column(sa.Column('client_project_id', sa.Integer(), sa.ForeignKey('client_projects.id', name='fk_social_channels_client_project_id'), nullable=True))
        batch_op.add_column(sa.Column('monthly_fee', sa.Float(), nullable=True))
    with op.batch_alter_table('automation_workflows') as batch_op:
        batch_op.add_column(sa.Column('client_project_id', sa.Integer(), sa.ForeignKey('client_projects.id', name='fk_automation_workflows_client_project_id'), nullable=True))
        batch_op.add_column(sa.Column('monthly_fee', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('automation_workflows') as batch_op:
        batch_op.drop_column('monthly_fee')
        batch_op.drop_column('client_project_id')
    with op.batch_alter_table('social_channels') as batch_op:
        batch_op.drop_column('monthly_fee')
        batch_op.drop_column('client_project_id')
