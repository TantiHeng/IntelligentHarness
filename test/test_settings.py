"""配置边界测试。

配置决定工作流重试次数、告警阈值和模型调用参数。非法配置必须在装配工作流前失败，
避免运行时静默使用错误策略。
"""

import pytest
from pydantic import ValidationError

from intelligent_harness.adapters.settings import (
    BusinessEventSettings,
    RuntimeConfig,
    SemanticReviewSettings,
    WorkflowPolicy,
    load_harness_settings,
    load_runtime_config,
)
from intelligent_harness.models import ReviewAction


def test_load_harness_settings_reads_valid_yaml(tmp_path):
    settings_path = tmp_path / "harness.yaml"
    settings_path.write_text(
        """default_scenario: marketing_copy
policy:
  max_review_attempts: 1
  max_inference_attempts: 2
business_events:
  alert_severity_threshold: 3
""",
        encoding="utf-8",
    )

    settings = load_harness_settings(settings_path)

    assert settings.default_scenario == "marketing_copy"
    assert settings.policy.max_review_attempts == 1
    assert settings.policy.max_inference_attempts == 2
    assert settings.business_events.alert_severity_threshold == 3


def test_load_harness_settings_rejects_invalid_yaml_policy(tmp_path):
    settings_path = tmp_path / "harness.yaml"
    settings_path.write_text(
        """policy:
  max_review_attempts: 0
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="max_review_attempts"):
        load_harness_settings(settings_path)


@pytest.mark.parametrize("field", ["max_review_attempts", "max_inference_attempts"])
def test_workflow_policy_rejects_zero_attempts(field):
    with pytest.raises(ValidationError):
        WorkflowPolicy(**{field: 0})


@pytest.mark.parametrize("threshold", [0, 4])
def test_business_event_settings_reject_out_of_range_threshold(threshold):
    with pytest.raises(ValidationError):
        BusinessEventSettings(alert_severity_threshold=threshold)


@pytest.mark.parametrize(
    ("environment", "expected_error"),
    [
        ({"LLM_TEMPERATURE": "-0.1"}, "llm_temperature"),
        ({"LLM_TEMPERATURE": "2.1"}, "llm_temperature"),
        ({"LLM_MAX_TOKENS": "0"}, "llm_max_tokens"),
        ({"LLM_TIMEOUT": "0"}, "llm_timeout"),
    ],
)
def test_runtime_config_rejects_invalid_model_environment(monkeypatch, environment, expected_error):
    for name in ("LLM_TEMPERATURE", "LLM_MAX_TOKENS", "LLM_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError, match=expected_error):
        load_runtime_config()


def test_runtime_config_accepts_minimum_model_limits():
    config = RuntimeConfig(llm_temperature=0, llm_max_tokens=1, llm_timeout=1)

    assert config.llm_temperature == 0
    assert config.llm_max_tokens == 1
    assert config.llm_timeout == 1


def test_runtime_config_loads_separate_embedding_endpoint(monkeypatch):
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-key")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://embedding.example.com/v1")
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "embedding-model")

    config = load_runtime_config()

    assert config.embedding_api_key == "embedding-key"
    assert config.embedding_base_url == "https://embedding.example.com/v1"
    assert config.embedding_model_name == "embedding-model"


@pytest.mark.parametrize(
    ("review_again_threshold", "reject_threshold"),
    [(0.8, 0.8), (0.9, 0.8)],
)
def test_semantic_review_thresholds_must_be_ordered(review_again_threshold, reject_threshold):
    with pytest.raises(ValidationError, match="review_again_threshold"):
        SemanticReviewSettings(
            review_again_threshold=review_again_threshold,
            reject_threshold=reject_threshold,
        )


def test_semantic_review_actions_are_configurable():
    settings = SemanticReviewSettings(
        low_similarity_action="reject",
        medium_similarity_action="approve",
        high_similarity_action="review_again",
    )

    assert settings.low_similarity_action == ReviewAction.REJECT
    assert settings.medium_similarity_action == ReviewAction.APPROVE
    assert settings.high_similarity_action == ReviewAction.REVIEW_AGAIN
