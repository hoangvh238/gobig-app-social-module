from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.social import Comment, Report
from app.models.legacy_models import User, NLPEnrichment
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse, CommentListResponse
from app.services.activity_service import ActivityService
from app.config import settings


class CommentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_comment(self, user_id: int, data: CommentCreate) -> CommentResponse:
        comment = Comment(
            user_id=user_id,
            recipe_id=data.recipe_id,
            parent_id=data.parent_id,
            content=data.content,
        )
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)

        user = await self.db.get(User, user_id)

        swap_hint = await self._get_swap_hint(data.recipe_id)

        activity_service = ActivityService(self.db)
        await activity_service.create_activity(
            user_id=user_id,
            actor_id=user_id,
            action_type="comment",
            payload_json={
                "comment_id": comment.id,
                "recipe_id": data.recipe_id,
                "content": data.content[:100],
                "user_name": user.name if user else None,
            }
        )

        return CommentResponse(
            id=comment.id,
            user_id=comment.user_id,
            recipe_id=comment.recipe_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user_name=user.name if user else None,
            user_avatar_url=user.avatar_url if user else None,
            reply_count=0,
            swap_hint=swap_hint,
        )

    async def _get_swap_hint(self, recipe_id: int) -> str | None:
        result = await self.db.execute(
            select(NLPEnrichment.swap_hint).where(NLPEnrichment.recipe_id == recipe_id)
        )
        return result.scalar_one_or_none()

    async def update_comment(self, comment_id: int, user_id: int, data: CommentUpdate) -> CommentResponse | None:
        result = await self.db.execute(
            select(Comment).where(
                and_(
                    Comment.id == comment_id,
                    Comment.user_id == user_id,
                    Comment.is_deleted == False
                )
            )
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return None

        comment.content = data.content
        comment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        user = await self.db.get(User, user_id)
        reply_count = await self._get_reply_count(comment_id)

        return CommentResponse(
            id=comment.id,
            user_id=comment.user_id,
            recipe_id=comment.recipe_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            user_name=user.name if user else None,
            user_avatar_url=user.avatar_url if user else None,
            reply_count=reply_count,
        )

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(Comment).where(
                and_(
                    Comment.id == comment_id,
                    Comment.user_id == user_id,
                    Comment.is_deleted == False
                )
            )
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return False

        comment.is_deleted = True
        await self.db.flush()
        return True

    async def list_comments(
        self,
        recipe_id: int,
        cursor: int | None = None,
        limit: int = 20,
        blocked_ids: set[int] | None = None,
    ) -> CommentListResponse:
        query = (
            select(Comment, User)
            .join(User, Comment.user_id == User.id)
            .where(
                and_(
                    Comment.recipe_id == recipe_id,
                    Comment.is_deleted == False,
                    Comment.parent_id.is_(None),
                )
            )
            .order_by(Comment.id.desc())
            .limit(limit + 1)
        )
        if cursor:
            query = query.where(Comment.id < cursor)
        if blocked_ids:
            query = query.where(Comment.user_id.not_in(blocked_ids))

        result = await self.db.execute(query)
        rows = result.all()

        has_more = len(rows) > limit
        comments_data = rows[:limit]

        if not comments_data:
            return CommentListResponse(comments=[], next_cursor=None)

        comment_ids = [c.id for c, _ in comments_data]
        reply_rows = await self.db.execute(
            select(Comment.parent_id, func.count(Comment.id).label("cnt"))
            .where(and_(Comment.parent_id.in_(comment_ids), Comment.is_deleted == False))
            .group_by(Comment.parent_id)
        )
        reply_count_map: dict[int, int] = {row.parent_id: row.cnt for row in reply_rows}

        comments = [
            CommentResponse(
                id=comment.id,
                user_id=comment.user_id,
                recipe_id=comment.recipe_id,
                parent_id=comment.parent_id,
                content=comment.content,
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                user_name=user.name,
                user_avatar_url=user.avatar_url,
                reply_count=reply_count_map.get(comment.id, 0),
            )
            for comment, user in comments_data
        ]

        next_cursor = comments[-1].id if has_more else None
        return CommentListResponse(comments=comments, next_cursor=next_cursor)

    async def list_replies(
        self,
        parent_id: int,
        cursor: int | None = None,
        limit: int = 20,
        blocked_ids: set[int] | None = None,
    ) -> CommentListResponse:
        query = (
            select(Comment, User)
            .join(User, Comment.user_id == User.id)
            .where(
                and_(
                    Comment.parent_id == parent_id,
                    Comment.is_deleted == False
                )
            )
            .order_by(Comment.id.asc())
            .limit(limit + 1)
        )

        if cursor:
            query = query.where(Comment.id > cursor)
        if blocked_ids:
            query = query.where(Comment.user_id.not_in(blocked_ids))

        result = await self.db.execute(query)
        rows = result.all()

        has_more = len(rows) > limit
        comments_data = rows[:limit]

        comments = [
            CommentResponse(
                id=comment.id,
                user_id=comment.user_id,
                recipe_id=comment.recipe_id,
                parent_id=comment.parent_id,
                content=comment.content,
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                user_name=user.name,
                user_avatar_url=user.avatar_url,
                reply_count=0,
            )
            for comment, user in comments_data
        ]

        next_cursor = comments[-1].id if has_more and comments else None
        return CommentListResponse(comments=comments, next_cursor=next_cursor)

    async def flag_comment(self, comment_id: int, reporter_id: int, reason: str) -> bool:
        result = await self.db.execute(
            select(Comment).where(Comment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return False

        report = Report(
            reporter_id=reporter_id,
            reported_comment_id=comment_id,
            report_type="inappropriate_content",
            severity="medium",
            description=reason,
            status="pending",
        )
        self.db.add(report)
        await self.db.flush()

        # Push to Tuan's moderation queue (T2-M3). Non-fatal if service is not yet live.
        if settings.moderation_service_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"{settings.moderation_service_url}/moderation/reports",
                        json={
                            "comment_id": comment_id,
                            "reporter_id": reporter_id,
                            "recipe_id": comment.recipe_id,
                            "reason": reason,
                            "severity": "medium",
                        }
                    )
            except httpx.RequestError:
                pass  # Local report already persisted; queue delivery retried by Tuan's side

        return True

    async def _get_reply_count(self, parent_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Comment.id)).where(
                and_(
                    Comment.parent_id == parent_id,
                    Comment.is_deleted == False
                )
            )
        )
        return result.scalar() or 0
