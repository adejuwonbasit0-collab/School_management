"""add project deliveries

Revision ID: c3f5e912b8a4
Revises: b2e4d891a3f7
Create Date: 2026-07-11 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3f5e912b8a4'
down_revision = 'e93cfb58aeeb'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('project_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('file_url', sa.String(length=512), nullable=True),
        sa.Column('external_url', sa.String(length=512), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('delivered_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['client_projects.id'], ),
        sa.ForeignKeyConstraint(['delivered_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('project_deliveries', schema=None) as batch_op:
        batch_op.create_index('ix_project_deliveries_project_id', ['project_id'])


def downgrade():
    op.drop_table('project_deliveries')
