"""CLI 边界测试。

覆盖场景列表、策略配置校验，以及非法场景、缺失文件和损坏 JSON 的友好错误提示。
不调用真实模型，也不验证完整推理事务；完整事务由 test_workflow.py 覆盖。
"""

import cli


def test_cli_lists_scenarios(capsys):
    assert cli.main(["scenario-list"]) == 0
    assert "marketing_copy" in capsys.readouterr().out


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
