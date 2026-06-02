"""配置适配器：加载 YAML 策略和环境变量，不解释领域审核规则。"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from intelligent_harness.adapters.paths import project_path
from intelligent_harness.models import ReviewAction

load_dotenv(project_path(".env"))


class WorkflowPolicy(BaseModel):
    max_review_attempts: int = Field(default=3, ge=1)
    max_inference_attempts: int = Field(default=3, ge=1)


class PythonLoggingSettings(BaseModel):
    level: str = "INFO"


class BusinessEventSettings(BaseModel):
    alert_severity_threshold: int = Field(default=2, ge=1, le=3)


class SemanticReviewSettings(BaseModel):
    review_again_threshold: float = Field(default=0.6, ge=0, le=1)
    reject_threshold: float = Field(default=0.8, ge=0, le=1)
    low_similarity_action: ReviewAction = ReviewAction.APPROVE
    medium_similarity_action: ReviewAction = ReviewAction.REVIEW_AGAIN
    high_similarity_action: ReviewAction = ReviewAction.REJECT

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "SemanticReviewSettings":
        if self.review_again_threshold >= self.reject_threshold:
            raise ValueError("review_again_threshold 必须小于 reject_threshold。")
        return self


class HarnessSettings(BaseModel):
    default_scenario: str = "marketing_copy"
    policy: WorkflowPolicy = Field(default_factory=WorkflowPolicy)
    python_logging: PythonLoggingSettings = Field(default_factory=PythonLoggingSettings)
    business_events: BusinessEventSettings = Field(default_factory=BusinessEventSettings)
    semantic_review: SemanticReviewSettings = Field(default_factory=SemanticReviewSettings)


class RuntimeConfig(BaseModel):
    model_api_key: str = ""
    model_base_url: str = ""
    model_name: str = ""
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_model_name: str = ""
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
        db_path or os.getenv("DB_PATH") or project_path("data/harness_records.db")
    )
    if not resolved_db_path.is_absolute():
        resolved_db_path = project_path(resolved_db_path)
    return RuntimeConfig(
        model_api_key=os.getenv("MODEL_API_KEY", "").strip(),
        model_base_url=os.getenv("MODEL_BASE_URL", "").strip(),
        model_name=os.getenv("MODEL_NAME", "").strip(),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY", "").strip(),
        embedding_base_url=os.getenv("EMBEDDING_BASE_URL", "").strip(),
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "").strip(),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        llm_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        db_path=resolved_db_path,
        settings=load_harness_settings(settings_path),
    )
