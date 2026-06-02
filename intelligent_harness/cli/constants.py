"""CLI 命令常量：集中维护受控命令集合，不执行命令行为。"""

from enum import Enum


class Command(str, Enum):
    CONFIG_VALIDATE = "config-validate"
    SCENARIO_LIST = "scenario-list"
    SCENARIO_VALIDATE = "scenario-validate"
    SCENARIO_INSPECT = "scenario-inspect"
    RUN = "run"
    FAULT_INJECT = "fault-inject"
