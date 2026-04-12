"""Create social tables

Revision ID: 0001
Revises:
Create Date: 2026-04-09 13:13:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")

    # Create follows table
    op.execute("""
        CREATE TABLE follows (
            follower_id  INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_follows            PRIMARY KEY (follower_id, following_id),
            CONSTRAINT fk_follows_follower   FOREIGN KEY (follower_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT fk_follows_following  FOREIGN KEY (following_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_follows_no_self   CHECK (follower_id != following_id)
        );
    """)
    op.execute("CREATE INDEX idx_follows_follower_id ON follows(follower_id);")
    op.execute("CREATE INDEX idx_follows_following_id ON follows(following_id);")
    op.execute("CREATE INDEX idx_follows_created_at ON follows(created_at DESC);")
    op.execute("COMMENT ON TABLE follows IS 'User following relationships';")

    # Create likes table
    op.execute("""
        CREATE TABLE likes (
            user_id    INTEGER NOT NULL,
            recipe_id  INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_likes           PRIMARY KEY (user_id, recipe_id),
            CONSTRAINT fk_likes_user      FOREIGN KEY (user_id)
                REFERENCES public.users   (id) ON DELETE CASCADE,
            CONSTRAINT fk_likes_recipe    FOREIGN KEY (recipe_id)
                REFERENCES public.recipes (id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX idx_likes_recipe_id ON likes(recipe_id);")
    op.execute("CREATE INDEX idx_likes_user_id ON likes(user_id);")
    op.execute("CREATE INDEX idx_likes_created_at ON likes(created_at DESC);")
    op.execute("COMMENT ON TABLE likes IS 'Recipe likes';")

    # Create comments table
    op.execute("""
        CREATE TABLE comments (
            id         SERIAL      NOT NULL,
            user_id    INTEGER     NOT NULL,
            recipe_id  INTEGER     NOT NULL,
            parent_id  INTEGER,
            content    TEXT        NOT NULL,
            is_deleted BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_comments          PRIMARY KEY (id),
            CONSTRAINT fk_comments_user     FOREIGN KEY (user_id)
                REFERENCES public.users   (id) ON DELETE CASCADE,
            CONSTRAINT fk_comments_recipe   FOREIGN KEY (recipe_id)
                REFERENCES public.recipes (id) ON DELETE CASCADE,
            CONSTRAINT fk_comments_parent   FOREIGN KEY (parent_id)
                REFERENCES comments       (id) ON DELETE CASCADE,
            CONSTRAINT chk_comments_content CHECK (char_length(content) BETWEEN 1 AND 2000)
        );
    """)
    op.execute("CREATE INDEX idx_comments_recipe_id ON comments(recipe_id) WHERE is_deleted = FALSE;")
    op.execute("CREATE INDEX idx_comments_user_id ON comments(user_id);")
    op.execute("CREATE INDEX idx_comments_parent_id ON comments(parent_id) WHERE parent_id IS NOT NULL;")
    op.execute("CREATE INDEX idx_comments_recipe_created ON comments(recipe_id, created_at DESC) WHERE is_deleted = FALSE;")
    op.execute("CREATE INDEX idx_comments_created_at ON comments(created_at DESC);")
    op.execute("CREATE INDEX idx_comments_updated_at ON comments(updated_at DESC);")
    op.execute("COMMENT ON TABLE comments IS 'Recipe comments with soft delete';")

    # Create collections table
    op.execute("""
        CREATE TABLE collections (
            id          SERIAL      NOT NULL,
            user_id     INTEGER     NOT NULL,
            title       VARCHAR     NOT NULL,
            description VARCHAR,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_collections       PRIMARY KEY (id),
            CONSTRAINT fk_collections_user  FOREIGN KEY (user_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_collections_title CHECK (char_length(title) BETWEEN 1 AND 200)
        );
    """)
    op.execute("CREATE INDEX idx_collections_user_id ON collections(user_id);")
    op.execute("CREATE INDEX idx_collections_created_at ON collections(created_at DESC);")
    op.execute("CREATE INDEX idx_collections_updated_at ON collections(updated_at DESC);")
    op.execute("COMMENT ON TABLE collections IS 'User-created recipe collections';")

    # Create collection_items table
    op.execute("""
        CREATE TABLE collection_items (
            id         VARCHAR     NOT NULL,
            _order     INTEGER     NOT NULL,
            _parent_id INTEGER     NOT NULL,
            recipe_id  INTEGER     NOT NULL,
            notes      VARCHAR,
            added_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_collection_items            PRIMARY KEY (id),
            CONSTRAINT fk_collection_items_parent     FOREIGN KEY (_parent_id)
                REFERENCES collections    (id) ON DELETE CASCADE,
            CONSTRAINT fk_collection_items_recipe     FOREIGN KEY (recipe_id)
                REFERENCES public.recipes (id) ON DELETE CASCADE,
            CONSTRAINT uq_collection_items_col_recipe UNIQUE (_parent_id, recipe_id)
        );
    """)
    op.execute("CREATE INDEX idx_collection_items_parent_order ON collection_items(_parent_id, _order);")
    op.execute("CREATE INDEX idx_collection_items_recipe_id ON collection_items(recipe_id);")
    op.execute("COMMENT ON TABLE collection_items IS 'Items in a collection';")

    # Create hashtags table
    op.execute("""
        CREATE TABLE hashtags (
            id          SERIAL  NOT NULL,
            name        VARCHAR NOT NULL,
            usage_count INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_hashtags             PRIMARY KEY (id),
            CONSTRAINT uq_hashtags_name        UNIQUE (name),
            CONSTRAINT chk_hashtags_name_fmt   CHECK (
                name = LOWER(name)
                AND name !~ '^#'
                AND char_length(name) BETWEEN 2 AND 100
            ),
            CONSTRAINT chk_hashtags_usage_count CHECK (usage_count >= 0)
        );
    """)
    op.execute("CREATE INDEX idx_hashtags_usage_count ON hashtags(usage_count DESC);")
    op.execute("CREATE INDEX idx_hashtags_name_trgm ON hashtags USING gin(name gin_trgm_ops);")
    op.execute("COMMENT ON TABLE hashtags IS 'Normalized hashtags';")

    # Create recipe_hashtags table
    op.execute("""
        CREATE TABLE recipe_hashtags (
            recipe_id  INTEGER NOT NULL,
            hashtag_id INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_recipe_hashtags         PRIMARY KEY (recipe_id, hashtag_id),
            CONSTRAINT fk_recipe_hashtags_recipe  FOREIGN KEY (recipe_id)
                REFERENCES public.recipes  (id) ON DELETE CASCADE,
            CONSTRAINT fk_recipe_hashtags_hashtag FOREIGN KEY (hashtag_id)
                REFERENCES hashtags        (id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX idx_recipe_hashtags_hashtag_id ON recipe_hashtags(hashtag_id);")
    op.execute("CREATE INDEX idx_recipe_hashtags_recipe_id ON recipe_hashtags(recipe_id);")
    op.execute("COMMENT ON TABLE recipe_hashtags IS 'M2M junction: recipes and hashtags';")

    # Create blocks table
    op.execute("""
        CREATE TABLE blocks (
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_blocks           PRIMARY KEY (blocker_id, blocked_id),
            CONSTRAINT fk_blocks_blocker   FOREIGN KEY (blocker_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT fk_blocks_blocked   FOREIGN KEY (blocked_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_blocks_no_self  CHECK (blocker_id != blocked_id)
        );
    """)
    op.execute("CREATE INDEX idx_blocks_blocker_id ON blocks(blocker_id);")
    op.execute("CREATE INDEX idx_blocks_blocked_id ON blocks(blocked_id);")
    op.execute("COMMENT ON TABLE blocks IS 'User blocking';")

    # Create mutes table
    op.execute("""
        CREATE TABLE mutes (
            muter_id   INTEGER NOT NULL,
            muted_id   INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_mutes          PRIMARY KEY (muter_id, muted_id),
            CONSTRAINT fk_mutes_muter    FOREIGN KEY (muter_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT fk_mutes_muted    FOREIGN KEY (muted_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_mutes_no_self CHECK (muter_id != muted_id)
        );
    """)
    op.execute("CREATE INDEX idx_mutes_muter_id ON mutes(muter_id);")
    op.execute("COMMENT ON TABLE mutes IS 'User muting';")

    # Create reports table
    op.execute("""
        CREATE TABLE reports (
            id                  SERIAL  NOT NULL,
            reporter_id         INTEGER NOT NULL,
            reported_user_id    INTEGER,
            reported_recipe_id  INTEGER,
            reported_comment_id INTEGER,
            report_type         VARCHAR NOT NULL,
            severity            VARCHAR NOT NULL DEFAULT 'medium',
            description         VARCHAR,
            status              VARCHAR NOT NULL DEFAULT 'pending',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_reports               PRIMARY KEY (id),
            CONSTRAINT fk_reports_reporter      FOREIGN KEY (reporter_id)
                REFERENCES public.users   (id) ON DELETE CASCADE,
            CONSTRAINT fk_reports_user          FOREIGN KEY (reported_user_id)
                REFERENCES public.users   (id) ON DELETE SET NULL,
            CONSTRAINT fk_reports_recipe        FOREIGN KEY (reported_recipe_id)
                REFERENCES public.recipes (id) ON DELETE SET NULL,
            CONSTRAINT fk_reports_comment       FOREIGN KEY (reported_comment_id)
                REFERENCES comments       (id) ON DELETE SET NULL,
            CONSTRAINT chk_reports_has_target   CHECK (
                reported_user_id    IS NOT NULL OR
                reported_recipe_id  IS NOT NULL OR
                reported_comment_id IS NOT NULL
            ),
            CONSTRAINT chk_reports_severity     CHECK (severity IN ('low', 'medium', 'high')),
            CONSTRAINT chk_reports_status       CHECK (status   IN ('pending', 'reviewed', 'resolved', 'dismissed'))
        );
    """)
    op.execute("CREATE INDEX idx_reports_status ON reports(status) WHERE status = 'pending';")
    op.execute("CREATE INDEX idx_reports_reporter_id ON reports(reporter_id);")
    op.execute("CREATE INDEX idx_reports_created_at ON reports(created_at DESC);")
    op.execute("COMMENT ON TABLE reports IS 'Content reporting';")

    # Create activities table
    op.execute("""
        CREATE TABLE activities (
            id          SERIAL  NOT NULL,
            user_id     INTEGER NOT NULL,
            actor_id    INTEGER NOT NULL,
            action_type VARCHAR NOT NULL,
            payload_json JSONB  NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_activities            PRIMARY KEY (id),
            CONSTRAINT fk_activities_user       FOREIGN KEY (user_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT fk_activities_actor      FOREIGN KEY (actor_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_activities_action    CHECK (
                action_type IN ('like', 'comment', 'follow', 'share', 'mention')
            )
        );
    """)
    op.execute("CREATE INDEX idx_activities_user_created ON activities(user_id, created_at DESC);")
    op.execute("CREATE INDEX idx_activities_actor_id ON activities(actor_id);")
    op.execute("CREATE INDEX idx_activities_action_type ON activities(action_type);")
    op.execute("COMMENT ON TABLE activities IS 'Activity feed';")

    # Create conversations table
    op.execute("""
        CREATE TABLE conversations (
            id               SERIAL    NOT NULL,
            participant_ids  INTEGER[] NOT NULL,
            last_message_at  TIMESTAMPTZ,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_conversations              PRIMARY KEY (id),
            CONSTRAINT chk_conversations_min_parts   CHECK (array_length(participant_ids, 1) >= 2)
        );
    """)
    op.execute("CREATE INDEX idx_conversations_participants ON conversations USING GIN(participant_ids);")
    op.execute("CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);")
    op.execute("COMMENT ON TABLE conversations IS 'DM conversations';")

    # Create messages table
    op.execute("""
        CREATE TABLE messages (
            id              SERIAL  NOT NULL,
            conversation_id INTEGER NOT NULL,
            sender_id       INTEGER NOT NULL,
            content         TEXT    NOT NULL,
            read_at         TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_messages               PRIMARY KEY (id),
            CONSTRAINT fk_messages_conversation  FOREIGN KEY (conversation_id)
                REFERENCES conversations  (id) ON DELETE CASCADE,
            CONSTRAINT fk_messages_sender        FOREIGN KEY (sender_id)
                REFERENCES public.users   (id) ON DELETE CASCADE,
            CONSTRAINT chk_messages_content      CHECK (char_length(content) BETWEEN 1 AND 2000)
        );
    """)
    op.execute("CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at DESC);")
    op.execute("CREATE INDEX idx_messages_sender_id ON messages(sender_id);")
    op.execute("CREATE INDEX idx_messages_unread ON messages(conversation_id, read_at) WHERE read_at IS NULL;")
    op.execute("COMMENT ON TABLE messages IS 'DM messages';")

    # Create trusted_reviewers table
    op.execute("""
        CREATE TABLE trusted_reviewers (
            user_id      INTEGER NOT NULL,
            assigned_by  INTEGER NOT NULL,
            permissions  JSONB   NOT NULL DEFAULT '{"can_review": true}'::jsonb,
            revoked_at   TIMESTAMPTZ,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_trusted_reviewers          PRIMARY KEY (user_id),
            CONSTRAINT fk_trusted_reviewers_user     FOREIGN KEY (user_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT fk_trusted_reviewers_assigner FOREIGN KEY (assigned_by)
                REFERENCES public.users (id) ON DELETE RESTRICT
        );
    """)
    op.execute("COMMENT ON TABLE trusted_reviewers IS 'Users with moderation privileges';")

    # Create social_challenges table
    op.execute("""
        CREATE TABLE social_challenges (
            id             SERIAL  NOT NULL,
            title          VARCHAR NOT NULL,
            description    VARCHAR,
            challenge_type VARCHAR NOT NULL,
            start_date     DATE    NOT NULL,
            end_date       DATE    NOT NULL,
            created_by     INTEGER,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_social_challenges       PRIMARY KEY (id),
            CONSTRAINT fk_social_challenges_user  FOREIGN KEY (created_by)
                REFERENCES public.users (id) ON DELETE SET NULL,
            CONSTRAINT chk_social_challenges_dates CHECK (end_date >= start_date)
        );
    """)
    op.execute("CREATE INDEX idx_social_challenges_dates ON social_challenges(start_date, end_date);")
    op.execute("COMMENT ON TABLE social_challenges IS 'Cooking challenges';")

    # Create live_rooms table
    op.execute("""
        CREATE TABLE live_rooms (
            id         SERIAL  NOT NULL,
            creator_id INTEGER NOT NULL,
            recipe_id  INTEGER,
            room_type  VARCHAR NOT NULL DEFAULT 'personal',
            status     VARCHAR NOT NULL DEFAULT 'scheduled',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_live_rooms          PRIMARY KEY (id),
            CONSTRAINT fk_live_rooms_creator  FOREIGN KEY (creator_id)
                REFERENCES public.users   (id) ON DELETE CASCADE,
            CONSTRAINT fk_live_rooms_recipe   FOREIGN KEY (recipe_id)
                REFERENCES public.recipes (id) ON DELETE SET NULL,
            CONSTRAINT chk_live_rooms_type    CHECK (room_type IN ('personal', 'group')),
            CONSTRAINT chk_live_rooms_status  CHECK (status    IN ('scheduled', 'live', 'ended'))
        );
    """)
    op.execute("CREATE INDEX idx_live_rooms_creator_id ON live_rooms(creator_id);")
    op.execute("CREATE INDEX idx_live_rooms_status ON live_rooms(status) WHERE status = 'live';")
    op.execute("CREATE INDEX idx_live_rooms_created_at ON live_rooms(created_at DESC);")
    op.execute("COMMENT ON TABLE live_rooms IS 'Live cooking rooms';")

    # Create live_participants table
    op.execute("""
        CREATE TABLE live_participants (
            id        SERIAL  NOT NULL,
            room_id   INTEGER NOT NULL,
            user_id   INTEGER NOT NULL,
            role      VARCHAR NOT NULL DEFAULT 'viewer',
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            left_at   TIMESTAMPTZ,
            CONSTRAINT pk_live_participants        PRIMARY KEY (id),
            CONSTRAINT fk_live_participants_room   FOREIGN KEY (room_id)
                REFERENCES live_rooms   (id) ON DELETE CASCADE,
            CONSTRAINT fk_live_participants_user   FOREIGN KEY (user_id)
                REFERENCES public.users (id) ON DELETE CASCADE,
            CONSTRAINT chk_live_participants_role  CHECK (role IN ('host', 'co_host', 'viewer'))
        );
    """)
    op.execute("CREATE INDEX idx_live_participants_room_id ON live_participants(room_id);")
    op.execute("CREATE INDEX idx_live_participants_user_id ON live_participants(user_id);")
    op.execute("CREATE UNIQUE INDEX idx_live_participants_active ON live_participants(room_id, user_id) WHERE left_at IS NULL;")
    op.execute("COMMENT ON TABLE live_participants IS 'Live room participants';")

    # Create live_room_templates table
    op.execute("""
        CREATE TABLE live_room_templates (
            id               SERIAL  NOT NULL,
            name             VARCHAR NOT NULL,
            default_hashtags JSONB   DEFAULT '[]'::jsonb,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_live_room_templates    PRIMARY KEY (id),
            CONSTRAINT uq_live_room_templates_nm UNIQUE (name)
        );
    """)
    op.execute("COMMENT ON TABLE live_room_templates IS 'Reusable live room templates';")

    # Create group_boards table
    op.execute("""
        CREATE TABLE group_boards (
            id         SERIAL  NOT NULL,
            user_id    INTEGER NOT NULL,
            board_name VARCHAR NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_group_boards       PRIMARY KEY (id),
            CONSTRAINT fk_group_boards_user  FOREIGN KEY (user_id)
                REFERENCES public.users (id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX idx_group_boards_user_id ON group_boards(user_id);")
    op.execute("COMMENT ON TABLE group_boards IS 'Group meal planning boards';")

    # Create board_items table
    op.execute("""
        CREATE TABLE board_items (
            id            SERIAL  NOT NULL,
            board_id      INTEGER NOT NULL,
            recipe_id     INTEGER NOT NULL,
            slot          VARCHAR NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_board_items         PRIMARY KEY (id),
            CONSTRAINT fk_board_items_board   FOREIGN KEY (board_id)
                REFERENCES group_boards   (id) ON DELETE CASCADE,
            CONSTRAINT fk_board_items_recipe  FOREIGN KEY (recipe_id)
                REFERENCES public.recipes (id) ON DELETE CASCADE,
            CONSTRAINT chk_board_items_slot   CHECK (slot IN ('tonight', 'this_week', 'later'))
        );
    """)
    op.execute("CREATE INDEX idx_board_items_board_id ON board_items(board_id);")
    op.execute("CREATE INDEX idx_board_items_recipe_id ON board_items(recipe_id);")
    op.execute("COMMENT ON TABLE board_items IS 'Items in meal planning boards';")

    # Create triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_comments_updated_at
            BEFORE UPDATE ON comments
            FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
    """)

    op.execute("""
        CREATE TRIGGER trg_collections_updated_at
            BEFORE UPDATE ON collections
            FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();
    """)

    # Create utility function
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_increment_counter(
            p_table_name  TEXT,
            p_id          INTEGER,
            p_counter_name TEXT,
            p_delta       INTEGER DEFAULT 1
        )
        RETURNS VOID AS $$
        DECLARE
            v_lock_id BIGINT;
        BEGIN
            v_lock_id := ('x' || MD5(p_table_name || p_id::TEXT))::bit(64)::BIGINT;
            PERFORM pg_advisory_xact_lock(v_lock_id);
            EXECUTE format(
                'UPDATE %I SET %I = %I + $1 WHERE id = $2',
                p_table_name, p_counter_name, p_counter_name
            ) USING p_delta, p_id;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("COMMENT ON FUNCTION fn_increment_counter IS 'Atomically increment denormalized counters';")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS board_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS group_boards CASCADE;")
    op.execute("DROP TABLE IF EXISTS live_room_templates CASCADE;")
    op.execute("DROP TABLE IF EXISTS live_participants CASCADE;")
    op.execute("DROP TABLE IF EXISTS live_rooms CASCADE;")
    op.execute("DROP TABLE IF EXISTS social_challenges CASCADE;")
    op.execute("DROP TABLE IF EXISTS trusted_reviewers CASCADE;")
    op.execute("DROP TABLE IF EXISTS messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE;")
    op.execute("DROP TABLE IF EXISTS activities CASCADE;")
    op.execute("DROP TABLE IF EXISTS reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS mutes CASCADE;")
    op.execute("DROP TABLE IF EXISTS blocks CASCADE;")
    op.execute("DROP TABLE IF EXISTS recipe_hashtags CASCADE;")
    op.execute("DROP TABLE IF EXISTS hashtags CASCADE;")
    op.execute("DROP TABLE IF EXISTS collection_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS collections CASCADE;")
    op.execute("DROP TABLE IF EXISTS comments CASCADE;")
    op.execute("DROP TABLE IF EXISTS likes CASCADE;")
    op.execute("DROP TABLE IF EXISTS follows CASCADE;")

    op.execute("DROP FUNCTION IF EXISTS fn_increment_counter CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS fn_update_updated_at CASCADE;")
