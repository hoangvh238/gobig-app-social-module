from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
    CollectionItemAdd
)
from app.services.collection_service import CollectionService

router = APIRouter(prefix="/collections", tags=["collections"])


def get_current_user_id() -> int:
    return 1


@router.post("", response_model=CollectionResponse, status_code=201)
async def create_collection(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CollectionService(db)
    collection = await service.create_collection(user_id, data)
    await db.commit()
    return collection


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CollectionService(db)
    collection = await service.update_collection(collection_id, user_id, data)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found or unauthorized")
    await db.commit()
    return collection


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CollectionService(db)
    success = await service.delete_collection(collection_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found or unauthorized")
    await db.commit()


@router.get("", response_model=CollectionListResponse)
async def list_collections(
    offline_sync: bool | None = Query(None),
    cursor: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CollectionService(db)
    return await service.list_collections(user_id, offline_sync, cursor, limit)


@router.post("/{collection_id}/items", status_code=204)
async def add_item_to_collection(
    collection_id: int,
    data: CollectionItemAdd,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    service = CollectionService(db)
    success = await service.add_item(collection_id, user_id, data)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found or unauthorized")
    await db.commit()
