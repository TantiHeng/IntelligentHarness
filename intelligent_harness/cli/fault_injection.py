"""故障注入替身：提供手写模型输出用于诊断，不调用真实模型。"""

import json
from pathlib import Path
from typing import Any

from intelligent_harness.models import ReviewResult
from intelligent_harness.scenarios import ScenarioDefinition


class InjectedOutputInference:
    """每次推理都返回手写输出，用于验证拦截链路。"""

    def __init__(
        self,
        output: dict[str, Any],
        scenario: ScenarioDefinition,
    ) -> None:
        self.output = scenario.validate("output", output)
        self.infer_called = 0
        self.retry_inference_called = 0

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        scenario: ScenarioDefinition,
    ) -> "InjectedOutputInference":
        output_path = Path(path)
        if not output_path.is_file():
            raise ValueError(f"故障注入输出文件不存在: {output_path}")
        try:
            value = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"故障注入输出不是合法 JSON: {output_path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"故障注入输出必须是 JSON object: {output_path}")
        return cls(value, scenario)

    def infer(self, input_data: dict[str, Any]) -> dict[str, Any]:
        self.infer_called += 1
        return self.output

    def retry_inference(
        self,
        input_data: dict[str, Any],
        output: dict[str, Any],
        review: ReviewResult,
    ) -> dict[str, Any]:
        self.retry_inference_called += 1
        return self.output


class UnexpectedModelCall:
    """当故障注入意外调用真实模型路径时，立即给出明确错误。"""

    def invoke(self, prompt: str) -> str:
        raise RuntimeError("故障注入模式不应调用真实模型。")
