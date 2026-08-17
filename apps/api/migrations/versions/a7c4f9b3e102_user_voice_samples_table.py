"""user_voice_samples table — Voice Studio 'My Voices' favorites library

Additive only.

Revision ID: a7c4f9b3e102
Revises: d7f4a1c8e320
Create Date: 2026-08-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7c4f9b3e102'
down_revision = 'd7f4a1c8e320'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_voice_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_format', sa.String(length=8), nullable=True),
        sa.Column('duration_sec', sa.Float(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_voice_samples_user_id', 'user_voice_samples', ['user_id'])
    op.create_index('ix_user_voice_samples_created_at', 'user_voice_samples', ['created_at'])


def downgrade():
    op.drop_index('ix_user_voice_samples_created_at', table_name='user_voice_samples')
    op.drop_index('ix_user_voice_samples_user_id', table_name='user_voice_samples')
    op.drop_table('user_voice_samples')
