"""外置场景资源测试。

验证四个预设场景均可被注册表发现，Prompt 与 JSON Schema 资源可以加载，
并验证贷款场景会拒绝不符合输入 Schema 的数据。
不判断 Prompt 的业务质量，也不替代领域人员审核 Schema 是否充分。
"""

import pytest
from jsonschema import ValidationError

from intelligent_harness.scenarios import ScenarioDefinition, ScenarioRegistry


def test_registry_loads_four_external_scenarios():
    scenarios = ScenarioRegistry().list()
    assert {item.name for item in scenarios} == {
        "marketing_copy",
        "content_safety",
        "financial_audit",
        "loan_qualification",
    }


def test_non_marketing_scenarios_are_labeled_demo_skeletons():
    registry = ScenarioRegistry()
    for name in ("content_safety", "financial_audit", "loan_qualification"):
        assert "[DEMO SKELETON]" in registry.get(name).description


@pytest.mark.parametrize(
    "name", ["marketing_copy", "content_safety", "financial_audit", "loan_qualification"]
)
def test_scenario_resources_are_valid(name):
    ScenarioRegistry().get(name).validate_resources()


def test_json_schema_rejects_invalid_loan_input():
    scenario = ScenarioRegistry().get("loan_qualification")
    with pytest.raises(ValidationError):
        scenario.validate(
            "input",
            {
                "applicant": {"applicant_id": "a-1", "annual_income": -1},
                "requested_amount": 100,
                "loan_type": "personal",
            },
        )


def test_validation_checks_configured_retry_prompt(tmp_path):
    scenario = ScenarioDefinition(
        name="broken_retry",
        description="broken retry prompt",
        reviewer="llm",
        root=tmp_path,
        prompts={
            "inference": "inference.txt",
            "retry_inference": "missing.txt",
            "review": "review.txt",
        },
        schemas={"input": "input.json", "output": "output.json"},
    )
    (tmp_path / "inference.txt").write_text("{input_json}", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        scenario.validate_resources()


def test_risk_sample_validation_rejects_empty_examples(tmp_path):
    (tmp_path / "risk_samples.json").write_text(
        '[{"intent": "guaranteed_return", "examples": []}]',
        encoding="utf-8",
    )
    scenario = ScenarioDefinition(
        name="broken_samples",
        description="broken semantic samples",
        reviewer="semantic_layered",
        root=tmp_path,
        prompts={},
        schemas={},
        risk_samples="risk_samples.json",
    )

    with pytest.raises(ValueError, match="examples"):
        scenario.load_risk_samples()
