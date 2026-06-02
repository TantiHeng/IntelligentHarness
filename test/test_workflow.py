"""核心控制事务测试。

验证审核通过时返回 approved 响应并保存审计记录。
验证手写输出配合离线审核替身会触发重复审核、有限次重新推理、九次拦截事件和最终拒绝事件。
测试不调用真实模型，也不执行宿主程序的真实副作用。
"""

from intelligent_harness.adapters.repository import SQLiteAuditRepository
from intelligent_harness.cli.fault_injection import InjectedOutputInference
from intelligent_harness.errors import NonRetryableInferenceError
from intelligent_harness.events import BusinessEventService, BusinessEventType
from intelligent_harness.models import (
    HarnessDecision,
    HarnessWorkflowState,
    ReviewAction,
    ReviewResult,
)
from intelligent_harness.scenarios import ScenarioRegistry
from intelligent_harness.workflow import HarnessWorkflow


class ApproveReviewer:
    def review(self, output):
        return ReviewResult(approved=True, score=90, reasons=["通过"])


class FailingReviewer:
    def review(self, output):
        raise RuntimeError("review service unavailable")


class RejectReviewer:
    def review(self, output):
        return ReviewResult(approved=False, score=40, reasons=["离线审核替身拒绝"])


class DirectRejectReviewer:
    def review(self, output):
        return ReviewResult(
            approved=False,
            score=90,
            reasons=["高风险语义直接拒绝"],
            action=ReviewAction.REJECT,
        )


class ReviewAgainReviewer:
    def review(self, output):
        return ReviewResult(
            approved=False,
            score=70,
            reasons=["中风险语义再次审核"],
            action=ReviewAction.REVIEW_AGAIN,
        )


class FailingInference:
    def __init__(self, errors):
        self.errors = iter(errors)
        self.attempts = 0

    def infer(self, input_data):
        self.attempts += 1
        error = next(self.errors)
        if error is not None:
            raise error
        return {"title": "标题", "body": "正文", "call_to_action": "联系"}

    def retry_inference(self, input_data, output, review):
        return self.infer(input_data)


def state():
    return HarnessWorkflowState(
        scenario="marketing_copy", input={"product": {"name": "p"}, "customer": {"name": "c"}}
    )


def test_workflow_returns_approved_response(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "标题", "body": "正文", "call_to_action": "联系"}, scenario
    )
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(inference, ApproveReviewer(), repo, BusinessEventService(repo))

    response = workflow.execute(state())

    assert response.decision == HarnessDecision.APPROVED
    assert response.approved is True
    assert response.record_id


def test_handwritten_fault_is_rejected_and_logged(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "行业第一", "body": "100%保证稳赚", "call_to_action": "购买"}, scenario
    )
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    reviewer = RejectReviewer()
    workflow = HarnessWorkflow(inference, reviewer, repo, BusinessEventService(repo))
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.REJECTED
    assert response.approved is False
    assert inference.infer_called == 1
    assert inference.retry_inference_called == 2
    assert [x["event_type"] for x in events].count(BusinessEventType.REVIEW_REJECTED.value) == 9
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_REJECTED.value) == 1


def test_minimum_attempt_policy_rejects_after_one_inference_and_one_review(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "行业第一", "body": "正文", "call_to_action": "购买"}, scenario
    )
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    reviewer = RejectReviewer()
    workflow = HarnessWorkflow(
        inference,
        reviewer,
        repo,
        BusinessEventService(repo),
        max_review_attempts=1,
        max_inference_attempts=1,
    )
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.REJECTED
    assert inference.infer_called == 1
    assert inference.retry_inference_called == 0
    assert response.inference_attempt == 1
    assert response.review_attempt == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.REVIEW_REJECTED.value) == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_REJECTED.value) == 1


def test_direct_reject_action_does_not_repeat_review_or_inference(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "标题", "body": "正文", "call_to_action": "购买"}, scenario
    )
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(
        inference,
        DirectRejectReviewer(),
        repo,
        BusinessEventService(repo),
    )

    response = workflow.execute(state())

    assert response.decision == HarnessDecision.REJECTED
    assert response.inference_attempt == 1
    assert response.review_attempt == 1
    assert inference.retry_inference_called == 0


def test_review_again_action_stops_at_review_limit_without_regeneration(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "标题", "body": "正文", "call_to_action": "购买"}, scenario
    )
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(
        inference,
        ReviewAgainReviewer(),
        repo,
        BusinessEventService(repo),
        max_review_attempts=2,
        max_inference_attempts=3,
    )

    response = workflow.execute(state())

    assert response.decision == HarnessDecision.REJECTED
    assert response.inference_attempt == 1
    assert response.review_attempt == 2
    assert inference.retry_inference_called == 0


def test_retryable_inference_error_can_recover(tmp_path):
    inference = FailingInference([TimeoutError("upstream timeout"), None])
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(inference, ApproveReviewer(), repo, BusinessEventService(repo))
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.APPROVED
    assert inference.attempts == 2
    assert [x["event_type"] for x in events].count(BusinessEventType.INFERENCE_FAILED.value) == 1


def test_retryable_inference_error_exhaustion_returns_error(tmp_path):
    inference = FailingInference([TimeoutError("upstream timeout")] * 3)
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(inference, ApproveReviewer(), repo, BusinessEventService(repo))
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.ERROR
    assert response.approved is False
    assert inference.attempts == 3
    assert [x["event_type"] for x in events].count(BusinessEventType.INFERENCE_FAILED.value) == 3
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_ERROR.value) == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_REJECTED.value) == 0


def test_non_retryable_inference_error_returns_error_without_retry(tmp_path):
    inference = FailingInference([NonRetryableInferenceError("invalid model response")])
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(inference, ApproveReviewer(), repo, BusinessEventService(repo))
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.ERROR
    assert inference.attempts == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.INFERENCE_FAILED.value) == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_ERROR.value) == 1


def test_reviewer_failure_returns_error_instead_of_rejection(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "标题", "body": "正文", "call_to_action": "联系"}, scenario
    )
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(inference, FailingReviewer(), repo, BusinessEventService(repo))
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.ERROR
    assert [x["event_type"] for x in events].count(BusinessEventType.REVIEW_FAILED.value) == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_ERROR.value) == 1
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_REJECTED.value) == 0
