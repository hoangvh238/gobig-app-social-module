"""user_avatar_url

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-21

Replace avatar_id (int) with avatar_url (varchar).
Upload service returns a static URL; we store it directly — no presign needed.
"""
from alembic import op
import sqlalchemy as sa


revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('avatar_url', sa.String(), nullable=True))
    op.drop_column('users', 'avatar_id')


def downgrade():
    op.add_column('users', sa.Column('avatar_id', sa.Integer(), nullable=True))
    op.drop_column('users', 'avatar_url')
