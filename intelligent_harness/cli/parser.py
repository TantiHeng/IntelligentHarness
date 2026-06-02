"""CLI 参数解析器：声明命令帮助和参数格式，不执行命令逻辑。"""

import argparse

from intelligent_harness.adapters.paths import project_path
from intelligent_harness.cli.constants import Command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="intelligent-harness",
        description="校验场景资源、运行输出控制流程或执行本地故障注入。",
        epilog="运营配置位于 config/ 与 scenarios/。使用 `<command> --help` 查看子命令参数。",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="commands",
    )
    _add_config_validate(subparsers)
    _add_scenario_list(subparsers)
    _add_scenario_validate(subparsers)
    _add_scenario_inspect(subparsers)
    _add_run(subparsers)
    _add_fault_inject(subparsers)
    return parser


def _add_config_validate(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        Command.CONFIG_VALIDATE.value,
        description="读取并校验 YAML 策略配置。",
        help="校验 YAML 策略配置",
    )


def _add_scenario_list(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        Command.SCENARIO_LIST.value,
        description="列出 scenarios/ 下可用的场景资源。",
        help="列出可用场景",
    )


def _add_scenario_validate(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        Command.SCENARIO_VALIDATE.value,
        description="校验指定场景的 YAML、prompt 和 JSON Schema 资源。",
        help="校验指定场景资源",
    )
    parser.add_argument("name", help="场景名称，例如 marketing_copy")


def _add_scenario_inspect(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        Command.SCENARIO_INSPECT.value,
        description="校验并输出指定场景的资源绑定信息。",
        help="查看指定场景资源",
    )
    parser.add_argument("name", help="场景名称，例如 marketing_copy")


def _add_run(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        Command.RUN.value,
        description="使用宿主输入运行完整推理与审核流程。",
        help="运行完整控制流程",
    )
    parser.add_argument("--scenario", required=True, help="场景名称")
    parser.add_argument("--input", required=True, help="JSON 输入文件路径")


def _add_fault_inject(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        Command.FAULT_INJECT.value,
        description="注入手写模型输出，验证审核拦截、重复审核和最终拒绝。",
        epilog="该命令不会调用真实模型，适合人工编写不合规输出后执行回归验证。",
        help="注入手写模型输出",
    )
    parser.add_argument(
        "--scenario",
        default="marketing_copy",
        help="场景名称，默认 marketing_copy",
    )
    parser.add_argument(
        "--output",
        default=str(
            project_path("fixtures/fault_injection/marketing_copy_rejected.json")
        ),
        help="需要注入的 JSON 模型输出文件",
    )
