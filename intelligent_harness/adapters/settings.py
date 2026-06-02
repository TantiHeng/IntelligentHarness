"""配置适配器：加载 YAML 策略和环境变量，不解释领域审核规则。"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from intelligent_harness.adapters.paths import project_path


load_dotenv(project_path(".env"))


class WorkflowPolicy(BaseModel):
    max_review_attempts: int = Field(default=3, ge=1)
    max_inference_attempts: int = Field(default=3, ge=1)


class PythonLoggingSettings(BaseModel):
    level: str = "INFO"


class BusinessEventSettings(BaseModel):
    alert_severity_threshold: int = Field(default=2, ge=1, le=3)


class HarnessSettings(BaseModel):
    default_scenario: str = "marketing_copy"
    policy: WorkflowPolicy = Field(default_factory=WorkflowPolicy)
    python_logging: PythonLoggingSettings = Field(default_factory=PythonLoggingSettings)
    business_events: BusinessEventSettings = Field(default_factory=BusinessEventSettings)


class RuntimeConfig(BaseModel):
    model_api_key: str = ""
    model_base_url: str = ""
    model_name: str = ""
    llm_temperature: float = Field(default=0.7, ge=0, le=2)
    llm_max_tokens: int = Field(default=4096, gt=0)
    llm_timeout: int = Field(default=60, gt=0)
    db_path: Path = Field(default_factory=lambda: project_path("data/harness_records.db"))
    settings: HarnessSettings = Field(default_factory=HarnessSettings)


def load_harness_settings(path: str | Path | None = None) -> HarnessSettings:
    settings_path = Path(path or project_path("config/harness.yaml"))
    with settings_path.open("r", encoding="utf-8") as file:
        return HarnessSettings.model_validate(yaml.safe_load(file) or {})


def load_runtime_config(
    settings_path: str | Path | None = None,
    db_path: str | Path | None = None,
) -> RuntimeConfig:
    resolved_db_path = Path(
        db_path or os.getenv("DB_PATH", project_path("data/harness_records.db"))
    )
    if not resolved_db_path.is_absolute():
        resolved_db_path = project_path(resolved_db_path)
    return RuntimeConfig(
        model_api_key=os.getenv("MODEL_API_KEY", "").strip(),
        model_base_url=os.getenv("MODEL_BASE_URL", "").strip(),
        model_name=os.getenv("MODEL_NAME", "").strip(),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        llm_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        db_path=resolved_db_path,
        settings=load_harness_settings(settings_path),
    )
