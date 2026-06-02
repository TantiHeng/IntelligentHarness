"""CLI 边界测试。

覆盖场景列表、策略配置校验，以及非法场景、缺失文件和损坏 JSON 的友好错误提示。
离线端到端用例使用模型替身，但执行真实 CLI、装配器、状态图、Schema 和 SQLite 链路。
"""

import json

import cli
from intelligent_harness.adapters.settings import RuntimeConfig
from intelligent_harness.assembler import build_harness as assemble_harness
from intelligent_harness.cli.fault_injection import InjectedOutputInference
from intelligent_harness.models import HarnessDecision, HarnessResponse


def test_cli_lists_scenarios(capsys):
    assert cli.main(["scenario-list"]) == 0
    assert "marketing_copy" in capsys.readouterr().out


def test_cli_without_command_prints_help(capsys):
    assert cli.main([]) == 0
    output = capsys.readouterr().out
    assert "usage: intelligent-harness" in output
    assert "run" in output


def test_cli_validates_config(capsys):
    assert cli.main(["config-validate"]) == 0
    assert "max_review_attempts" in capsys.readouterr().out


def test_cli_reports_unknown_scenario_without_traceback(capsys):
    assert cli.main(["scenario-validate", "missing"]) == 2
    assert "未知场景: missing" in capsys.readouterr().err


def test_cli_reports_missing_fault_file_without_traceback(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    assert cli.main(["fault-inject", "--output", str(missing)]) == 2
    assert "故障注入输出文件不存在" in capsys.readouterr().err


def test_cli_reports_invalid_fault_json_without_traceback(tmp_path, capsys):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    assert cli.main(["fault-inject", "--output", str(invalid)]) == 2
    assert "故障注入输出不是合法 JSON" in capsys.readouterr().err


def test_fault_injection_replaces_inference_but_keeps_default_reviewer(monkeypatch, capsys):
    captured = {}

    class Harness:
        def execute(self, state):
            return HarnessResponse(
                run_id=state.run_id,
                thread_id=state.thread_id,
                scenario=state.scenario,
                decision=HarnessDecision.REJECTED,
                approved=False,
            )

    def build_harness(**kwargs):
        captured.update(kwargs)
        return Harness()

    monkeypatch.setattr("intelligent_harness.cli.commands.build_harness", build_harness)

    assert cli.main(["fault-inject"]) == 0
    assert isinstance(captured["inference"], InjectedOutputInference)
    assert "reviewer" not in captured
    assert "model" not in captured
    assert '"decision": "rejected"' in capsys.readouterr().out


class LowRiskEmbeddings:
    def embed_documents(self, texts):
        if len(texts) == 1:
            return [[1.0, 0.0]]
        return [[0.0, 1.0] for _ in texts]


class SuccessfulInferenceModel:
    def invoke(self, prompt):
        return """{
            "title": "专业服务方案",
            "body": "帮助团队改善工作流程。",
            "call_to_action": "了解更多"
        }"""


class UnexpectedModelCall:
    def invoke(self, prompt):
        raise AssertionError("高相似度 Mock Embedding 应直接拦截，不应调用外部模型")


def test_run_command_executes_end_to_end_and_prints_host_kv_payload(
    tmp_path,
    monkeypatch,
    capsys,
):
    def build_harness(**kwargs):
        return assemble_harness(
            **kwargs,
            config=RuntimeConfig(db_path=tmp_path / "audit.db"),
            model=SuccessfulInferenceModel(),
            embeddings=LowRiskEmbeddings(),
        )

    monkeypatch.setattr("intelligent_harness.cli.commands.build_harness", build_harness)

    assert (
        cli.main(
            [
                "run",
                "--scenario",
                "marketing_copy",
                "--input",
                "examples/marketing_input.json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert isinstance(payload, dict)
    assert payload["decision"] == "approved"
    assert payload["approved"] is True
    assert payload["output"]["title"] == "专业服务方案"
    assert payload["record_id"]


def test_fault_inject_with_mock_embeddings_executes_end_to_end_and_rejects(
    tmp_path,
    monkeypatch,
    capsys,
):
    def build_harness(**kwargs):
        return assemble_harness(
            **kwargs,
            config=RuntimeConfig(db_path=tmp_path / "audit.db"),
            model=UnexpectedModelCall(),
        )

    monkeypatch.setattr("intelligent_harness.cli.commands.build_harness", build_harness)

    assert (
        cli.main(
            [
                "fault-inject",
                "--scenario",
                "marketing_copy",
                "--output",
                "fixtures/fault_injection/marketing_copy_rejected.json",
                "--mock-embeddings",
                "fixtures/fault_injection/marketing_copy_rejected.embeddings.json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["decision"] == "rejected"
    assert payload["approved"] is False
    assert payload["review"]["action"] == "reject"
    assert payload["review"]["metadata"]["risk_intent"] == "guaranteed_return"
    assert payload["review"]["metadata"]["cosine_similarity"] == 1.0
