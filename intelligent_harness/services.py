"""推理与审核服务：执行场景相关模型调用和审核，不决定重试事务。"""

import json
import math
from typing import Any, Protocol

from intelligent_harness.adapters.settings import SemanticReviewSettings
from intelligent_harness.models import ReviewAction, ReviewResult
from intelligent_harness.ports import (
    ContextEnhancer,
    EmbeddingModel,
    EnhancementStage,
    NoOpContextEnhancer,
    NoOpPrivacyProcessor,
    PrivacyProcessor,
)
from intelligent_harness.scenarios import ScenarioDefinition


class TextModel(Protocol):
    """Minimal text completion boundary required by inference and review services."""

    def invoke(self, prompt: str) -> str: ...


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a model response and reject JSON values that are not objects."""
    value = json.loads(text.strip())
    if not isinstance(value, dict):
        raise ValueError("模型输出不是 JSON object。")
    return value


class InferenceService:
    """Render scenario prompts, call a text model, and validate generated output."""

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
        """Generate the first candidate output for a host input."""
        return self._invoke("inference", input_data)

    def retry_inference(
        self,
        input_data: dict[str, Any],
        output: dict[str, Any],
        review: ReviewResult,
    ) -> dict[str, Any]:
        """Generate a revised candidate using the previous output and review."""
        return self._invoke("retry_inference", input_data, output, review)

    def _invoke(
        self,
        prompt_name: str,
        input_data: dict[str, Any],
        output: dict[str, Any] | None = None,
        review: ReviewResult | None = None,
    ) -> dict[str, Any]:
        """Apply privacy hooks, render one prompt, invoke the model, and validate JSON."""
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
        """Append optional host-provided context without changing scenario resources."""
        extra = self.context.enhance(
            scenario=self.scenario.name,
            stage=EnhancementStage.INFERENCE,
            input_data=input_data,
            output=output,
        )
        return f"\n增强上下文：{json.dumps(extra, ensure_ascii=False)}" if extra else ""


class ReviewService:
    """Render scenario review prompts and normalize model review results."""

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
        """Ask the review model to assess one schema-valid candidate."""
        return self._review_with_model(output)

    def _review_with_model(self, output: dict[str, Any]) -> ReviewResult:
        """Ask the model for a review and validate it as `ReviewResult`."""
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


class SemanticLayeredReviewer:
    """Route semantic similarity bands to approve, LLM review, or direct rejection."""

    def __init__(
        self,
        embeddings: EmbeddingModel,
        scenario: ScenarioDefinition,
        fallback: ReviewService,
        settings: SemanticReviewSettings,
    ) -> None:
        self.embeddings = embeddings
        self.scenario = scenario
        self.fallback = fallback
        self.settings = settings
        self.samples = self._load_samples()
        self.sample_vectors = self._embed_samples()

    def review(self, output: dict[str, Any]) -> ReviewResult:
        """Apply configured similarity bands and use LLM review for the middle band."""
        match = self._best_match(json.dumps(output, ensure_ascii=False))
        metadata = {
            "risk_intent": match["intent"],
            "matched_sample": match["text"],
            "cosine_similarity": match["cosine_similarity"],
            "euclidean_distance": match["euclidean_distance"],
            "review_again_threshold": self.settings.review_again_threshold,
            "reject_threshold": self.settings.reject_threshold,
        }
        similarity = match["cosine_similarity"]
        if similarity > self.settings.reject_threshold:
            action = self.settings.high_similarity_action
        elif similarity < self.settings.review_again_threshold:
            action = self.settings.low_similarity_action
        else:
            action = self.settings.medium_similarity_action
        metadata["semantic_action"] = action
        if action != ReviewAction.REVIEW_AGAIN:
            return self._build_semantic_result(action, similarity, match, metadata)
        review = self.fallback.review(output)
        return review.model_copy(
            update={
                "score": round(similarity * 100),
                "action": (ReviewAction.APPROVE if review.approved else ReviewAction.REVIEW_AGAIN),
                "metadata": {**review.metadata, **metadata},
            }
        )

    @staticmethod
    def _build_semantic_result(
        action: ReviewAction,
        similarity: float,
        match: dict[str, Any],
        metadata: dict[str, Any],
    ) -> ReviewResult:
        approved = action == ReviewAction.APPROVE
        return ReviewResult(
            approved=approved,
            score=round(similarity * 100),
            reasons=(
                ["未命中高风险语义样本"] if approved else [f"语义风险命中: {match['intent']}"]
            ),
            revision_suggestions=[] if approved else ["删除或改写风险表达"],
            action=action,
            metadata=metadata,
        )

    def _load_samples(self) -> list[dict[str, str]]:
        samples: list[dict[str, str]] = []
        for group in self.scenario.load_risk_samples():
            intent = group.get("intent")
            examples = group.get("examples")
            if not isinstance(intent, str) or not isinstance(examples, list):
                raise ValueError("risk_samples 条目必须包含 intent 和 examples。")
            for example in examples:
                if not isinstance(example, str):
                    raise ValueError("risk_samples.examples 必须全部是字符串。")
                samples.append({"intent": intent, "text": example})
        if not samples:
            raise ValueError(f"场景 {self.scenario.name} 缺少语义风险样本。")
        return samples

    def _embed_samples(self) -> list[list[float]]:
        vectors = self.embeddings.embed_documents([item["text"] for item in self.samples])
        if len(vectors) != len(self.samples):
            raise ValueError("Embedding 返回向量数量与风险样本数量不一致。")
        return [self._normalize(vector) for vector in vectors]

    def _best_match(self, text: str) -> dict[str, Any]:
        vectors = self.embeddings.embed_documents([text])
        if len(vectors) != 1:
            raise ValueError("Embedding 返回向量数量与输入文本数量不一致。")
        query = self._normalize(vectors[0])
        matches = []
        for sample, normalized in zip(self.samples, self.sample_vectors, strict=True):
            cosine_similarity = sum(
                left * right for left, right in zip(query, normalized, strict=True)
            )
            euclidean_distance = math.sqrt(
                sum((left - right) ** 2 for left, right in zip(query, normalized, strict=True))
            )
            matches.append(
                {
                    **sample,
                    "cosine_similarity": cosine_similarity,
                    "euclidean_distance": euclidean_distance,
                }
            )
        return max(matches, key=lambda item: item["cosine_similarity"])

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value**2 for value in vector))
        if magnitude == 0:
            raise ValueError("Embedding 向量不能为零向量。")
        return [value / magnitude for value in vector]
