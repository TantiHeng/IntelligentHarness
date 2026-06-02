"""默认依赖装配测试。"""

from intelligent_harness.adapters.settings import RuntimeConfig
from intelligent_harness.assembler import build_harness
from intelligent_harness.cli.fault_injection import InjectedOutputInference
from intelligent_harness.models import HarnessDecision, HarnessWorkflowState
from intelligent_harness.scenarios import ScenarioRegistry
from intelligent_harness.services import SemanticLayeredReviewer


class MatchingEmbeddings:
    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]


class UnexpectedModelCall:
    def invoke(self, prompt):
        raise AssertionError("高相似度直接拒绝不应调用 LLM")


def test_default_marketing_harness_uses_semantic_layered_reviewer(tmp_path):
    scenario = ScenarioRegistry().get("marketing_copy")
    inference = InjectedOutputInference(
        {"title": "标题", "body": "同义风险表达", "call_to_action": "购买"},
        scenario,
    )
    harness = build_harness(
        scenario_name="marketing_copy",
        config=RuntimeConfig(db_path=tmp_path / "audit.db"),
        model=UnexpectedModelCall(),
        inference=inference,
        embeddings=MatchingEmbeddings(),
    )

    response = harness.execute(
        HarnessWorkflowState(
            scenario="marketing_copy",
            input={"product": {"name": "p"}, "customer": {"name": "c"}},
        )
    )

    assert isinstance(harness.reviewer, SemanticLayeredReviewer)
    assert response.decision == HarnessDecision.REJECTED
    assert response.review
    assert response.review.metadata["cosine_similarity"] == 1.0
