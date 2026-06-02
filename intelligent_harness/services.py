"""推理与审核服务：执行场景相关模型调用和审核，不决定重试事务。"""

import json
from typing import Any, Protocol

from intelligent_harness.models import ReviewResult
from intelligent_harness.ports import (
    ContextEnhancer,
    EnhancementStage,
    NoOpContextEnhancer,
    NoOpPrivacyProcessor,
    PrivacyProcessor,
)
from intelligent_harness.scenarios import ScenarioDefinition


class TextModel(Protocol):
    def invoke(self, prompt: str) -> str: ...


def extract_json_object(text: str) -> dict[str, Any]:
    value = json.loads(text.strip())
    if not isinstance(value, dict):
        raise ValueError("模型输出不是 JSON object。")
    return value


class InferenceService:
    def __init__(
        self,
        model: TextModel,
        scenario: ScenarioDefinition,
        context: ContextEnhancer | None = None,
        privacy: PrivacyProcessor | None = None,
    ) -> None:
        self.model = model
        self.scenario = scenario
        self.context = context or NoOpContextEnhancer()
        self.privacy = privacy or NoOpPrivacyProcessor()

    def infer(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return self._invoke("inference", input_data)

    def retry_inference(
        self,
        input_data: dict[str, Any],
        output: dict[str, Any],
        review: ReviewResult,
    ) -> dict[str, Any]:
        return self._invoke("retry_inference", input_data, output, review)

    def _invoke(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        output: dict[str, Any] | None = None,
        review: ReviewResult | None = None,
    ) -> dict[str, Any]:
        protected_input = self.privacy.before_model(
            input_data,
            scenario=self.scenario.name,
            stage="inference",
        )
        values = {"input_json": json.dumps(protected_input, ensure_ascii=False)}
        if output is not None:
            protected_output = self.privacy.before_model(
                output,
                scenario=self.scenario.name,
                stage="inference",
            )
            values["output_json"] = json.dumps(protected_output, ensure_ascii=False)
        if review is not None:
            values["review_json"] = review.model_dump_json(ensure_ascii=False)

        prompt = self.scenario.render_prompt(prompt_name, **values)
        prompt += self._render_context(input_data=input_data, output=output)
        return self.scenario.validate(
            "output",
            extract_json_object(self.model.invoke(prompt)),
        )

    def _render_context(
        self,
        *,
        input_data: dict[str, Any],
        output: dict[str, Any] | None,
    ) -> str:
        extra = self.context.enhance(
            scenario=self.scenario.name,
            stage=EnhancementStage.INFERENCE,
            input_data=input_data,
            output=output,
        )
        return f"\n增强上下文：{json.dumps(extra, ensure_ascii=False)}" if extra else ""


class ReviewService:
    FORBIDDEN_MARKETING_PHRASES = [
        "100%保证",
        "稳赚",
        "行业第一",
        "绝对有效",
        "永久解决",
    ]

    def __init__(
        self,
        model: TextModel,
        scenario: ScenarioDefinition,
        context: ContextEnhancer | None = None,
        privacy: PrivacyProcessor | None = None,
    ) -> None:
        self.model = model
        self.scenario = scenario
        self.context = context or NoOpContextEnhancer()
        self.privacy = privacy or NoOpPrivacyProcessor()

    def review(self, output: dict[str, Any]) -> ReviewResult:
        deterministic_result = self._review_marketing_phrases(output)
        if deterministic_result is not None:
            return deterministic_result
        return self._review_with_model(output)

    def _review_marketing_phrases(
        self,
        output: dict[str, Any],
    ) -> ReviewResult | None:
        if self.scenario.reviewer != "marketing_copy":
            return None
        text = "\n".join(str(output.get(key, "")) for key in ("title", "body", "call_to_action"))
        hits = [phrase for phrase in self.FORBIDDEN_MARKETING_PHRASES if phrase in text]
        if not hits:
            return None
        return ReviewResult(
            approved=False,
            score=40,
            reasons=[f"命中禁用表达: {phrase}" for phrase in hits],
            revision_suggestions=["删除风险表达"],
        )

    def _review_with_model(self, output: dict[str, Any]) -> ReviewResult:
        protected_output = self.privacy.before_model(
            output,
            scenario=self.scenario.name,
            stage="review",
        )
        prompt = self.scenario.render_prompt(
            "review",
            output_json=json.dumps(protected_output, ensure_ascii=False),
        )
        extra = self.context.enhance(
            scenario=self.scenario.name,
            stage=EnhancementStage.REVIEW,
            output=output,
        )
        if extra:
            prompt += f"\n增强上下文：{json.dumps(extra, ensure_ascii=False)}"
        return ReviewResult.model_validate(extract_json_object(self.model.invoke(prompt)))
