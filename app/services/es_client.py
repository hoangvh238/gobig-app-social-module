"""
Elasticsearch client for story indexing and TasteSearch.
Index name and field conventions follow backend spec.

IMPORTANT: Always use _source filtering to avoid fetching unnecessary data.
ES responses can be huge — only fetch fields we actually need.
"""
from elasticsearch import AsyncElasticsearch
from app.config import settings


class ESClient:
    _client: AsyncElasticsearch | None = None

    @classmethod
    def _get_client(cls) -> AsyncElasticsearch:
        if cls._client is None:
            cls._client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                request_timeout=10,
                max_retries=2,
                retry_on_timeout=True,
            )
        return cls._client

    @classmethod
    async def ensure_index(cls) -> None:
        """
        Ensure index exists with proper mapping.
        Call once at startup — idempotent.
        """
        client = cls._get_client()
        exists = await client.indices.exists(index=settings.es_story_index)
        if not exists:
            await client.indices.create(
                index=settings.es_story_index,
                body={
                    "mappings": {
                        "properties": {
                            "story_id": {"type": "long"},
                            "user_id": {"type": "long"},
                            "story_type": {"type": "keyword"},
                            "emotion_preset": {"type": "keyword"},
                            "challenge_type": {"type": "keyword"},
                            "time_preference": {"type": "keyword"},
                            "recipe_ids": {"type": "long"},
                            "url": {"type": "keyword"},
                            "key": {"type": "keyword"},
                            "status": {"type": "keyword"},
                            "created_at": {"type": "date"},
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    },
                },
            )

    @classmethod
    async def index_story(cls, story_id: int, document: dict) -> None:
        """
        Index a confirmed story document.
        Only index fields we actually search/return — avoid bloat.
        """
        client = cls._get_client()
        await client.index(
            index=settings.es_story_index,
            id=str(story_id),
            document=document,
            refresh=False,  # Don't force refresh — batch indexing is faster
        )

    @classmethod
    async def search_stories(
        cls,
        query: str,
        emotion_preset: str | None = None,
        challenge_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """
        Fuzzy search for stories.
        Zero DB queries — filters applied directly in ES.

        CRITICAL: Use _source filtering to avoid fetching huge ES responses.
        Only fetch fields we actually return to client.
        """
        client = cls._get_client()

        # Build bool query
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["emotion_preset^2", "challenge_type^1.5", "story_type"],
                    "fuzziness": "AUTO",
                    "type": "best_fields",
                }
            }
        ]

        filters = [{"term": {"status": "confirmed"}}]

        if emotion_preset:
            filters.append({"term": {"emotion_preset": emotion_preset}})
        if challenge_type:
            filters.append({"term": {"challenge_type": challenge_type}})

        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filters,
                }
            },
            "_source": [
                "story_id",
                "user_id",
                "story_type",
                "url",
                "key",
                "emotion_preset",
                "challenge_type",
                "created_at",
            ],
            "from": offset,
            "size": limit,
            "sort": [{"_score": "desc"}, {"created_at": "desc"}],
        }

        resp = await client.search(index=settings.es_story_index, body=body)
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]["value"]

        results = []
        for hit in hits:
            doc = hit["_source"]
            doc["score"] = hit["_score"]
            results.append(doc)

        return results, total

    @classmethod
    async def delete_story(cls, story_id: int) -> None:
        """Remove story from index (moderation/expiry)."""
        client = cls._get_client()
        await client.delete(
            index=settings.es_story_index,
            id=str(story_id),
            ignore=[404],
        )

    @classmethod
    async def search_by_hashtag(
        cls,
        hashtag: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict:
        """
        Search recipes by hashtag using ES index.
        Returns recipes with cursor-based pagination.
        """
        client = cls._get_client()

        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"hashtags": hashtag}}
                    ]
                }
            },
            "_source": ["recipe_id", "title", "slug", "author_id"],
            "size": limit + 1,
            "sort": [{"recipe_id": "desc"}]
        }

        if cursor:
            body["search_after"] = [int(cursor)]

        resp = await client.search(index="recipes", body=body)
        hits = resp["hits"]["hits"]

        has_more = len(hits) > limit
        recipes_data = hits[:limit]

        recipes = [hit["_source"] for hit in recipes_data]
        next_cursor = str(recipes[-1]["recipe_id"]) if has_more and recipes else None

        return {
            "recipes": recipes,
            "next_cursor": next_cursor
        }

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
