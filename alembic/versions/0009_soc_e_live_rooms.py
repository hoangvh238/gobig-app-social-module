"""soc_e_live_rooms — extend live room tables, add clip markers and reaction events

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-09

"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── live_rooms: add missing SOC-E columns ─────────────────────────
    op.execute("""
        ALTER TABLE live_rooms
            ADD COLUMN IF NOT EXISTS potluck_id     VARCHAR,
            ADD COLUMN IF NOT EXISTS template_id    INTEGER REFERENCES live_room_templates(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS emotion_preset VARCHAR,
            ADD COLUMN IF NOT EXISTS low_res_first  BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS audio_only     BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    op.execute("COMMENT ON COLUMN live_rooms.low_res_first IS 'Tuan SFU reads this flag to switch video quality';")
    op.execute("COMMENT ON COLUMN live_rooms.audio_only IS 'Flutter switches to audio-only view when true';")
    op.execute("COMMENT ON COLUMN live_rooms.potluck_id IS 'Optional link to a potluck session (Tuan domain, no FK)';")

    # ── live_room_templates: add emotion_preset and default_slot_min ──
    op.execute("""
        ALTER TABLE live_room_templates
            ADD COLUMN IF NOT EXISTS emotion_preset  VARCHAR,
            ADD COLUMN IF NOT EXISTS default_slot_min INTEGER;
    """)

    # ── live_clip_markers ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS live_clip_markers (
            id           SERIAL      NOT NULL,
            room_id      INTEGER     NOT NULL,
            user_id      INTEGER     NOT NULL,
            timestamp_s  INTEGER     NOT NULL,
            label        VARCHAR     NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_live_clip_markers    PRIMARY KEY (id),
            CONSTRAINT fk_clip_markers_room    FOREIGN KEY (room_id)
                REFERENCES live_rooms(id) ON DELETE CASCADE,
            CONSTRAINT fk_clip_markers_user    FOREIGN KEY (user_id)
                REFERENCES public.users(id) ON DELETE CASCADE,
            CONSTRAINT chk_clip_marker_label   CHECK (char_length(label) BETWEEN 1 AND 200),
            CONSTRAINT chk_clip_marker_ts      CHECK (timestamp_s >= 0)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_clip_markers_room_id ON live_clip_markers(room_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_clip_markers_ts ON live_clip_markers(room_id, timestamp_s ASC);")
    op.execute("COMMENT ON TABLE live_clip_markers IS 'Clip markers consumed by L-M3-S Celery task';")

    # ── live_reaction_events ──────────────────────────────────────────
    # Batch-written from Redis buffer every 30s — never written per-reaction on hot path.
    op.execute("""
        CREATE TABLE IF NOT EXISTS live_reaction_events (
            id            SERIAL      NOT NULL,
            room_id       INTEGER     NOT NULL,
            user_id       INTEGER     NOT NULL,
            reaction_type VARCHAR     NOT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_live_reaction_events   PRIMARY KEY (id),
            CONSTRAINT fk_reaction_events_room   FOREIGN KEY (room_id)
                REFERENCES live_rooms(id) ON DELETE CASCADE,
            CONSTRAINT fk_reaction_events_user   FOREIGN KEY (user_id)
                REFERENCES public.users(id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_reaction_events_room_id ON live_reaction_events(room_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reaction_events_created_at ON live_reaction_events(room_id, created_at DESC);")
    op.execute("COMMENT ON TABLE live_reaction_events IS 'Batched reaction storage — 30s Celery flush from Redis';")

    # ── seed pre-defined templates ────────────────────────────────────
    op.execute("""
        INSERT INTO live_room_templates (name, emotion_preset, default_slot_min, default_hashtags)
        VALUES
            ('Pasta Night',       'cozy',      60,  '["pasta", "italian", "homecooking"]'::jsonb),
            ('Meal Prep Sunday',  'productive', 90,  '["mealprep", "sunday", "healthy"]'::jsonb),
            ('$20 Budget Week',   'creative',   45,  '["budget", "frugal", "cheapmeals"]'::jsonb)
        ON CONFLICT (name) DO UPDATE
            SET emotion_preset    = EXCLUDED.emotion_preset,
                default_slot_min  = EXCLUDED.default_slot_min,
                default_hashtags  = EXCLUDED.default_hashtags;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS live_reaction_events;")
    op.execute("DROP TABLE IF EXISTS live_clip_markers;")
    op.execute("""
        ALTER TABLE live_room_templates
            DROP COLUMN IF EXISTS emotion_preset,
            DROP COLUMN IF EXISTS default_slot_min;
    """)
    op.execute("""
        ALTER TABLE live_rooms
            DROP COLUMN IF EXISTS potluck_id,
            DROP COLUMN IF EXISTS template_id,
            DROP COLUMN IF EXISTS emotion_preset,
            DROP COLUMN IF EXISTS low_res_first,
            DROP COLUMN IF EXISTS audio_only;
    """)
