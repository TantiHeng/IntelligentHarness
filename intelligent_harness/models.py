"""领域模型：定义工作流状态、审核结果和宿主响应，不执行流程控制。"""

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ReviewResult(BaseModel):
    approved: bool
    score: int = Field(..., ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    revision_suggestions: list[str] = Field(default_factory=list)


class HarnessDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


class HarnessWorkflowState(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str = Field(default_factory=lambda: str(uuid4()))
    scenario: str
    input: Any
    output: Any | None = None
    review: ReviewResult | None = None
    decision: HarnessDecision | None = None
    reasons: list[str] = Field(default_factory=list)
    record_id: str | None = None
    inference_attempt: int = 0
    review_attempt: int = 0
    last_error: str | None = None
    errors: list[str] = Field(default_factory=list)


class HarnessResponse(BaseModel):
    run_id: str
    thread_id: str
    scenario: str
    decision: HarnessDecision
    approved: bool
    output: Any | None = None
    review: ReviewResult | None = None
    reasons: list[str] = Field(default_factory=list)
    inference_attempt: int = 0
    review_attempt: int = 0
    record_id: str | None = None
