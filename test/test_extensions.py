"""可选扩展接口测试。

验证 ContextEnhancer 可以向推理 Prompt 注入知识上下文，
并验证 PrivacyProcessor 可以在模型调用前和业务事件落库前处理敏感内容。
不验证具体 RAG、知识图谱、脱敏算法或外部告警供应商实现。
"""

import json

from intelligent_harness.adapters.repository import SQLiteAuditRepository
from intelligent_harness.events import BusinessEvent, BusinessEventService, BusinessEventType
from intelligent_harness.scenarios import ScenarioRegistry
from intelligent_harness.services import InferenceService


class LLM:
    def __init__(self):
        self.prompt = ""

    def invoke(self, prompt):
        self.prompt = prompt
        return '{"title":"标题","body":"正文","call_to_action":"联系"}'


class Enhancer:
    def enhance(self, **kwargs):
        return {"evidence": ["知识图谱关系"]}


class Privacy:
    def before_model(self, value, **kwargs):
        return {"masked": True}

    def before_event_store(self, event):
        return event.model_copy(update={"content": {"masked": True}})


def test_optional_context_and_privacy_extensions_are_called(tmp_path):
    llm = LLM()
    scenario = ScenarioRegistry().get("marketing_copy")
    InferenceService(llm, scenario, Enhancer(), Privacy()).infer({"secret": "raw"})
    assert '"masked": true' in llm.prompt
    assert "知识图谱关系" in llm.prompt

    repo = SQLiteAuditRepository(tmp_path / "events.db")
    events = BusinessEventService(repo, privacy=Privacy())
    events.publish(
        BusinessEvent(
            run_id="r",
            thread_id="t",
            severity=1,
            event_type=BusinessEventType.FINAL_REJECTED,
            step="reject",
            scenario="marketing_copy",
            inference_attempt=1,
            content={"secret": "raw"},
        )
    )
    assert json.loads(repo.list_events("r")[0]["content_json"]) == {"masked": True}
