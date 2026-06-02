"""控制事务：编排有界推理、重复审核和稳定拒绝，不执行宿主副作用动作。"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from intelligent_harness.adapters.logging import logger
from intelligent_harness.events import (
    BusinessEvent,
    BusinessEventService,
    BusinessEventType,
)
from intelligent_harness.models import (
    HarnessDecision,
    HarnessResponse,
    HarnessWorkflowState,
)
from intelligent_harness.ports import AuditRepository, Inference, Reviewer


class HarnessWorkflow:
    def __init__(
        self,
        inference: Inference,
        reviewer: Reviewer,
        repository: AuditRepository,
        events: BusinessEventService,
        max_review_attempts: int = 3,
        max_inference_attempts: int = 3,
    ) -> None:
        self.inference = inference
        self.reviewer = reviewer
        self.repository = repository
        self.events = events
        self.max_review_attempts = max_review_attempts
        self.max_inference_attempts = max_inference_attempts
        self.app = self._build_graph()

    def execute(self, state: HarnessWorkflowState) -> HarnessResponse:
        try:
            raw_result = self.app.invoke(
                state,
                config={"configurable": {"thread_id": state.thread_id}},
            )
            result = HarnessWorkflowState.model_validate(raw_result)
        except Exception as exc:
            logger.exception("Harness 执行异常: %s", exc)
            return self._error_response(state, exc)
        return self._response_from_state(result)

    def _infer(self, state: HarnessWorkflowState, *, retry: bool = False) -> dict[str, Any]:
        attempt = state.inference_attempt + 1
        try:
            output = self._run_inference(state, retry=retry)
        except Exception as exc:
            self._publish_event(
                state,
                severity=2,
                event_type=BusinessEventType.INFERENCE_FAILED,
                step="inference",
                inference_attempt=attempt,
                review_attempt=0,
                reasons=[str(exc)],
            )
            return {
                "output": None,
                "review": None,
                "inference_attempt": attempt,
                "review_attempt": 0,
                "last_error": str(exc),
                "errors": [*state.errors, str(exc)],
            }
        self._publish_event(
            state,
            severity=3,
            event_type=BusinessEventType.NODE_COMPLETED,
            step="inference",
            inference_attempt=attempt,
            review_attempt=0,
            content=output,
        )
        return {
            "output": output,
            "review": None,
            "inference_attempt": attempt,
            "review_attempt": 0,
            "last_error": None,
        }

    def _run_inference(
        self,
        state: HarnessWorkflowState,
        *,
        retry: bool,
    ) -> dict[str, Any]:
        if retry and state.output is not None and state.review is not None:
            return self.inference.retry_inference(state.input, state.output, state.review)
        return self.inference.infer(state.input)

    def _review(self, state: HarnessWorkflowState) -> dict[str, Any]:
        attempt = state.review_attempt + 1
        review = self.reviewer.review(state.output)
        self._publish_event(
            state,
            severity=3,
            event_type=BusinessEventType.NODE_COMPLETED,
            step="review",
            review_attempt=attempt,
            content=state.output,
            reasons=review.reasons,
        )
        if not review.approved:
            self._publish_event(
                state,
                severity=2,
                event_type=BusinessEventType.REVIEW_REJECTED,
                step="review",
                review_attempt=attempt,
                content=state.output,
                reasons=review.reasons,
            )
        return {"review": review, "review_attempt": attempt}

    def _finish(
        self,
        state: HarnessWorkflowState,
        decision: HarnessDecision,
    ) -> dict[str, Any]:
        reasons = (
            state.review.reasons
            if state.review
            else [state.last_error or "无审核结果"]
        )
        if decision == HarnessDecision.REJECTED:
            self._publish_event(
                state,
                severity=1,
                event_type=BusinessEventType.FINAL_REJECTED,
                step="reject",
                content=state.output,
                reasons=reasons,
            )
        saved_state = state.model_copy(update={"decision": decision, "reasons": reasons})
        return {
            "decision": decision,
            "reasons": reasons,
            "record_id": self.repository.save_run(saved_state),
        }

    def _publish_event(
        self,
        state: HarnessWorkflowState,
        *,
        severity: int,
        event_type: BusinessEventType,
        step: str,
        **updates: Any,
    ) -> None:
        self.events.publish(
            BusinessEvent(
                run_id=state.run_id,
                thread_id=state.thread_id,
                severity=severity,
                event_type=event_type,
                step=step,
                scenario=state.scenario,
                inference_attempt=updates.pop(
                    "inference_attempt",
                    state.inference_attempt,
                ),
                review_attempt=updates.pop("review_attempt", state.review_attempt),
                **updates,
            )
        )

    def _route_inference(self, state: HarnessWorkflowState) -> str:
        if state.output is not None:
            return "review"
        if state.inference_attempt < self.max_inference_attempts:
            return "retry"
        return "reject"

    def _route_review(self, state: HarnessWorkflowState) -> str:
        if state.review and state.review.approved:
            return "approve"
        if state.review_attempt < self.max_review_attempts:
            return "review"
        if state.inference_attempt < self.max_inference_attempts:
            return "retry"
        return "reject"

    def _build_graph(self):
        graph = StateGraph(HarnessWorkflowState)
        graph.add_node("infer", self._infer)
        graph.add_node("retry", lambda state: self._infer(state, retry=True))
        graph.add_node(
            "approve",
            lambda state: self._finish(state, HarnessDecision.APPROVED),
        )
        graph.add_node(
            "reject",
            lambda state: self._finish(state, HarnessDecision.REJECTED),
        )
        graph.add_node("review", self._review)
        graph.add_edge(START, "infer")
        graph.add_conditional_edges("infer", self._route_inference)
        graph.add_conditional_edges("retry", self._route_inference)
        graph.add_conditional_edges("review", self._route_review)
        graph.add_edge("approve", END)
        graph.add_edge("reject", END)
        return graph.compile()

    @staticmethod
    def _response_from_state(result: HarnessWorkflowState) -> HarnessResponse:
        decision = result.decision or HarnessDecision.ERROR
        return HarnessResponse(
            run_id=result.run_id,
            thread_id=result.thread_id,
            scenario=result.scenario,
            decision=decision,
            approved=decision == HarnessDecision.APPROVED,
            output=result.output,
            review=result.review,
            reasons=result.reasons,
            inference_attempt=result.inference_attempt,
            review_attempt=result.review_attempt,
            record_id=result.record_id,
        )

    @staticmethod
    def _error_response(
        state: HarnessWorkflowState,
        error: Exception,
    ) -> HarnessResponse:
        return HarnessResponse(
            run_id=state.run_id,
            thread_id=state.thread_id,
            scenario=state.scenario,
            decision=HarnessDecision.ERROR,
            approved=False,
            reasons=[str(error)],
        )
