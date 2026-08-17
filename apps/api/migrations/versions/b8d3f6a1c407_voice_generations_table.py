"""voice_generations table — persistent Voice Studio audio history

Additive only.

Revision ID: b8d3f6a1c407
Revises: f7a2c8e5d1b4
Create Date: 2026-08-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8d3f6a1c407'
down_revision = 'f7a2c8e5d1b4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'voice_generations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('voice_id', sa.String(length=64), nullable=False),
        sa.Column('voice_name', sa.String(length=128), nullable=True),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_format', sa.String(length=8), nullable=True),
        sa.Column('duration_sec', sa.Float(), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=True),
        sa.Column('credits_used', sa.Integer(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=True),
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_voice_generations_user_id', 'voice_generations', ['user_id'])
    op.create_index('ix_voice_generations_created_at', 'voice_generations', ['created_at'])


def downgrade():
    op.drop_index('ix_voice_generations_created_at', table_name='voice_generations')
    op.drop_index('ix_voice_generations_user_id', table_name='voice_generations')
    op.drop_table('voice_generations')
