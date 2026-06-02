"""业务事件：定义事件结构与发布策略，不负责实现具体告警渠道。"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from intelligent_harness.ports import AlertSink, AuditRepository, PrivacyProcessor


class BusinessEventType(str, Enum):
    NODE_COMPLETED = "node_completed"
    REVIEW_REJECTED = "review_rejected"
    INFERENCE_FAILED = "inference_failed"
    FINAL_REJECTED = "final_rejected"


class BusinessEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    thread_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: int = Field(..., ge=1, le=3)
    event_type: BusinessEventType
    step: str
    scenario: str
    inference_attempt: int = Field(..., ge=0)
    review_attempt: int | None = Field(default=None, ge=0)
    content: Any = None
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BusinessEventService:
    def __init__(
        self,
        repository: AuditRepository,
        alert_threshold: int = 2,
        sink: AlertSink | None = None,
        privacy: PrivacyProcessor | None = None,
    ) -> None:
        from intelligent_harness.ports import NoOpPrivacyProcessor, NullAlertSink

        self.repository = repository
        self.alert_threshold = alert_threshold
        self.sink = sink or NullAlertSink()
        self.privacy = privacy or NoOpPrivacyProcessor()

    def publish(self, event: BusinessEvent) -> None:
        from intelligent_harness.adapters.logging import logger

        protected_event = self.privacy.before_event_store(event)
        self.repository.save_event(protected_event)
        if protected_event.severity > self.alert_threshold:
            return
        try:
            self.sink.emit(protected_event)
        except Exception as exc:
            logger.exception(
                "业务事件 sink 执行失败: event_id=%s error=%s",
                protected_event.event_id,
                exc,
            )
