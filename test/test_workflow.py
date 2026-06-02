"""核心控制事务测试。

验证审核通过时返回 approved 响应并保存审计记录。
验证手写不合规输出会触发重复审核、有限次重新推理、九次拦截事件和最终拒绝事件。
使用本地故障注入替身，不调用真实模型，也不执行宿主程序的真实副作用。
"""

from intelligent_harness.adapters.repository import SQLiteAuditRepository
from intelligent_harness.cli.fault_injection import InjectedOutputInference
from intelligent_harness.events import BusinessEventService, BusinessEventType
from intelligent_harness.models import HarnessDecision, HarnessWorkflowState, ReviewResult
from intelligent_harness.scenarios import ScenarioRegistry
from intelligent_harness.services import ReviewService
from intelligent_harness.workflow import HarnessWorkflow


class ApproveReviewer:
    def review(self, output):
        return ReviewResult(approved=True, score=90, reasons=["通过"])


def state():
    return HarnessWorkflowState(scenario="marketing_copy", input={"product": {"name": "p"}, "customer": {"name": "c"}})


def test_workflow_returns_approved_response(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference({"title": "标题", "body": "正文", "call_to_action": "联系"}, scenario)
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    workflow = HarnessWorkflow(inference, ApproveReviewer(), repo, BusinessEventService(repo))

    response = workflow.execute(state())

    assert response.decision == HarnessDecision.APPROVED
    assert response.approved is True
    assert response.record_id


def test_handwritten_fault_is_rejected_and_logged(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference({"title": "行业第一", "body": "100%保证稳赚", "call_to_action": "购买"}, scenario)
    repo = SQLiteAuditRepository(tmp_path / "audit.db")
    reviewer = ReviewService(object(), scenario)
    workflow = HarnessWorkflow(inference, reviewer, repo, BusinessEventService(repo))
    initial = state()

    response = workflow.execute(initial)
    events = repo.list_events(initial.run_id)

    assert response.decision == HarnessDecision.REJECTED
    assert response.approved is False
    assert [x["event_type"] for x in events].count(BusinessEventType.REVIEW_REJECTED.value) == 9
    assert [x["event_type"] for x in events].count(BusinessEventType.FINAL_REJECTED.value) == 1
