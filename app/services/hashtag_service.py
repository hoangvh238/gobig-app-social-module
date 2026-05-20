from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models.social import Hashtag, RecipeHashtag
from app.schemas.hashtag import HashtagResponse, HashtagRecipeListResponse
from app.services.es_client import ESClient
import re


class HashtagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def normalize_hashtag(tag: str) -> str:
        tag = tag.strip().lower()
        if tag.startswith("#"):
            tag = tag[1:]
        return tag

    @staticmethod
    def extract_hashtags(content: str) -> list[str]:
        pattern = r'#(\w+)'
        matches = re.findall(pattern, content)
        normalized = [HashtagService.normalize_hashtag(tag) for tag in matches]
        return list(dict.fromkeys(normalized))

    async def get_or_create_hashtag(self, tag_name: str) -> Hashtag:
        normalized = self.normalize_hashtag(tag_name)

        result = await self.db.execute(
            select(Hashtag).where(Hashtag.name == normalized)
        )
        hashtag = result.scalar_one_or_none()

        if not hashtag:
            hashtag = Hashtag(name=normalized, usage_count=0)
            self.db.add(hashtag)
            await self.db.flush()
            await self.db.refresh(hashtag)

        return hashtag

    async def link_hashtags_to_recipe(self, recipe_id: int, content: str) -> None:
        hashtags = self.extract_hashtags(content)

        for tag_name in hashtags:
            hashtag = await self.get_or_create_hashtag(tag_name)

            result = await self.db.execute(
                select(RecipeHashtag).where(
                    RecipeHashtag.recipe_id == recipe_id,
                    RecipeHashtag.hashtag_id == hashtag.id
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                recipe_hashtag = RecipeHashtag(
                    recipe_id=recipe_id,
                    hashtag_id=hashtag.id
                )
                self.db.add(recipe_hashtag)

                await self.db.execute(
                    text("UPDATE hashtags SET usage_count = usage_count + 1 WHERE id = :id"),
                    {"id": hashtag.id}
                )

        await self.db.flush()

    async def get_recipes_by_hashtag(
        self,
        tag_name: str,
        cursor: str | None = None,
        limit: int = 20
    ) -> HashtagRecipeListResponse:
        normalized = self.normalize_hashtag(tag_name)

        es_client = ESClient()
        results = await es_client.search_by_hashtag(normalized, cursor, limit)

        return HashtagRecipeListResponse(
            recipes=results.get("recipes", []),
            next_cursor=results.get("next_cursor")
        )

    async def get_hashtag(self, tag_name: str) -> HashtagResponse | None:
        normalized = self.normalize_hashtag(tag_name)

        result = await self.db.execute(
            select(Hashtag).where(Hashtag.name == normalized)
        )
        hashtag = result.scalar_one_or_none()

        if not hashtag:
            return None

        return HashtagResponse(
            id=hashtag.id,
            name=hashtag.name,
            usage_count=hashtag.usage_count,
            created_at=hashtag.created_at
        )
