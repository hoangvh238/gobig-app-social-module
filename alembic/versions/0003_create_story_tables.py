"""Create story tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-13 20:00:00.000000

"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── stories ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE stories (
            id              SERIAL      NOT NULL,
            user_id         INTEGER     NOT NULL,
            b2_object_key   VARCHAR     NOT NULL,
            story_type      VARCHAR     NOT NULL,
            emotion_preset  VARCHAR,
            challenge_id    INTEGER,
            challenge_type  VARCHAR,
            time_preference VARCHAR,
            file_size_bytes BIGINT,
            status          VARCHAR     NOT NULL DEFAULT 'pending',
            expires_at      TIMESTAMPTZ NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_stories               PRIMARY KEY (id),
            CONSTRAINT fk_stories_user          FOREIGN KEY (user_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT fk_stories_challenge     FOREIGN KEY (challenge_id)
                REFERENCES social_challenges (id) ON DELETE SET NULL,
            CONSTRAINT chk_stories_type         CHECK (
                story_type IN ('cooking_moment', 'prep_pack', 'challenge_entry')
            ),
            CONSTRAINT chk_stories_status       CHECK (
                status IN ('pending', 'confirmed', 'rejected')
            ),
            CONSTRAINT chk_stories_size         CHECK (
                file_size_bytes IS NULL OR file_size_bytes <= 52428800
            ),
            CONSTRAINT chk_stories_time_pref    CHECK (
                time_preference IS NULL OR time_preference IN ('late_night')
            )
        );
    """)
    op.execute("CREATE INDEX idx_stories_user_id ON stories(user_id);")
    op.execute("CREATE INDEX idx_stories_status_confirmed ON stories(created_at DESC) WHERE status = 'confirmed';")
    op.execute("CREATE INDEX idx_stories_expires_at ON stories(expires_at) WHERE status = 'confirmed';")
    op.execute("CREATE INDEX idx_stories_challenge_id ON stories(challenge_id) WHERE challenge_id IS NOT NULL;")
    op.execute("CREATE INDEX idx_stories_emotion_preset ON stories(emotion_preset) WHERE emotion_preset IS NOT NULL;")
    op.execute("COMMENT ON TABLE stories IS 'User stories with B2 media — 60-day lifecycle';")

    # ── story_recipe_links (prep_pack → multiple recipes) ────────────
    op.execute("""
        CREATE TABLE story_recipe_links (
            story_id      INTEGER NOT NULL,
            recipe_id     INTEGER NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            CONSTRAINT pk_story_recipe_links        PRIMARY KEY (story_id, recipe_id),
            CONSTRAINT fk_story_recipe_links_story  FOREIGN KEY (story_id)
                REFERENCES stories (id) ON DELETE CASCADE,
            CONSTRAINT fk_story_recipe_links_recipe FOREIGN KEY (recipe_id)
                REFERENCES public.recipes (id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX idx_story_recipe_links_recipe_id ON story_recipe_links(recipe_id);")
    op.execute("COMMENT ON TABLE story_recipe_links IS 'M2M: prep_pack stories linked to recipes';")

    # ── potluck_social_events (audit trail) ──────────────────────────
    op.execute("""
        CREATE TABLE potluck_social_events (
            id           SERIAL      NOT NULL,
            session_id   VARCHAR     NOT NULL,
            event_type   VARCHAR     NOT NULL,
            actor_id     INTEGER     NOT NULL,
            payload_json JSONB       NOT NULL DEFAULT '{}'::jsonb,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_potluck_social_events     PRIMARY KEY (id),
            CONSTRAINT fk_pse_actor                 FOREIGN KEY (actor_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_pse_event_type           CHECK (
                event_type IN ('rsvp', 'invite_sent', 'buddy_suggested', 'ping_sent', 'state_updated')
            )
        );
    """)
    op.execute("CREATE INDEX idx_pse_session_id ON potluck_social_events(session_id);")
    op.execute("CREATE INDEX idx_pse_actor_created ON potluck_social_events(actor_id, created_at DESC);")
    op.execute("COMMENT ON TABLE potluck_social_events IS 'Audit trail for social potluck interactions';")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS potluck_social_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS story_recipe_links CASCADE;")
    op.execute("DROP TABLE IF EXISTS stories CASCADE;")
