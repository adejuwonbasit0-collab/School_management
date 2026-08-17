"""add email sequences (drip campaigns)

Revision ID: f2a5c9e0d834
Revises: e1f4a8c7b923
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2a5c9e0d834'
down_revision = 'e1f4a8c7b923'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_sequences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('trigger', sa.String(length=64), server_default='manual'),
        sa.Column('active', sa.Boolean(), server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        'email_sequence_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sequence_id', sa.Integer(),
                   sa.ForeignKey('email_sequences.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_order', sa.Integer(), server_default='0'),
        sa.Column('delay_days', sa.Integer(), server_default='0'),
        sa.Column('subject', sa.String(length=256), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
    )
    op.create_table(
        'email_sequence_enrollments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sequence_id', sa.Integer(),
                   sa.ForeignKey('email_sequences.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subscriber_id', sa.Integer(),
                   sa.ForeignKey('newsletter_subscribers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('current_step', sa.Integer(), server_default='0'),
        sa.Column('enrolled_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_sent_at', sa.DateTime(), nullable=True),
        sa.Column('completed', sa.Boolean(), server_default=sa.false()),
        sa.UniqueConstraint('sequence_id', 'subscriber_id', name='uq_sequence_subscriber'),
    )


def downgrade():
    op.drop_table('email_sequence_enrollments')
    op.drop_table('email_sequence_steps')
    op.drop_table('email_sequences')
