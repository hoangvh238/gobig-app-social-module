from pydantic import BaseModel, model_validator
from datetime import datetime
from typing import Literal


class ReportCreate(BaseModel):
    reported_user_id: int | None = None
    reported_recipe_id: int | None = None
    reported_comment_id: int | None = None
    report_type: str
    severity: Literal["low", "medium", "high"] = "medium"
    description: str | None = None

    @model_validator(mode="after")
    def require_target(self) -> "ReportCreate":
        if not any([self.reported_user_id, self.reported_recipe_id, self.reported_comment_id]):
            raise ValueError("At least one of reported_user_id, reported_recipe_id, reported_comment_id is required")
        return self


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int | None
    reported_recipe_id: int | None
    reported_comment_id: int | None
    report_type: str
    severity: str
    description: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TriageItem(BaseModel):
    id: int
    reporter_id: int
    reported_user_id: int | None
    reported_recipe_id: int | None
    reported_comment_id: int | None
    report_type: str
    severity: str
    description: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
