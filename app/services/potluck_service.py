"""
Potluck social layer — separate Redis keys from core potluck:{session_id}.
We use potluck_social:{session_id} exclusively. Never modify core potluck hash.
"""
import json
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.potluck import (
    PotluckSocialStateRequest, PotluckSocialStateResponse,
    RSVPRequest, RSVPResponse,
    BuddySuggestRequest, BuddySuggestResponse, BuddySuggestion,
    PotluckPingRequest, PotluckPingResponse,
)
from app.metrics import potluck_requests_total

try:
    from app.redis_client import redis_pool
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False


REDIS_KEY_PREFIX = "potluck_social"


def _key(session_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}:{session_id}"


class PotluckService:

    @staticmethod
    async def set_state(
        user_id: int,
        request: PotluckSocialStateRequest,
        db: AsyncSession,
    ) -> PotluckSocialStateResponse:
        """Create/update social state in Redis. Never touches core potluck:{id}."""
        potluck_requests_total.labels(operation="set_state").inc()

        # Verify user is the host of this session
        if REDIS_AVAILABLE:
            core_key = f"potluck:{request.session_id}"
            host_id_str = await redis_pool.hget(core_key, "host_id")
            if host_id_str and int(host_id_str) != user_id:
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Only session host can update state")

        state = {
            "friends_only": str(int(request.friends_only)),
            "invite_from_followers": str(int(request.invite_from_followers)),
            "slot_duration_min": str(request.slot_duration_min.value),
            "host_controls": json.dumps(request.host_controls),
        }

        if REDIS_AVAILABLE:
            key = _key(request.session_id)
            await redis_pool.hset(key, mapping=state)
            await redis_pool.expire(key, 86400)  # 24h TTL

        # Audit event
        await db.execute(
            text("""
                INSERT INTO potluck_social_events (session_id, event_type, actor_id, payload_json)
                VALUES (:sid, 'state_updated', :uid, :payload)
            """),
            {"sid": request.session_id, "uid": user_id, "payload": json.dumps(state)},
        )
        await db.commit()

        return PotluckSocialStateResponse(
            session_id=request.session_id,
            friends_only=request.friends_only,
            invite_from_followers=request.invite_from_followers,
            rsvp={},
            host_controls=request.host_controls,
            slot_duration_min=request.slot_duration_min.value,
        )

    @staticmethod
    async def get_state(session_id: str) -> PotluckSocialStateResponse | None:
        """Read social state from Redis."""
        potluck_requests_total.labels(operation="get_state").inc()

        if not REDIS_AVAILABLE:
            return None

        key = _key(session_id)
        data = await redis_pool.hgetall(key)
        if not data:
            return None

        # Collect RSVP entries
        rsvp = {}
        for k, v in data.items():
            if k.startswith("rsvp:"):
                user_id_str = k.split(":", 1)[1]
                rsvp[user_id_str] = v

        return PotluckSocialStateResponse(
            session_id=session_id,
            friends_only=bool(int(data.get("friends_only", "0"))),
            invite_from_followers=bool(int(data.get("invite_from_followers", "1"))),
            rsvp=rsvp,
            host_controls=json.loads(data.get("host_controls", "{}")),
            slot_duration_min=int(data.get("slot_duration_min", "30")),
        )

    @staticmethod
    async def rsvp(
        user_id: int,
        request: RSVPRequest,
        db: AsyncSession,
    ) -> RSVPResponse:
        """RSVP to a potluck session. Stored in Redis hash field rsvp:{user_id}."""
        potluck_requests_total.labels(operation="rsvp").inc()

        # Validate user is allowed to RSVP based on session settings
        if REDIS_AVAILABLE:
            key = _key(request.session_id)
            data = await redis_pool.hgetall(key)

            if data:
                friends_only = bool(int(data.get("friends_only", "0")))
                invite_from_followers = bool(int(data.get("invite_from_followers", "1")))

                # Get host_id from core potluck key
                core_key = f"potluck:{request.session_id}"
                host_id_str = await redis_pool.hget(core_key, "host_id")

                if host_id_str:
                    host_id = int(host_id_str)

                    # Skip validation if user is the host
                    if user_id != host_id:
                        if friends_only:
                            # Check if user is mutual follow with host
                            mutual_check = await db.execute(
                                text("""
                                    SELECT 1 FROM follows f1
                                    INNER JOIN follows f2
                                        ON f1.following_id = f2.follower_id
                                        AND f2.following_id = f1.follower_id
                                    WHERE f1.follower_id = :host_id
                                        AND f1.following_id = :user_id
                                    LIMIT 1
                                """),
                                {"host_id": host_id, "user_id": user_id},
                            )
                            if not mutual_check.fetchone():
                                from fastapi import HTTPException
                                raise HTTPException(status_code=403, detail="Session is friends-only")

                        elif not invite_from_followers:
                            # If invite_from_followers is false, only explicitly invited users can RSVP
                            # Check if user has been invited (has existing RSVP entry or is in invite list)
                            existing_rsvp = data.get(f"rsvp:{user_id}")
                            if not existing_rsvp:
                                from fastapi import HTTPException
                                raise HTTPException(status_code=403, detail="You must be invited to RSVP")

            await redis_pool.hset(key, f"rsvp:{user_id}", request.status)

        await db.execute(
            text("""
                INSERT INTO potluck_social_events (session_id, event_type, actor_id, payload_json)
                VALUES (:sid, 'rsvp', :uid, :payload)
            """),
            {
                "sid": request.session_id,
                "uid": user_id,
                "payload": json.dumps({"status": request.status}),
            },
        )
        await db.commit()

        return RSVPResponse(
            session_id=request.session_id,
            user_id=user_id,
            status=request.status,
        )

    @staticmethod
    async def suggest_buddies(
        user_id: int,
        request: BuddySuggestRequest,
        db: AsyncSession,
    ) -> BuddySuggestResponse:
        """
        Cook-buddy suggestions:
        - Follow graph overlap (mutual follows)
        - Hashed inventory compatibility (from dish scorer, no raw inventory)
        Combined score = 0.4 * compatibility + 0.6 * normalized_mutual_follows
        """
        potluck_requests_total.labels(operation="suggest_buddies").inc()

        # Get mutual follows (users who follow me AND I follow them)
        mutual_result = await db.execute(
            text("""
                SELECT f1.following_id as user_id,
                       u.name as display_name,
                       u.avatar_id
                FROM follows f1
                INNER JOIN follows f2
                    ON f1.following_id = f2.follower_id
                    AND f2.following_id = f1.follower_id
                LEFT JOIN users u ON f1.following_id = u.id
                WHERE f1.follower_id = :uid
                LIMIT :lim
            """),
            {"uid": user_id, "lim": request.limit * 3},  # fetch more, rank later
        )
        mutual_rows = mutual_result.fetchall()

        if not mutual_rows:
            return BuddySuggestResponse(suggestions=[])

        # Get hashed inventory compatibility scores from Redis
        # Key pattern: inventory_compat:{user_id} → hash of {other_user_id: score}
        compatibility_scores: dict[int, float] = {}
        if REDIS_AVAILABLE:
            try:
                compat_key = f"inventory_compat:{user_id}"
                buddy_ids = [str(row.user_id) for row in mutual_rows]
                scores = await redis_pool.hmget(compat_key, *buddy_ids)
                for i, score in enumerate(scores):
                    if score is not None:
                        compatibility_scores[mutual_rows[i].user_id] = float(score)
            except Exception:
                pass  # graceful degradation — rank by follow graph only

        # Compute combined scores
        max_mutual = len(mutual_rows)
        suggestions = []
        for i, row in enumerate(mutual_rows):
            compat = compatibility_scores.get(row.user_id, 0.5)  # default 0.5 if unknown
            normalized_mutual = (max_mutual - i) / max_mutual  # position-based proxy

            combined = 0.4 * compat + 0.6 * normalized_mutual

            suggestions.append(BuddySuggestion(
                user_id=row.user_id,
                display_name=row.display_name,
                avatar_id=f"https://cdn.example.com/avatars/{row.avatar_id}.jpg" if row.avatar_id else None,
                compatibility_score=round(compat, 3),
                mutual_follows=max_mutual - i,
                combined_score=round(combined, 3),
            ))

        # Sort by combined score, take top N
        suggestions.sort(key=lambda s: s.combined_score, reverse=True)
        suggestions = suggestions[:request.limit]

        return BuddySuggestResponse(suggestions=suggestions)

    @staticmethod
    async def ping(
        user_id: int,
        request: PotluckPingRequest,
        db: AsyncSession,
    ) -> PotluckPingResponse:
        """
        Send a DM ping to multiple users — creates messages in conversations/messages tables.
        NEVER creates a live_room. These are simple DMs.
        """
        potluck_requests_total.labels(operation="ping").inc()

        sent_to = []
        failed = []
        message_ids = []

        # Remove self from target list
        target_user_ids = [uid for uid in request.target_user_ids if uid != user_id]

        if not target_user_ids:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Cannot ping yourself or empty user list")

        # Check blocks/mutes for all targets in one query
        block_check = await db.execute(
            text("""
                SELECT blocked_id as user_id FROM blocks
                WHERE blocker_id = ANY(:target_ids) AND blocked_id = :sender_id
                UNION
                SELECT muted_id as user_id FROM mutes
                WHERE muter_id = ANY(:target_ids) AND muted_id = :sender_id
            """),
            {"target_ids": target_user_ids, "sender_id": user_id},
        )
        blocked_by = {row.user_id for row in block_check.fetchall()}

        # Send message to each target
        for target_user_id in target_user_ids:
            try:
                # Skip if blocked/muted
                if target_user_id in blocked_by:
                    failed.append(target_user_id)
                    continue

                # Find or create conversation
                conv_result = await db.execute(
                    text("""
                        SELECT id FROM conversations
                        WHERE participant_ids @> ARRAY[:uid1, :uid2]::INTEGER[]
                          AND participant_ids <@ ARRAY[:uid1, :uid2]::INTEGER[]
                        LIMIT 1
                    """),
                    {"uid1": user_id, "uid2": target_user_id},
                )
                conv_row = conv_result.fetchone()

                if conv_row:
                    conversation_id = conv_row.id
                else:
                    # Create new conversation
                    new_conv = await db.execute(
                        text("""
                            INSERT INTO conversations (participant_ids)
                            VALUES (ARRAY[:uid1, :uid2]::INTEGER[])
                            RETURNING id
                        """),
                        {"uid1": user_id, "uid2": target_user_id},
                    )
                    conversation_id = new_conv.scalar_one()

                # Insert message
                msg_result = await db.execute(
                    text("""
                        INSERT INTO messages (conversation_id, sender_id, content)
                        VALUES (:conv_id, :sender_id, :content)
                        RETURNING id
                    """),
                    {
                        "conv_id": conversation_id,
                        "sender_id": user_id,
                        "content": request.message,
                    },
                )
                message_id = msg_result.scalar_one()

                # Update last_message_at
                await db.execute(
                    text("UPDATE conversations SET last_message_at = now() WHERE id = :cid"),
                    {"cid": conversation_id},
                )

                sent_to.append(target_user_id)
                message_ids.append(message_id)

            except Exception as e:
                print(f"Error sending to user {target_user_id}: {e}")
                failed.append(target_user_id)

        # Audit event
        await db.execute(
            text("""
                INSERT INTO potluck_social_events (session_id, event_type, actor_id, payload_json)
                VALUES (:sid, 'ping_sent', :uid, :payload)
            """),
            {
                "sid": request.session_id,
                "uid": user_id,
                "payload": json.dumps({
                    "target_user_ids": target_user_ids,
                    "sent_to": sent_to,
                    "failed": failed,
                    "message_count": len(message_ids),
                }),
            },
        )
        await db.commit()

        return PotluckPingResponse(
            session_id=request.session_id,
            sent_to=sent_to,
            failed=failed,
            message_ids=message_ids,
        )
