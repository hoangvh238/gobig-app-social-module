"""soc_d_indexes

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-26

"""
from alembic import op


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    # blocks: fast bidirectional lookup
    op.execute("CREATE INDEX IF NOT EXISTS idx_blocks_blocked_id ON blocks(blocked_id);")

    # mutes: already has idx_mutes_muter_id; add muted_id for reverse lookup
    op.execute("CREATE INDEX IF NOT EXISTS idx_mutes_muted_id ON mutes(muted_id);")

    # reports: triage queue — pending ordered by created_at
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_reports_pending_created "
        "ON reports(created_at ASC) WHERE status = 'pending';"
    )

    # trusted_reviewers: active reviewers (not revoked)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_trusted_reviewers_active "
        "ON trusted_reviewers(user_id) WHERE revoked_at IS NULL;"
    )

    # conversations: GIN on participant_ids already exists from migration 0001
    # messages: already indexed on conversation_id+created_at
    # activities: actor_id filter for blocked user exclusion
    op.execute("CREATE INDEX IF NOT EXISTS idx_activities_actor_id ON activities(actor_id);")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_activities_actor_id;")
    op.execute("DROP INDEX IF EXISTS idx_trusted_reviewers_active;")
    op.execute("DROP INDEX IF EXISTS idx_reports_pending_created;")
    op.execute("DROP INDEX IF EXISTS idx_mutes_muted_id;")
    op.execute("DROP INDEX IF EXISTS idx_blocks_blocked_id;")
