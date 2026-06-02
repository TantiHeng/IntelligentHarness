"""外置场景资源测试。

验证四个预设场景均可被注册表发现，Prompt 与 JSON Schema 资源可以加载，
并验证贷款场景会拒绝不符合输入 Schema 的数据。
不判断 Prompt 的业务质量，也不替代领域人员审核 Schema 是否充分。
"""

import pytest
from jsonschema import ValidationError

from intelligent_harness.scenarios import ScenarioRegistry


def test_registry_loads_four_external_scenarios():
    scenarios = ScenarioRegistry().list()
    assert {item.name for item in scenarios} == {
        "marketing_copy", "content_safety", "financial_audit", "loan_qualification"
    }


@pytest.mark.parametrize("name", ["marketing_copy", "content_safety", "financial_audit", "loan_qualification"])
def test_scenario_resources_are_valid(name):
    ScenarioRegistry().get(name).validate_resources()


def test_json_schema_rejects_invalid_loan_input():
    scenario = ScenarioRegistry().get("loan_qualification")
    with pytest.raises(ValidationError):
        scenario.validate("input", {
            "applicant": {"applicant_id": "a-1", "annual_income": -1},
            "requested_amount": 100,
            "loan_type": "personal",
        })
