import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.auth import get_current_user_id
from app.models.social import Report, TrustedReviewer
from app.schemas.moderation import ReportCreate, ReportResponse, TriageItem
from app.services.safety import queue_safety_event
from app.config import settings

router = APIRouter(tags=["moderation"])


@router.post("/reports", response_model=ReportResponse, status_code=201)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    report = Report(
        reporter_id=user_id,
        reported_user_id=data.reported_user_id,
        reported_recipe_id=data.reported_recipe_id,
        reported_comment_id=data.reported_comment_id,
        report_type=data.report_type,
        severity=data.severity,
        description=data.description,
        status="pending",
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    await db.commit()

    await _push_to_moderation_queue(report)
    await queue_safety_event("report", {
        "report_id": report.id,
        "reporter_id": user_id,
        "report_type": data.report_type,
        "severity": data.severity,
    })

    return ReportResponse.model_validate(report)


@router.get("/moderation/triage", response_model=TriageItem | None)
async def get_triage_item(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    reviewer = await db.get(TrustedReviewer, user_id)
    if not reviewer or reviewer.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Not a trusted reviewer")

    result = await db.execute(
        select(Report)
        .where(Report.status == "pending")
        .order_by(Report.created_at.asc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        return None

    return TriageItem.model_validate(report)


async def _push_to_moderation_queue(report: Report) -> None:
    if not settings.moderation_service_url:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.moderation_service_url}/moderation/reports",
                json={
                    "report_id": report.id,
                    "reporter_id": report.reporter_id,
                    "reported_user_id": report.reported_user_id,
                    "reported_recipe_id": report.reported_recipe_id,
                    "reported_comment_id": report.reported_comment_id,
                    "report_type": report.report_type,
                    "severity": report.severity,
                    "description": report.description,
                },
            )
    except httpx.RequestError:
        pass
