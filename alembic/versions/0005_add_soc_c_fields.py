"""add_soc_c_fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-04

"""
from alembic import op
import sqlalchemy as sa


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipes', sa.Column('like_count', sa.Integer(), server_default='0', nullable=False))

    op.add_column('users', sa.Column('follower_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('following_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('recipe_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('streak_hash', sa.String(), nullable=True))

    op.add_column('collections', sa.Column('offline_sync', sa.Boolean(), server_default='false', nullable=False))

    op.create_index('idx_comments_recipe_parent', 'comments', ['recipe_id', 'parent_id'])
    op.create_index('idx_comments_user', 'comments', ['user_id'])
    op.create_index('idx_activities_user_created', 'activities', ['user_id', 'created_at'])
    op.create_index('idx_hashtags_name', 'hashtags', ['name'])
    op.create_index('idx_recipe_hashtags_hashtag', 'recipe_hashtags', ['hashtag_id'])
    op.create_index('idx_board_items_board_slot', 'board_items', ['board_id', 'slot'])


def downgrade():
    op.drop_index('idx_board_items_board_slot', 'board_items')
    op.drop_index('idx_recipe_hashtags_hashtag', 'recipe_hashtags')
    op.drop_index('idx_hashtags_name', 'hashtags')
    op.drop_index('idx_activities_user_created', 'activities')
    op.drop_index('idx_comments_user', 'comments')
    op.drop_index('idx_comments_recipe_parent', 'comments')

    op.drop_column('collections', 'offline_sync')

    op.drop_column('users', 'streak_hash')
    op.drop_column('users', 'recipe_count')
    op.drop_column('users', 'following_count')
    op.drop_column('users', 'follower_count')

    op.drop_column('recipes', 'like_count')
