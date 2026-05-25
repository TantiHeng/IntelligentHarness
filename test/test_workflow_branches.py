import logging

import pytest

from src.exceptions import MarketingReviewRejectedError, MarketingSendFailedError
from src.logger import logger
from src.schemas.marketing import (
    Channel,
    CustomerInfo,
    MarketingContent,
    MarketingInput,
    MarketingWorkflowState,
    ProductInfo,
    ReviewResult,
    SendResult,
)
from src.workflows.marketing_workflow import MarketingWorkflow


class ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    @property
    def messages(self) -> list[str]:
        return [record.getMessage() for record in self.records]


class FakeGenerator:
    def __init__(self):
        self.generate_called = 0
        self.revise_called = 0

    def generate(self, marketing_input: MarketingInput) -> MarketingContent:
        self.generate_called += 1
        return MarketingContent(title="初始标题", body="初始正文", call_to_action="预约演示", risk_notes=[])

    def revise(self, marketing_input: MarketingInput, content: MarketingContent, review: ReviewResult) -> MarketingContent:
        self.revise_called += 1
        return MarketingContent(
            title="改写标题",
            body=f"根据审核建议改写: {';'.join(review.revision_suggestions)}",
            call_to_action="预约演示",
            risk_notes=[],
        )


class SequenceReviewer:
    def __init__(self, results: list[ReviewResult]):
        self.results = results
        self.index = 0

    def review(self, content: MarketingContent) -> ReviewResult:
        if self.index >= len(self.results):
            return self.results[-1]
        result = self.results[self.index]
        self.index += 1
        return result


class FakeSender:
    def __init__(self, result: SendResult):
        self.result = result
        self.called = 0

    def send(self, marketing_input: MarketingInput, content: MarketingContent) -> SendResult:
        self.called += 1
        return self.result


class FakeRecorder:
    def __init__(self):
        self.states: list[MarketingWorkflowState] = []

    def record(self, state: MarketingWorkflowState) -> str:
        self.states.append(state)
        return f"record-{len(self.states)}"


def build_state() -> MarketingWorkflowState:
    return MarketingWorkflowState(
        input=MarketingInput(
            product=ProductInfo(
                name="智能营销助手",
                selling_points=["自动生成营销文案"],
                price="按量计费",
                target_audience="中小企业销售团队",
            ),
            customer=CustomerInfo(
                name="某教育 SaaS 公司",
                segment="教育行业",
                pain_points=["销售跟进效率低"],
                contact="customer@example.com",
            ),
            channel=Channel.EMAIL,
            tone="专业、克制",
        )
    )


def build_workflow(
    reviewer: SequenceReviewer,
    sender: FakeSender,
    recorder: FakeRecorder,
    generator: FakeGenerator | None = None,
) -> MarketingWorkflow:
    return MarketingWorkflow(
        generator=generator or FakeGenerator(),
        reviewer=reviewer,
        sender=sender,
        recorder=recorder,
    )


def approved_review() -> ReviewResult:
    return ReviewResult(approved=True, score=90, reasons=["通过"], revision_suggestions=[])


def rejected_review() -> ReviewResult:
    return ReviewResult(approved=False, score=40, reasons=["命中禁用表达"], revision_suggestions=["删除绝对化表达"])


def test_workflow_state_generates_run_id_and_thread_id():
    state = build_state()

    assert state.run_id
    assert state.thread_id
    assert state.run_id != state.thread_id


def test_workflow_success_path_preserves_run_id_thread_id_and_records_result():
    recorder = FakeRecorder()
    sender = FakeSender(SendResult(success=True, provider_message_id="mock-id"))
    reviewer = SequenceReviewer([approved_review()])
    workflow = build_workflow(reviewer=reviewer, sender=sender, recorder=recorder)
    state = build_state()

    result = workflow.invoke(state)

    assert result.run_id == state.run_id
    assert result.thread_id == state.thread_id
    assert result.content is not None
    assert result.review is not None
    assert result.review.approved is True
    assert result.send_result is not None
    assert result.send_result.success is True
    assert result.record_id == "record-1"
    assert sender.called == 1
    assert len(recorder.states) == 1
    assert recorder.states[0].run_id == state.run_id
    assert recorder.states[0].thread_id == state.thread_id
    assert recorder.states[0].send_result is not None
    assert recorder.states[0].send_result.success is True


def test_workflow_revise_path_uses_review_suggestions_then_succeeds():
    generator = FakeGenerator()
    recorder = FakeRecorder()
    sender = FakeSender(SendResult(success=True, provider_message_id="mock-id"))
    reviewer = SequenceReviewer([rejected_review(), approved_review()])
    workflow = build_workflow(reviewer=reviewer, sender=sender, recorder=recorder, generator=generator)
    state = build_state()

    result = workflow.invoke(state)

    assert result.run_id == state.run_id
    assert result.thread_id == state.thread_id
    assert generator.generate_called == 1
    assert generator.revise_called == 1
    assert result.retry_count == 1
    assert result.content is not None
    assert "删除绝对化表达" in result.content.body
    assert result.review is not None
    assert result.review.approved is True
    assert result.record_id == "record-1"


def test_workflow_reject_path_records_then_raises():
    recorder = FakeRecorder()
    sender = FakeSender(SendResult(success=True, provider_message_id="mock-id"))
    reviewer = SequenceReviewer([rejected_review(), rejected_review(), rejected_review()])
    workflow = build_workflow(reviewer=reviewer, sender=sender, recorder=recorder)
    state = build_state()

    with pytest.raises(MarketingReviewRejectedError):
        workflow.invoke(state)

    assert len(recorder.states) == 1
    assert recorder.states[0].run_id == state.run_id
    assert recorder.states[0].thread_id == state.thread_id
    assert recorder.states[0].review is not None
    assert recorder.states[0].review.approved is False


def test_workflow_send_failed_path_records_log_and_raises():
    handler = ListHandler()
    logger.addHandler(handler)

    recorder = FakeRecorder()
    sender = FakeSender(SendResult(success=False, error="mock provider failed"))
    reviewer = SequenceReviewer([approved_review()])
    workflow = build_workflow(reviewer=reviewer, sender=sender, recorder=recorder)
    state = build_state()

    try:
        with pytest.raises(MarketingSendFailedError):
            workflow.invoke(state)

        assert any("mock 发送失败路径触发" in message for message in handler.messages)
        assert len(recorder.states) == 1
        assert recorder.states[0].run_id == state.run_id
        assert recorder.states[0].thread_id == state.thread_id
        assert recorder.states[0].send_result is not None
        assert recorder.states[0].send_result.success is False
        assert recorder.states[0].send_result.error == "mock provider failed"
    finally:
        logger.removeHandler(handler)
