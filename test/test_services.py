"""推理与审核服务测试。"""

import json
import math

import pytest

from intelligent_harness.adapters.settings import SemanticReviewSettings
from intelligent_harness.models import ReviewAction, ReviewResult
from intelligent_harness.scenarios import ScenarioDefinition, ScenarioRegistry
from intelligent_harness.services import ReviewService, SemanticLayeredReviewer


class RecordingReviewModel:
    def __init__(self):
        self.prompt = ""

    def invoke(self, prompt):
        self.prompt = prompt
        return """{
            "approved": false,
            "score": 20,
            "reasons": ["包含无法证实的收益承诺"],
            "revision_suggestions": ["删除收益承诺"]
        }"""


def test_marketing_review_uses_model_for_semantic_intent():
    model = RecordingReviewModel()
    scenario = ScenarioRegistry().get("marketing_copy")
    output = {
        "title": "让业绩一路向上",
        "body": "采用这套方案后，回报只会增加，不存在亏损可能。",
        "call_to_action": "立即了解",
    }

    review = ReviewService(model, scenario).review(output)

    assert review.approved is False
    assert review.reasons == ["包含无法证实的收益承诺"]
    assert "回报只会增加，不存在亏损可能" in model.prompt
    assert "不要只做关键词匹配" in model.prompt


class FixedSimilarityEmbeddings:
    def __init__(self, similarity):
        self.similarity = similarity
        self.calls = []

    def embed_documents(self, texts):
        self.calls.append(texts)
        if texts == ["稳赚不赔"]:
            return [[self.similarity, math.sqrt(1 - self.similarity**2)]]
        return [[1.0, 0.0]]


class RecordingFallbackReviewer:
    def __init__(self, approved=False):
        self.approved = approved
        self.called = 0

    def review(self, output):
        self.called += 1
        return ReviewResult(approved=self.approved, score=50, reasons=["LLM 复核"])


def semantic_scenario(tmp_path):
    (tmp_path / "risk_samples.json").write_text(
        json.dumps([{"intent": "guaranteed_return", "examples": ["稳赚不赔"]}]),
        encoding="utf-8",
    )
    return ScenarioDefinition(
        name="semantic",
        description="semantic",
        reviewer="semantic_layered",
        root=tmp_path,
        prompts={},
        schemas={},
        risk_samples="risk_samples.json",
    )


def test_semantic_reviewer_rejects_above_high_threshold_without_llm(tmp_path):
    fallback = RecordingFallbackReviewer()
    reviewer = SemanticLayeredReviewer(
        FixedSimilarityEmbeddings(0.81),
        semantic_scenario(tmp_path),
        fallback,
        SemanticReviewSettings(),
    )

    review = reviewer.review({"body": "semantic text"})

    assert review.action == ReviewAction.REJECT
    assert review.approved is False
    assert fallback.called == 0
    assert review.metadata["cosine_similarity"] == 0.81


@pytest.mark.parametrize("similarity", [0.6, 0.8])
def test_semantic_reviewer_uses_llm_for_middle_band_boundaries(tmp_path, similarity):
    fallback = RecordingFallbackReviewer()
    reviewer = SemanticLayeredReviewer(
        FixedSimilarityEmbeddings(similarity),
        semantic_scenario(tmp_path),
        fallback,
        SemanticReviewSettings(),
    )

    review = reviewer.review({"body": "semantic text"})

    assert review.action == ReviewAction.REVIEW_AGAIN
    assert fallback.called == 1


def test_semantic_reviewer_approves_below_low_threshold_without_llm(tmp_path):
    fallback = RecordingFallbackReviewer()
    reviewer = SemanticLayeredReviewer(
        FixedSimilarityEmbeddings(0.59),
        semantic_scenario(tmp_path),
        fallback,
        SemanticReviewSettings(),
    )

    review = reviewer.review({"body": "semantic text"})

    assert review.action == ReviewAction.APPROVE
    assert review.approved is True
    assert fallback.called == 0
    assert review.score == 59


def test_semantic_reviewer_uses_configured_band_action(tmp_path):
    fallback = RecordingFallbackReviewer()
    reviewer = SemanticLayeredReviewer(
        FixedSimilarityEmbeddings(0.81),
        semantic_scenario(tmp_path),
        fallback,
        SemanticReviewSettings(high_similarity_action=ReviewAction.REVIEW_AGAIN),
    )

    review = reviewer.review({"body": "semantic text"})

    assert review.action == ReviewAction.REVIEW_AGAIN
    assert fallback.called == 1


def test_semantic_reviewer_caches_sample_vectors(tmp_path):
    embeddings = FixedSimilarityEmbeddings(0.59)
    reviewer = SemanticLayeredReviewer(
        embeddings,
        semantic_scenario(tmp_path),
        RecordingFallbackReviewer(),
        SemanticReviewSettings(),
    )

    reviewer.review({"body": "first"})
    reviewer.review({"body": "second"})

    assert embeddings.calls == [["稳赚不赔"], ['{"body": "first"}'], ['{"body": "second"}']]
