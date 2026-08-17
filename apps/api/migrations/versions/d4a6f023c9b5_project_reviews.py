"""add project reviews and completed_at

Revision ID: d4a6f023c9b5
Revises: c3f5e912b8a4
Create Date: 2026-07-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4a6f023c9b5'
down_revision = 'c3f5e912b8a4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('project_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['client_projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id')
    )
    with op.batch_alter_table('client_projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('client_projects', schema=None) as batch_op:
        batch_op.drop_column('completed_at')
    op.drop_table('project_reviews')
