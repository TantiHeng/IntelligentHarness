"""场景注册表：加载运营维护的 Prompt 与 Schema，不承载工作流状态流转。"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from intelligent_harness.adapters.paths import project_path


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    description: str
    reviewer: str
    root: Path
    prompts: dict[str, str]
    schemas: dict[str, str]

    def load_prompt(self, name: str) -> str:
        relative = self.prompts.get(name)
        if name == "retry_inference" and relative is None:
            relative = self.prompts["inference"]
        if relative is None:
            raise ValueError(f"场景 {self.name} 缺少 prompt: {name}")
        return (self.root / relative).read_text(encoding="utf-8")

    def render_prompt(self, name: str, **values: str) -> str:
        prompt = self.load_prompt(name)
        for key, value in values.items():
            prompt = prompt.replace(f"{{{key}}}", value)
        return prompt

    def load_schema(self, name: str) -> dict[str, Any]:
        path = self.root / self.schemas[name]
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        return schema

    def validate(self, schema_name: str, value: Any) -> dict[str, Any]:
        Draft202012Validator(self.load_schema(schema_name)).validate(value)
        return value

    def validate_resources(self) -> None:
        self.load_prompt("inference")
        self.load_prompt("review")
        self.load_schema("input")
        self.load_schema("output")


class ScenarioRegistry:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or project_path("scenarios"))

    def list(self) -> list[ScenarioDefinition]:
        return [
            self._load(path)
            for path in sorted(self.root.iterdir())
            if (path / "scenario.yaml").exists()
        ]

    def get(self, name: str) -> ScenarioDefinition:
        path = self.root / name
        if not (path / "scenario.yaml").exists():
            raise ValueError(f"未知场景: {name}")
        return self._load(path)

    @staticmethod
    def _load(path: Path) -> ScenarioDefinition:
        data = yaml.safe_load((path / "scenario.yaml").read_text(encoding="utf-8"))
        return ScenarioDefinition(
            name=data["name"],
            description=data["description"],
            reviewer=data.get("reviewer", "llm"),
            root=path,
            prompts=data["prompts"],
            schemas=data["schemas"],
        )
