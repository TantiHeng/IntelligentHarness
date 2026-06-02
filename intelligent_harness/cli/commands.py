"""CLI 命令处理器：连接用户参数与核心 API，不实现控制事务。"""

from __future__ import annotations

import json
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from intelligent_harness.adapters.paths import project_path
from intelligent_harness.adapters.settings import load_harness_settings
from intelligent_harness.assembler import build_harness
from intelligent_harness.cli.constants import Command
from intelligent_harness.cli.fault_injection import InjectedEmbeddings, InjectedOutputInference
from intelligent_harness.models import HarnessResponse, HarnessWorkflowState
from intelligent_harness.scenarios import ScenarioDefinition, ScenarioRegistry

CommandHandler = Callable[[Namespace], None]


class ScenarioArgs(Protocol):
    name: str


class RunArgs(Protocol):
    scenario: str
    input: str


class FaultInjectionArgs(Protocol):
    scenario: str
    output: str
    mock_embeddings: str | None


def validate_config(args: object) -> None:
    print(load_harness_settings().model_dump_json(indent=2))


def list_scenarios(args: object) -> None:
    for scenario in ScenarioRegistry().list():
        print(f"{scenario.name}: {scenario.description}")


def validate_scenario(args: ScenarioArgs) -> None:
    scenario = _load_valid_scenario(args.name)
    print(_scenario_json(scenario))


def inspect_scenario(args: ScenarioArgs) -> None:
    scenario = _load_valid_scenario(args.name)
    print(_scenario_json(scenario, include_resources=True))


def run_harness(args: RunArgs) -> None:
    scenario = ScenarioRegistry().get(args.scenario)
    payload = _load_json_object(project_path(args.input), label="宿主输入")
    scenario.validate("input", payload)
    state = HarnessWorkflowState(scenario=scenario.name, input=payload)
    response = build_harness(scenario_name=scenario.name).execute(state)
    _print_host_payload(response)


def inject_fault(args: FaultInjectionArgs) -> None:
    scenario = ScenarioRegistry().get(args.scenario)
    inference = InjectedOutputInference.from_file(args.output, scenario)
    harness = build_harness(
        scenario_name=scenario.name,
        inference=inference,
        embeddings=(
            InjectedEmbeddings.from_file(args.mock_embeddings)
            if args.mock_embeddings
            else None
        ),
    )
    state = HarnessWorkflowState(scenario=scenario.name, input={})
    _print_host_payload(harness.execute(state))


HANDLERS: dict[Command, CommandHandler] = {
    Command.CONFIG_VALIDATE: validate_config,
    Command.SCENARIO_LIST: list_scenarios,
    Command.SCENARIO_VALIDATE: validate_scenario,
    Command.SCENARIO_INSPECT: inspect_scenario,
    Command.RUN: run_harness,
    Command.FAULT_INJECT: inject_fault,
}


def _load_valid_scenario(name: str) -> ScenarioDefinition:
    scenario = ScenarioRegistry().get(name)
    scenario.validate_resources()
    return scenario


def _scenario_json(
    scenario: ScenarioDefinition,
    *,
    include_resources: bool = False,
) -> str:
    data: dict[str, Any] = {
        "name": scenario.name,
        "description": scenario.description,
        "reviewer": scenario.reviewer,
    }
    if include_resources:
        data["prompts"] = scenario.prompts
        data["schemas"] = scenario.schemas
        data["risk_samples"] = scenario.risk_samples
    return json.dumps(data, ensure_ascii=False, indent=2)


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label}文件不存在: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label}不是合法 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}必须是 JSON object: {path}")
    return value


def _print_host_payload(response: HarnessResponse) -> None:
    print(json.dumps(response.to_host_payload(), ensure_ascii=False, indent=2))
