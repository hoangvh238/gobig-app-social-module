from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import aliased
from app.models.social import Comment, Report
from app.models.legacy_models import User
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse, CommentListResponse
from app.services.activity_service import ActivityService


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

        activity_service = ActivityService(self.db)
        await activity_service.create_activity(
            user_id=user_id,
            actor_id=user_id,
            action_type="comment",
            payload_json={
                "comment_id": comment.id,
                "recipe_id": data.recipe_id,
                "content": data.content[:100],
                "user_name": user.name if user else None
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
            user_avatar_id=user.avatar_id if user else None,
            reply_count=0,
        )

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
        comment.updated_at = func.now()
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
            user_avatar_id=user.avatar_id if user else None,
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
        limit: int = 20
    ) -> CommentListResponse:
        query = (
            select(Comment, User)
            .join(User, Comment.user_id == User.id)
            .where(
                and_(
                    Comment.recipe_id == recipe_id,
                    Comment.is_deleted == False,
                    Comment.parent_id == None
                )
            )
            .order_by(Comment.id.desc())
            .limit(limit + 1)
        )

        if cursor:
            query = query.where(Comment.id < cursor)

        result = await self.db.execute(query)
        rows = result.all()

        has_more = len(rows) > limit
        comments_data = rows[:limit]

        comments = []
        for comment, user in comments_data:
            reply_count = await self._get_reply_count(comment.id)
            comments.append(
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
                    user_avatar_id=user.avatar_id,
                    reply_count=reply_count,
                )
            )

        next_cursor = comments[-1].id if has_more and comments else None
        return CommentListResponse(comments=comments, next_cursor=next_cursor)

    async def list_replies(
        self,
        parent_id: int,
        cursor: int | None = None,
        limit: int = 20
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
                user_avatar_id=user.avatar_id,
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
