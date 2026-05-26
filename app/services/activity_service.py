from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.social import Activity
from app.schemas.activity import ActivityResponse, ActivityListResponse


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_activity(
        self,
        user_id: int,
        actor_id: int,
        action_type: str,
        payload_json: dict
    ) -> None:
        activity = Activity(
            user_id=user_id,
            actor_id=actor_id,
            action_type=action_type,
            payload_json=payload_json
        )
        self.db.add(activity)
        await self.db.flush()

    async def get_user_activities(
        self,
        user_id: int,
        cursor: int | None = None,
        limit: int = 20
    ) -> ActivityListResponse:
        query = (
            select(Activity)
            .where(Activity.user_id == user_id)
            .order_by(Activity.id.desc())
            .limit(limit + 1)
        )

        if cursor:
            query = query.where(Activity.id < cursor)

        result = await self.db.execute(query)
        activities_data = result.scalars().all()

        has_more = len(activities_data) > limit
        activities = activities_data[:limit]

        activities_response = [
            ActivityResponse(
                id=activity.id,
                user_id=activity.user_id,
                actor_id=activity.actor_id,
                action_type=activity.action_type,
                payload_json=activity.payload_json,
                created_at=activity.created_at
            )
            for activity in activities
        ]

        next_cursor = activities_response[-1].id if has_more and activities_response else None
        return ActivityListResponse(activities=activities_response, next_cursor=next_cursor)
