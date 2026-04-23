"""Update stories table for direct URL storage

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-21 13:38:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.execute("""
        ALTER TABLE stories
        ADD COLUMN url VARCHAR,
        ADD COLUMN key VARCHAR,
        ADD COLUMN size BIGINT,
        ADD COLUMN mimetype VARCHAR
    """)

    # Migrate existing data: b2_object_key -> key
    op.execute("""
        UPDATE stories
        SET key = b2_object_key
        WHERE b2_object_key IS NOT NULL
    """)

    # Make new columns NOT NULL after migration
    op.execute("""
        ALTER TABLE stories
        ALTER COLUMN url SET NOT NULL,
        ALTER COLUMN key SET NOT NULL,
        ALTER COLUMN size SET NOT NULL,
        ALTER COLUMN mimetype SET NOT NULL
    """)

    # Drop old column
    op.execute("ALTER TABLE stories DROP COLUMN b2_object_key")

    # Drop file_size_bytes (replaced by size)
    op.execute("ALTER TABLE stories DROP COLUMN file_size_bytes")

    # Update size constraint
    op.execute("""
        ALTER TABLE stories DROP CONSTRAINT IF EXISTS chk_stories_size
    """)
    op.execute("""
        ALTER TABLE stories
        ADD CONSTRAINT chk_stories_size CHECK (size > 0 AND size <= 52428800)
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE stories
        ADD COLUMN b2_object_key VARCHAR,
        ADD COLUMN file_size_bytes BIGINT
    """)

    op.execute("""
        UPDATE stories
        SET b2_object_key = key,
            file_size_bytes = size
    """)

    op.execute("""
        ALTER TABLE stories
        ALTER COLUMN b2_object_key SET NOT NULL
    """)

    op.execute("""
        ALTER TABLE stories
        DROP COLUMN url,
        DROP COLUMN key,
        DROP COLUMN size,
        DROP COLUMN mimetype
    """)
