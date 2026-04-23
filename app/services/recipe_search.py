"""
Recipe search via Elasticsearch.
Integrates with recipes index for search functionality.

CRITICAL: Always use _source filtering to avoid fetching huge recipe documents.
Recipe docs can contain large ingredient lists, instructions, etc.
"""
from elasticsearch import AsyncElasticsearch
from app.config import settings


class RecipeSearchClient:
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
    async def search_recipes(
        cls,
        query: str,
        filters: dict | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """
        Search recipes in ES index.

        IMPORTANT: Only fetch minimal fields to avoid token waste.
        Full recipe docs can be 10KB+ each with ingredients/instructions.
        """
        client = cls._get_client()

        must = []
        if query:
            must.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description^2", "tags"],
                    "fuzziness": "AUTO",
                    "type": "best_fields",
                }
            })

        filter_clauses = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {field: value}})
                else:
                    filter_clauses.append({"term": {field: value}})

        body = {
            "query": {
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "_source": [
                "recipe_id",
                "title",
                "description",
                "author_id",
                "tags",
                "difficulty",
                "prep_time_min",
                "cook_time_min",
                "servings",
                "created_at",
            ],  # ONLY minimal fields — no ingredients/instructions
            "from": offset,
            "size": limit,
            "sort": [{"_score": "desc"}, {"created_at": "desc"}],
        }

        resp = await client.search(index="recipes", body=body)
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]["value"]

        results = []
        for hit in hits:
            doc = hit["_source"]
            doc["score"] = hit["_score"]
            results.append(doc)

        return results, total

    @classmethod
    async def get_recipe_by_id(cls, recipe_id: int) -> dict | None:
        """
        Get single recipe by ID.
        Use _source filtering even for single doc — avoid fetching unnecessary fields.
        """
        client = cls._get_client()
        try:
            resp = await client.get(
                index="recipes",
                id=str(recipe_id),
                _source=[
                    "recipe_id",
                    "title",
                    "description",
                    "author_id",
                    "tags",
                    "difficulty",
                    "prep_time_min",
                    "cook_time_min",
                    "servings",
                    "created_at",
                ],
            )
            return resp["_source"]
        except Exception:
            return None

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
