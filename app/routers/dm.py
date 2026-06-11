import starlette
import asyncio
import json
import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import array as pg_array

from app.database import get_db, AsyncSessionLocal
from app.auth import get_current_user_id
from app.models.social import Conversation, Message
from app.schemas.dm import ConversationStartRequest, ConversationResponse
from app.services.safety import is_blocked
from app.metrics import dm_rate_limit_hits_total

log = structlog.get_logger()

router = APIRouter(tags=["dm"])

_MAX_MSGS_PER_MINUTE = 60
_MAX_CONTENT_LEN = 2000


@router.post("/conversations/start", response_model=ConversationResponse, status_code=201)
async def start_conversation(
    data: ConversationStartRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if data.recipient_id == user_id:
        raise HTTPException(status_code=422, detail="Cannot start conversation with yourself")

    if await is_blocked(user_id, data.recipient_id, db):
        raise HTTPException(status_code=403, detail="Blocked")

    result = await db.execute(
        select(Conversation).where(
            Conversation.participant_ids.op("@>")(
                pg_array([user_id, data.recipient_id]
            # FIX: THÊM RÀNG BUỘC NÀY Mảng chỉ có 2 thôi 
                )
            )
        )
    )
    conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversation(participant_ids=[user_id, data.recipient_id])
        db.add(conv)
        await db.flush()
        await db.refresh(conv)
        await db.commit()

    return ConversationResponse.model_validate(conv)


@router.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket,
    conversation_id: int = Query(...),
):
    user_id = _auth_from_headers(websocket)
    if not user_id:
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        conv = await db.get(Conversation, conversation_id)
        if not conv or user_id not in conv.participant_ids:
            await websocket.close(code=4003)
            return

    await websocket.accept()

    from app.redis_client import redis_pool

    channel = f"conv:{conversation_id}"
    pubsub = redis_pool.pubsub()
    await pubsub.subscribe(channel)

    # FIX: Biến đếm in-memory rl_count sẽ bị reset mỗi lần user reconnect, cho phép bypass rate limit dễ dàng. Yêu cầu Fix:
    # Đưa state rate-limit vào Redis để quản lý tập trung:
    rl_window = time.monotonic()
    rl_count = 0

    async def _redis_to_ws():
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    await websocket.send_text(msg["data"])
        except Exception:
            pass

    listener = asyncio.create_task(_redis_to_ws())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event_type = data.get("type")

            if event_type in ("typing_start", "typing_stop"):
                await redis_pool.publish(
                    channel,
                    json.dumps({
                        "type": event_type,
                        "user_id": user_id,
                        "conversation_id": conversation_id,
                    }),
                )
                continue

            if event_type == "message_read":
                message_id = data.get("message_id")
                if message_id:
                    await _mark_read(message_id, user_id, conversation_id, redis_pool, channel)
                continue

            if event_type != "message_sent":
                continue

            content = str(data.get("content", "")).strip()
            if not content:
                continue

            now = time.monotonic()
            if now - rl_window >= 60.0:
                rl_window, rl_count = now, 0
            rl_count += 1

            if rl_count > _MAX_MSGS_PER_MINUTE or len(content) > _MAX_CONTENT_LEN:
                dm_rate_limit_hits_total.inc()
                log.warning(
                    "dm_rate_limit_exceeded",
                    user_id=user_id,
                    conversation_id=conversation_id,
                    count=rl_count,
                    content_len=len(content),
                )
                await websocket.close(code=4029)
                return

            msg = await _persist_message(conversation_id, user_id, content)
            await redis_pool.publish(
                channel,
                json.dumps({
                    "type": "message_sent",
                    "id": msg.id,
                    "conversation_id": conversation_id,
                    "sender_id": user_id,
                    "content": content,
                    "created_at": msg.created_at.isoformat(),
                }),
            )

    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws_chat_error", user_id=user_id, conversation_id=conversation_id)
    finally:
        listener.cancel()
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass

# Fix: Websocket trên web ko hỗ trợ truyền custom header đâu. 
def _auth_from_headers(websocket: WebSocket) -> int | None:
    raw = websocket.headers.get("x-user-id")
    if raw and raw.isdigit():
        uid = int(raw)
        return uid if uid > 0 else None
    return None


async def _persist_message(conversation_id: int, sender_id: int, content: str) -> Message:
    async with AsyncSessionLocal() as db:
        msg = Message(conversation_id=conversation_id, sender_id=sender_id, content=content)
        db.add(msg)
        await db.flush()

        conv = await db.get(Conversation, conversation_id)
        if conv:
            conv.last_message_at = datetime.now(timezone.utc)

        await db.refresh(msg)
        await db.commit()
        return msg


async def _mark_read(message_id: int, user_id: int, conversation_id: int, redis_pool, channel: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message).where(
                Message.id == message_id,
                Message.conversation_id == conversation_id,
                Message.read_at.is_(None),
                # Message.sender_id != user_id,  # FIX: Xóa dòng này để đảm bảo gửi cho chính mình vẫn được
            )
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return

        msg.read_at = datetime.now(timezone.utc)
        await db.commit()

    await redis_pool.publish(
        channel,
        json.dumps({
            "type": "message_read",
            "message_id": message_id,
            "reader_id": user_id,
            "conversation_id": conversation_id,
        }),
    )
