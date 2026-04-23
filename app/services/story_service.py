"""
Story service — direct upload flow:
  1. Client uploads to /api/upload → gets {url, key, size, mimetype}
  2. Client calls /confirm with that data → write to DB, schedule cleanup, index ES
  3. search: TasteSearch via ES with tier-based boost
"""
import time
from datetime import datetime, timezone, timedelta

from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.social import Story, StoryRecipeLink
from app.schemas.story import (
    StoryConfirmRequest, StoryConfirmResponse,
    TasteSearchParams, TasteSearchResponse, StorySearchHit,
    StoryDetail, StoryFeedResponse,
)
from app.services.es_client import ESClient
from app.metrics import story_upload_latency_seconds, story_requests_total, taste_search_latency_seconds


# TasteProfile boost multipliers — read from JWT, zero DB queries
TASTE_TIER_BOOST = {
    "basic": 1.0,
    "advanced": 1.3,
    "hyper": 1.6,
}


class StoryService:

    @staticmethod
    async def confirm(
        user_id: int,
        request: StoryConfirmRequest,
        db: AsyncSession,
    ) -> StoryConfirmResponse:
        """
        Write confirmed story record directly to DB.
        Tag stories created after 9pm with time_preference=late_night.
        Create Redis job to auto-delete after 60 days.
        """
        start = time.time()

        # Validate size
        if request.size > settings.story_max_size_bytes:
            raise ValueError(f"File size {request.size} exceeds max {settings.story_max_size_bytes}")

        # Time preference: late_night if after 9pm UTC
        now = datetime.now(timezone.utc)
        time_preference = "late_night" if now.hour >= 21 else None

        # Determine story_type from context
        story_type = "cooking_moment"
        if request.recipe_ids:
            story_type = "prep_pack"
        if request.challenge_id:
            story_type = "challenge_entry"

        expires_at = now + timedelta(days=settings.story_ttl_days)

        # Insert story record with status='confirmed'
        result = await db.execute(
            text("""
                INSERT INTO stories (user_id, url, key, size, mimetype, story_type, emotion_preset,
                    challenge_id, time_preference, status, expires_at)
                VALUES (:user_id, :url, :key, :size, :mimetype, :story_type, :emotion_preset,
                    :challenge_id, :time_pref, 'confirmed', :expires_at)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "url": request.url,
                "key": request.key,
                "size": request.size,
                "mimetype": request.mimetype,
                "story_type": story_type,
                "emotion_preset": request.emotion_preset,
                "challenge_id": request.challenge_id,
                "time_pref": time_preference,
                "expires_at": expires_at,
            },
        )
        story_id = result.scalar_one()

        # Link recipes for prep_pack
        if request.recipe_ids:
            for i, recipe_id in enumerate(request.recipe_ids):
                await db.execute(
                    text("""
                        INSERT INTO story_recipe_links (story_id, recipe_id, display_order)
                        VALUES (:sid, :rid, :ord)
                    """),
                    {"sid": story_id, "rid": recipe_id, "ord": i},
                )

        await db.commit()

        # Schedule Redis job to delete story after TTL
        try:
            from app.redis_client import redis_pool
            delete_at = int(expires_at.timestamp())
            await redis_pool.zadd(
                "story_cleanup_queue",
                {f"story:{story_id}": delete_at}
            )
        except Exception as e:
            print(f"Redis cleanup job error: {e}")

        # Index in ES
        try:
            recipe_ids = request.recipe_ids if request.recipe_ids else []
            doc = {
                "story_id": story_id,
                "user_id": user_id,
                "story_type": story_type,
                "emotion_preset": request.emotion_preset,
                "challenge_type": None,
                "time_preference": time_preference,
                "recipe_ids": recipe_ids,
                "url": request.url,
                "key": request.key,
                "status": "confirmed",
                "created_at": now.isoformat(),
            }
            await ESClient.index_story(story_id, doc)
        except Exception as e:
            print(f"ES indexing error (non-fatal): {e}")

        story_requests_total.labels(operation="confirm", status="ok").inc()
        story_upload_latency_seconds.labels(operation="confirm").observe(time.time() - start)

        return StoryConfirmResponse(
            story_id=story_id,
            status="confirmed",
        )

    @staticmethod
    async def taste_search(
        params: TasteSearchParams,
        taste_tier: str,
    ) -> TasteSearchResponse:
        """
        Fuzzy ES search with TasteProfile boost.
        Tier from JWT — zero DB queries per boost.
        """
        start = time.time()

        boost = TASTE_TIER_BOOST.get(taste_tier, 1.0)

        results, total = await ESClient.search_stories(
            query=params.q,
            emotion_preset=params.emotion_preset,
            challenge_type=params.challenge_type,
            boost_factor=boost,
            limit=params.limit,
            offset=params.offset,
        )

        hits = [
            StorySearchHit(
                story_id=r["story_id"],
                user_id=r["user_id"],
                story_type=r["story_type"],
                url=r["url"],
                key=r["key"],
                emotion_preset=r.get("emotion_preset"),
                challenge_type=r.get("challenge_type"),
                score=r["score"],
                created_at=r["created_at"],
            )
            for r in results
        ]

        taste_search_latency_seconds.labels(taste_tier=taste_tier).observe(time.time() - start)

        return TasteSearchResponse(results=hits, total=total)

    @staticmethod
    async def get_story(story_id: int, db: AsyncSession) -> StoryDetail | None:
        """Get a single confirmed story."""
        result = await db.execute(
            text("""
                SELECT s.*, COALESCE(
                    ARRAY_AGG(srl.recipe_id ORDER BY srl.display_order)
                    FILTER (WHERE srl.recipe_id IS NOT NULL), '{}'
                ) as recipe_ids
                FROM stories s
                LEFT JOIN story_recipe_links srl ON s.id = srl.story_id
                WHERE s.id = :sid AND s.status = 'confirmed'
                GROUP BY s.id
            """),
            {"sid": story_id},
        )
        row = result.fetchone()
        if not row:
            return None

        return StoryDetail(
            id=row.id,
            user_id=row.user_id,
            url=row.url,
            key=row.key,
            size=row.size,
            mimetype=row.mimetype,
            story_type=row.story_type,
            emotion_preset=row.emotion_preset,
            challenge_type=row.challenge_type,
            time_preference=row.time_preference,
            recipe_ids=list(row.recipe_ids) if row.recipe_ids else [],
            status=row.status,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )

    @staticmethod
    async def get_feed(
        user_id: int | None,
        limit: int,
        offset: int,
        db: AsyncSession,
    ) -> StoryFeedResponse:
        """Get confirmed, non-expired stories feed."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            text("""
                SELECT s.*, COALESCE(
                    ARRAY_AGG(srl.recipe_id ORDER BY srl.display_order)
                    FILTER (WHERE srl.recipe_id IS NOT NULL), '{}'
                ) as recipe_ids
                FROM stories s
                LEFT JOIN story_recipe_links srl ON s.id = srl.story_id
                WHERE s.status = 'confirmed' AND s.expires_at > :now
                GROUP BY s.id
                ORDER BY s.created_at DESC
                LIMIT :lim OFFSET :off
            """),
            {"now": now, "lim": limit + 1, "off": offset},
        )
        rows = result.fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]

        stories = [
            StoryDetail(
                id=r.id,
                user_id=r.user_id,
                url=r.url,
                key=r.key,
                size=r.size,
                mimetype=r.mimetype,
                story_type=r.story_type,
                emotion_preset=r.emotion_preset,
                challenge_type=r.challenge_type,
                time_preference=r.time_preference,
                recipe_ids=list(r.recipe_ids) if r.recipe_ids else [],
                status=r.status,
                expires_at=r.expires_at,
                created_at=r.created_at,
            )
            for r in rows
        ]

        return StoryFeedResponse(stories=stories, has_more=has_more)
