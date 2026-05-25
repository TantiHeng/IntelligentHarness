from enum import Enum
from typing import Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WECHAT = "wechat"


class ProductInfo(BaseModel):
    name: str = Field(..., min_length=1)
    selling_points: List[str] = Field(default_factory=list)
    price: Optional[str] = None
    target_audience: Optional[str] = None


class CustomerInfo(BaseModel):
    name: str = Field(..., min_length=1)
    segment: Optional[str] = None
    pain_points: List[str] = Field(default_factory=list)
    contact: Optional[str] = None


class MarketingInput(BaseModel):
    product: ProductInfo
    customer: CustomerInfo
    channel: Channel = Channel.EMAIL
    tone: str = "专业、克制、有转化导向"


class MarketingContent(BaseModel):
    title: str
    body: str
    call_to_action: str
    risk_notes: List[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    approved: bool
    score: int = Field(..., ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    revision_suggestions: List[str] = Field(default_factory=list)


class SendResult(BaseModel):
    success: bool
    provider_message_id: Optional[str] = None
    error: Optional[str] = None


class MarketingWorkflowState(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str = Field(default_factory=lambda: str(uuid4()))

    input: MarketingInput
    content: Optional[MarketingContent] = None
    review: Optional[ReviewResult] = None
    send_result: Optional[SendResult] = None
    record_id: Optional[str] = None
    retry_count: int = 0
    errors: List[str] = Field(default_factory=list)
