"""扩展协议：约束宿主可注入的能力边界，不提供特定业务系统实现。"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from intelligent_harness.events import BusinessEvent
    from intelligent_harness.models import HarnessWorkflowState, ReviewResult


class EnhancementStage(str, Enum):
    INFERENCE = "inference"
    REVIEW = "review"


class Inference(Protocol):
    def infer(self, input_data: dict[str, Any]) -> dict[str, Any]: ...

    def retry_inference(
        self,
        input_data: dict[str, Any],
        output: dict[str, Any],
        review: ReviewResult,
    ) -> dict[str, Any]: ...


class Reviewer(Protocol):
    def review(self, output: dict[str, Any]) -> ReviewResult: ...


class AuditRepository(Protocol):
    def save_run(self, state: HarnessWorkflowState) -> str: ...

    def save_event(self, event: BusinessEvent) -> str: ...


class ContextEnhancer(Protocol):
    def enhance(
        self,
        *,
        scenario: str,
        stage: EnhancementStage,
        input_data: Any = None,
        output: Any = None,
    ) -> dict[str, Any]: ...


class PrivacyProcessor(Protocol):
    def before_model(self, value: Any, *, scenario: str, stage: str) -> Any: ...

    def before_event_store(self, event: BusinessEvent) -> BusinessEvent: ...


class AlertSink(Protocol):
    def emit(self, event: BusinessEvent) -> None: ...


class NoOpContextEnhancer:
    def enhance(
        self,
        *,
        scenario: str,
        stage: EnhancementStage,
        input_data: Any = None,
        output: Any = None,
    ) -> dict[str, Any]:
        return {}


class NoOpPrivacyProcessor:
    def before_model(self, value: Any, *, scenario: str, stage: str) -> Any:
        return value

    def before_event_store(self, event: BusinessEvent) -> BusinessEvent:
        return event


class NullAlertSink:
    def emit(self, event: BusinessEvent) -> None:
        return None
