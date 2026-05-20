from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.social import Collection, CollectionItem
from app.models.legacy_models import Recipe
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionMinimalResponse,
    CollectionListResponse,
    CollectionItemAdd
)
import uuid


class CollectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_collection(self, user_id: int, data: CollectionCreate) -> CollectionResponse:
        collection = Collection(
            user_id=user_id,
            title=data.title,
            description=data.description,
            offline_sync=data.offline_sync
        )
        self.db.add(collection)
        await self.db.flush()
        await self.db.refresh(collection)

        return CollectionResponse(
            id=collection.id,
            user_id=collection.user_id,
            title=collection.title,
            description=collection.description,
            offline_sync=collection.offline_sync,
            created_at=collection.created_at,
            updated_at=collection.updated_at
        )

    async def update_collection(
        self,
        collection_id: int,
        user_id: int,
        data: CollectionUpdate
    ) -> CollectionResponse | None:
        result = await self.db.execute(
            select(Collection).where(
                and_(
                    Collection.id == collection_id,
                    Collection.user_id == user_id
                )
            )
        )
        collection = result.scalar_one_or_none()
        if not collection:
            return None

        if data.title is not None:
            collection.title = data.title
        if data.description is not None:
            collection.description = data.description
        if data.offline_sync is not None:
            collection.offline_sync = data.offline_sync

        collection.updated_at = func.now()
        await self.db.flush()

        return CollectionResponse(
            id=collection.id,
            user_id=collection.user_id,
            title=collection.title,
            description=collection.description,
            offline_sync=collection.offline_sync,
            created_at=collection.created_at,
            updated_at=collection.updated_at
        )

    async def delete_collection(self, collection_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(Collection).where(
                and_(
                    Collection.id == collection_id,
                    Collection.user_id == user_id
                )
            )
        )
        collection = result.scalar_one_or_none()
        if not collection:
            return False

        await self.db.delete(collection)
        await self.db.flush()
        return True

    async def list_collections(
        self,
        user_id: int,
        offline_sync: bool | None = None,
        cursor: int | None = None,
        limit: int = 20
    ) -> CollectionListResponse:
        query = select(Collection).where(Collection.user_id == user_id)

        if offline_sync is not None:
            query = query.where(Collection.offline_sync == offline_sync)

        query = query.order_by(Collection.id.desc()).limit(limit + 1)

        if cursor:
            query = query.where(Collection.id < cursor)

        result = await self.db.execute(query)
        collections_data = result.scalars().all()

        has_more = len(collections_data) > limit
        collections = collections_data[:limit]

        if offline_sync:
            response_collections = []
            for collection in collections:
                image_url, ingredient_summary = await self._get_minimal_payload(collection.id)
                response_collections.append(
                    CollectionMinimalResponse(
                        id=collection.id,
                        title=collection.title,
                        image_url=image_url,
                        ingredient_summary=ingredient_summary
                    )
                )
        else:
            response_collections = [
                CollectionResponse(
                    id=c.id,
                    user_id=c.user_id,
                    title=c.title,
                    description=c.description,
                    offline_sync=c.offline_sync,
                    created_at=c.created_at,
                    updated_at=c.updated_at
                )
                for c in collections
            ]

        next_cursor = collections[-1].id if has_more and collections else None
        return CollectionListResponse(collections=response_collections, next_cursor=next_cursor)

    async def add_item(
        self,
        collection_id: int,
        user_id: int,
        data: CollectionItemAdd
    ) -> bool:
        result = await self.db.execute(
            select(Collection).where(
                and_(
                    Collection.id == collection_id,
                    Collection.user_id == user_id
                )
            )
        )
        collection = result.scalar_one_or_none()
        if not collection:
            return False

        max_order_result = await self.db.execute(
            select(func.max(CollectionItem._order)).where(
                CollectionItem._parent_id == collection_id
            )
        )
        max_order = max_order_result.scalar() or 0

        item = CollectionItem(
            id=str(uuid.uuid4()),
            _order=max_order + 1,
            _parent_id=collection_id,
            recipe_id=data.recipe_id,
            notes=data.notes
        )
        self.db.add(item)
        await self.db.flush()
        return True

    async def _get_minimal_payload(self, collection_id: int) -> tuple[str | None, str | None]:
        result = await self.db.execute(
            select(CollectionItem, Recipe)
            .join(Recipe, CollectionItem.recipe_id == Recipe.id)
            .where(CollectionItem._parent_id == collection_id)
            .order_by(CollectionItem._order.asc())
            .limit(1)
        )
        row = result.first()

        if not row:
            return None, None

        item, recipe = row
        image_url = f"https://cdn.example.com/recipes/{recipe.id}/thumb.jpg"
        ingredient_summary = f"{recipe.title} ingredients"

        return image_url, ingredient_summary
