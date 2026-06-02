"""依赖装配：为宿主程序和 CLI 组合默认实现，不承载领域判断。"""

from intelligent_harness.adapters.llm import LLMClient
from intelligent_harness.adapters.repository import SQLiteAuditRepository
from intelligent_harness.adapters.settings import RuntimeConfig, load_runtime_config
from intelligent_harness.events import BusinessEventService
from intelligent_harness.ports import (
    AlertSink,
    ContextEnhancer,
    Inference,
    PrivacyProcessor,
    Reviewer,
)
from intelligent_harness.scenarios import ScenarioRegistry
from intelligent_harness.services import InferenceService, ReviewService, TextModel
from intelligent_harness.workflow import HarnessWorkflow


def build_harness(
    *,
    scenario_name: str | None = None,
    config: RuntimeConfig | None = None,
    model: TextModel | None = None,
    inference: Inference | None = None,
    reviewer: Reviewer | None = None,
    context: ContextEnhancer | None = None,
    privacy: PrivacyProcessor | None = None,
    sink: AlertSink | None = None,
) -> HarnessWorkflow:
    runtime = config or load_runtime_config()
    scenario = ScenarioRegistry().get(scenario_name or runtime.settings.default_scenario)
    repository = SQLiteAuditRepository(runtime.db_path)
    resolved_model = model
    if resolved_model is None and (inference is None or reviewer is None):
        resolved_model = LLMClient(runtime)
    inference_service = inference or InferenceService(
        _require_model(resolved_model),
        scenario,
        context,
        privacy,
    )
    review_service = reviewer or ReviewService(
        _require_model(resolved_model),
        scenario,
        context,
        privacy,
    )
    event_service = BusinessEventService(
        repository,
        runtime.settings.business_events.alert_severity_threshold,
        sink,
        privacy,
    )
    return HarnessWorkflow(
        inference_service,
        review_service,
        repository,
        event_service,
        runtime.settings.policy.max_review_attempts,
        runtime.settings.policy.max_inference_attempts,
    )


def _require_model(model: TextModel | None) -> TextModel:
    if model is None:
        raise RuntimeError("缺少模型实现。")
    return model
