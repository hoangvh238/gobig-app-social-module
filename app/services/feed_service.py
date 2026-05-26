import json
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select, func, text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


from app.models.social import Like, Comment, CollectionItem, Collection, Follow
from app.models.legacy_models import User, Recipe
from app.schemas.feed import RecipeSocialMeta, AuthorProfile
from app.metrics import (
    feed_enrich_latency_seconds,
    feed_enrich_requests_total,
    redis_cache_hits_total,
    redis_cache_misses_total
)
from app.emotion_context_config import EMOTION_CONTEXT_HASHTAG_MAPPING
from app.services.safety import get_blocked_ids, get_muted_ids
import time

try:
    from app.redis_client import redis_pool
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False


class FeedService:
    CACHE_TTL = 300
    CACHE_KEY_PREFIX = "feed_enrich"
    STREAM_NAME = "feed-events"

    @staticmethod
    async def enrich_feed(
        device_ranked_ids: list[str],
        emotion_context: str,
        taste_profile_hash: str | None,
        inventory_hash: str | None,
        frugal_mode: bool,
        user_id: int | None,
        db: AsyncSession
    ) -> list[RecipeSocialMeta]:
        """
        Enrich feed items with social metadata.
        """
        start_time = time.time()

        feed_enrich_requests_total.labels(
            emotion_context=emotion_context,
            frugal_mode=str(frugal_mode)
        ).inc()

        if not device_ranked_ids:
            feed_enrich_latency_seconds.observe(time.time() - start_time)
            return []

        recipe_ids = [int(rid) for rid in device_ranked_ids]

        cached_data = {}
        cache_keys = []
        date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if REDIS_AVAILABLE:
            try:
                for recipe_id in recipe_ids:
                    cache_key = f"{FeedService.CACHE_KEY_PREFIX}:{recipe_id}:{emotion_context}:{date_utc}"
                    cache_keys.append(cache_key)

                cached_values = await redis_pool.mget(cache_keys)

                for i, value in enumerate(cached_values):
                    if value:
                        cached_data[recipe_ids[i]] = json.loads(value)
                        redis_cache_hits_total.inc()
                    else:
                        redis_cache_misses_total.inc()
            except Exception as e:
                print(f"Redis MGET error: {e}")

        missing_ids = [rid for rid in recipe_ids if rid not in cached_data]

        blocked_author_ids: set[int] = set()
        if user_id:
            blocked_author_ids = (
                await get_blocked_ids(user_id, db) | await get_muted_ids(user_id, db)
            )

        if missing_ids:
            query = text("""
                SELECT
                    r.id as recipe_id,
                    r.title,
                    r.slug,
                    r.featured_image_id,
                    r.prep_time,
                    r.cook_time,
                    r.servings,
                    r.difficulty,
                    r.rating,
                    r.description,
                    u.id as author_id,
                    u.name as author_name,
                    u.avatar_url as author_avatar_url,
                    COALESCE(lc.like_count, 0) as like_count,
                    COALESCE(cc.comment_count, 0) as comment_count,
                    STRING_AGG(h.name, ',') as tags
                FROM recipes r
                LEFT JOIN users u ON r.author_id = u.id
                LEFT JOIN (
                    SELECT recipe_id, COUNT(*) as like_count
                    FROM likes
                    WHERE recipe_id IN :recipe_ids
                    GROUP BY recipe_id
                ) lc ON r.id = lc.recipe_id
                LEFT JOIN (
                    SELECT recipe_id, COUNT(*) as comment_count
                    FROM comments
                    WHERE recipe_id IN :recipe_ids AND is_deleted = FALSE
                    GROUP BY recipe_id
                ) cc ON r.id = cc.recipe_id
                LEFT JOIN recipe_hashtags rh ON r.id = rh.recipe_id
                LEFT JOIN hashtags h ON rh.hashtag_id = h.id
                WHERE r.id IN :recipe_ids
                GROUP BY r.id, u.id, lc.like_count, cc.comment_count
            """)

            result = await db.execute(query.bindparams(bindparam("recipe_ids", expanding=True)), {"recipe_ids": missing_ids})
            rows = result.fetchall()

            for row in rows:
                # Skip recipes from blocked/muted authors
                if row.author_id and row.author_id in blocked_author_ids:
                    continue

                # Parse tags from the concatenated string
                tags = []
                if row.tags:
                    tags = [tag.strip() for tag in row.tags.split(',') if tag.strip()]

                data = {
                    "recipe_id": row.recipe_id,
                    "title": row.title,
                    "slug": row.slug,
                    "featured_image_id": row.featured_image_id,
                    "prep_time": row.prep_time,
                    "cook_time": row.cook_time,
                    "servings": row.servings,
                    "difficulty": row.difficulty,
                    "rating": float(row.rating) if row.rating else None,
                    "description": row.description,
                    "author": {
                        "id": row.author_id,
                        "name": row.author_name,
                        "avatar_id": row.author_avatar_url
                    },
                    "like_count": int(row.like_count),
                    "comment_count": int(row.comment_count),
                    "tags": tags
                }

                cached_data[row.recipe_id] = data

                if REDIS_AVAILABLE:
                    try:
                        cache_key = f"{FeedService.CACHE_KEY_PREFIX}:{row.recipe_id}:{emotion_context}:{date_utc}"
                        await redis_pool.setex(
                            cache_key,
                            FeedService.CACHE_TTL,
                            json.dumps(data, cls=_DecimalEncoder)
                        )
                    except Exception as e:
                        print(f"Redis cache write error: {e}")

        frugal_recipe_ids = set()

        if frugal_mode and recipe_ids:
            frugal_hashtags = EMOTION_CONTEXT_HASHTAG_MAPPING.get("frugal_mode", [])
            if frugal_hashtags:
                frugal_query = text("""
                    SELECT DISTINCT rh.recipe_id
                    FROM recipe_hashtags rh
                    JOIN hashtags h ON rh.hashtag_id = h.id
                    WHERE rh.recipe_id IN :recipe_ids
                    AND LOWER(h.name) IN :frugal_tags
                """)

                frugal_result = await db.execute(
                    frugal_query.bindparams(
                        bindparam("recipe_ids", expanding=True),
                        bindparam("frugal_tags", expanding=True),
                    ),
                    {"recipe_ids": recipe_ids, "frugal_tags": [t.lower() for t in frugal_hashtags]}
                )
                frugal_rows = frugal_result.fetchall()
                frugal_recipe_ids.update(row[0] for row in frugal_rows)


        user_likes = set()
        user_saved = set()

        if user_id:
            likes_query = select(Like.recipe_id).where(
                Like.user_id == user_id,
                Like.recipe_id.in_(recipe_ids)
            )
            likes_result = await db.execute(likes_query)
            user_likes = {row[0] for row in likes_result.fetchall()}

            saved_query = select(CollectionItem.recipe_id).join(
                Collection, Collection.id == CollectionItem._parent_id
            ).where(
                Collection.user_id == user_id,
                CollectionItem.recipe_id.in_(recipe_ids)
            )
            saved_result = await db.execute(saved_query)
            user_saved = {row[0] for row in saved_result.fetchall()}

        result = []
        for recipe_id in recipe_ids:
            data = cached_data.get(recipe_id)
            if not data:
                continue

            # Filter out cached results from blocked/muted authors
            author_id = data.get("author", {}).get("id")
            if author_id and author_id in blocked_author_ids:
                continue

            result.append(RecipeSocialMeta(
                recipe_id=data["recipe_id"],
                title=data["title"],
                slug=data["slug"],
                featured_image_id=data["featured_image_id"],
                prep_time=data["prep_time"],
                cook_time=data["cook_time"],
                servings=data["servings"],
                difficulty=data["difficulty"],
                rating=data["rating"],
                description=data["description"],
                author=AuthorProfile(**data["author"]),
                like_count=data["like_count"],
                comment_count=data["comment_count"],
                is_liked=recipe_id in user_likes,
                is_saved=recipe_id in user_saved,
                tags=data["tags"]
            ))

        latency = time.time() - start_time
        if REDIS_AVAILABLE:
            try:
                await redis_pool.xadd(
                    FeedService.STREAM_NAME,
                    {
                        "event_type": "feed_enrich",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "user_id": str(user_id) if user_id else "anonymous",
                        "emotion_context": emotion_context,
                        "frugal_mode": str(frugal_mode),
                        "recipe_count": str(len(result)),
                        "latency_ms": str(int(latency * 1000)),
                        "cache_hit_rate": str(len(cached_data) / len(recipe_ids) if recipe_ids else 0)
                    }
                )
            except Exception as e:
                print(f"Redis Stream XADD error: {e}")

        feed_enrich_latency_seconds.observe(latency)

        return result

    @staticmethod
    def is_recipe_matching_emotion_context(recipe_tags: list[str], emotion_context: str) -> bool:
        """
        Check if a recipe's tags match the specified emotion context.
        """
        context_tags = EMOTION_CONTEXT_HASHTAG_MAPPING.get(emotion_context, [])
        recipe_tags_lower = [tag.lower() for tag in recipe_tags]

        for tag in context_tags:
            if tag.lower() in recipe_tags_lower:
                return True

        return False

    @staticmethod
    async def invalidate_cache(recipe_id: int):
        if REDIS_AVAILABLE:
            try:
                date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                emotions = ["lazy_night", "date_night", "family_chaos", "default"]
                for emotion in emotions:
                    cache_key = f"{FeedService.CACHE_KEY_PREFIX}:{recipe_id}:{emotion}:{date_utc}"
                    await redis_pool.delete(cache_key)
            except Exception as e:
                print(f"Redis cache invalidation error: {e}")
