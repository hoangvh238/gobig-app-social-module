"""Add performance indexes for feed enrichment

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-12 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_recipes_id_author ON public.recipes(id, author_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_likes_recipe_user ON likes(recipe_id, user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_comments_recipe_user ON comments(recipe_id, user_id) WHERE is_deleted = FALSE;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_follows_following_follower ON follows(following_id, follower_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_recipe_hashtags_recipe_hashtag ON recipe_hashtags(recipe_id, hashtag_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_id ON public.users(id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_recipes_id_author;")
    op.execute("DROP INDEX IF EXISTS idx_likes_recipe_user;")
    op.execute("DROP INDEX IF EXISTS idx_comments_recipe_user;")
    op.execute("DROP INDEX IF EXISTS idx_follows_following_follower;")
    op.execute("DROP INDEX IF EXISTS idx_recipe_hashtags_recipe_hashtag;")
    op.execute("DROP INDEX IF EXISTS idx_users_id;")