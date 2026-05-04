"""
Background worker to cleanup expired stories.
Reads from Redis sorted set 'story_cleanup_queue' and deletes expired stories.
Deletes: PostgreSQL record + ES index + B2 file (via storage service)
"""
import asyncio
import httpx
from datetime import datetime, timezone

from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.es_client import ESClient
from app.config import settings

try:
    from app.redis_client import redis_pool
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False
    print("Redis not available - story cleanup worker disabled")


async def cleanup_expired_stories():
    """
    Check story_cleanup_queue for expired stories and delete them.
    Runs every 5 minutes.
    """
    if not REDIS_AVAILABLE:
        return

    async with httpx.AsyncClient(timeout=30.0) as http_client:
        while True:
            try:
                now = int(datetime.now(timezone.utc).timestamp())

                # Get expired stories (score <= now)
                expired = await redis_pool.zrangebyscore(
                    "story_cleanup_queue",
                    min=0,
                    max=now,
                    start=0,
                    num=100  # Process 100 at a time
                )

                if expired:
                    print(f"[Cleanup] Found {len(expired)} expired stories")

                    async with AsyncSessionLocal() as db:
                        for item in expired:
                            story_id_str = item.decode() if isinstance(item, bytes) else item
                            # Format: "story:123"
                            if not story_id_str.startswith("story:"):
                                continue

                            story_id = int(story_id_str.split(":", 1)[1])

                            # Get story key before deleting
                            result = await db.execute(
                                text("SELECT key FROM stories WHERE id = :sid"),
                                {"sid": story_id}
                            )
                            row = result.fetchone()

                            if row:
                                story_key = row.key

                                # Delete file from B2 via storage service
                                try:
                                    delete_resp = await http_client.delete(
                                        f"{settings.upload_service_url}/api/delete/{story_key}"
                                    )
                                    if delete_resp.status_code == 200:
                                        print(f"[Cleanup] Deleted B2 file: {story_key}")
                                    else:
                                        print(f"[Cleanup] B2 delete failed for {story_key}: {delete_resp.status_code}")
                                except Exception as e:
                                    print(f"[Cleanup] B2 delete error for {story_key}: {e}")

                            # Delete from PostgreSQL
                            await db.execute(
                                text("DELETE FROM stories WHERE id = :sid"),
                                {"sid": story_id}
                            )

                            # Delete from ES
                            try:
                                await ESClient.delete_story(story_id)
                            except Exception as e:
                                print(f"[Cleanup] ES delete error for story {story_id}: {e}")

                            # Remove from queue
                            await redis_pool.zrem("story_cleanup_queue", story_id_str)

                            print(f"[Cleanup] Deleted story {story_id}")

                        await db.commit()

            except Exception as e:
                print(f"[Cleanup] Error: {e}")

            # Sleep 5 minutes
            await asyncio.sleep(300)


if __name__ == "__main__":
    print("[Cleanup] Starting story cleanup worker...")
    asyncio.run(cleanup_expired_stories())
