"""故障注入替身：使用手写推理输出验证后续审核与拦截链路。"""

import json
from pathlib import Path
from typing import Any

from intelligent_harness.models import ReviewResult
from intelligent_harness.scenarios import ScenarioDefinition


class InjectedEmbeddings:
    """Return fixture vectors instead of calling an external embedding service."""

    def __init__(
        self,
        sample_vectors: dict[str, list[float]],
        query_vector: list[float],
        default_sample_vector: list[float],
    ) -> None:
        self.sample_vectors = sample_vectors
        self.query_vector = query_vector
        self.default_sample_vector = default_sample_vector

    @classmethod
    def from_file(cls, path: str | Path) -> "InjectedEmbeddings":
        fixture_path = Path(path)
        if not fixture_path.is_file():
            raise ValueError(f"Mock Embedding 文件不存在: {fixture_path}")
        try:
            value = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Mock Embedding 文件不是合法 JSON: {fixture_path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Mock Embedding 文件必须是 JSON object: {fixture_path}")
        sample_vectors = value.get("sample_vectors", {})
        query_vector = value.get("query_vector")
        default_sample_vector = value.get("default_sample_vector")
        if not isinstance(sample_vectors, dict):
            raise ValueError("Mock Embedding sample_vectors 必须是 JSON object。")
        return cls(
            {
                text: cls._validate_vector(vector, label=f"sample_vectors[{text!r}]")
                for text, vector in sample_vectors.items()
                if isinstance(text, str)
            },
            cls._validate_vector(query_vector, label="query_vector"),
            cls._validate_vector(default_sample_vector, label="default_sample_vector"),
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if len(texts) == 1 and texts[0] not in self.sample_vectors:
            return [self.query_vector]
        return [
            self.sample_vectors.get(text, self.default_sample_vector)
            for text in texts
        ]

    @staticmethod
    def _validate_vector(value: Any, *, label: str) -> list[float]:
        if not isinstance(value, list) or not value:
            raise ValueError(f"Mock Embedding {label} 必须是非空数值 array。")
        if not all(isinstance(item, (int, float)) for item in value):
            raise ValueError(f"Mock Embedding {label} 必须是非空数值 array。")
        return [float(item) for item in value]


class InjectedOutputInference:
    """Return a schema-valid handwritten output instead of calling inference."""

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
