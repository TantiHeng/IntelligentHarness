"""公共 API：延迟导出稳定入口，避免导入子模块时初始化可选运行依赖。"""

from typing import Any

__all__ = [
    "HarnessDecision",
    "HarnessResponse",
    "HarnessWorkflow",
    "HarnessWorkflowState",
    "ReviewAction",
    "ReviewResult",
    "build_harness",
]


def __getattr__(name: str) -> Any:
    if name == "build_harness":
        from intelligent_harness.assembler import build_harness

        return build_harness
    if name == "HarnessWorkflow":
        from intelligent_harness.workflow import HarnessWorkflow

        return HarnessWorkflow
    if name in {
        "HarnessDecision",
        "HarnessResponse",
        "HarnessWorkflowState",
        "ReviewAction",
        "ReviewResult",
    }:
        from intelligent_harness import models

        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
