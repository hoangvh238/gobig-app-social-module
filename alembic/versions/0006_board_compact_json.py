"""board_compact_json

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-21

Replace board_items rows with compact_json column on group_boards.
Single UPDATE per board slot change — satisfies the spec's "single backend write" requirement.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'group_boards',
        sa.Column('compact_json', JSONB, server_default='{}', nullable=False)
    )
    op.drop_index('idx_board_items_board_slot', table_name='board_items')
    op.drop_table('board_items')


def downgrade():
    op.create_table(
        'board_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('board_id', sa.Integer(), sa.ForeignKey('group_boards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipe_id', sa.Integer(), sa.ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slot', sa.VARCHAR(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_board_items_board_slot', 'board_items', ['board_id', 'slot'])
    op.drop_column('group_boards', 'compact_json')
