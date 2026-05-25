import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from src.path_utils import get_env_path, get_file_path


load_dotenv(get_env_path())


def _get_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)

    if raw is None or raw.strip() == "":
        return default

    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是整数，当前值: {raw}") from exc


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)

    if raw is None or raw.strip() == "":
        return default

    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 必须是数字，当前值: {raw}") from exc


def _resolve_project_path(path_value: str) -> str:
    path = Path(path_value)

    if path.is_absolute():
        return str(path)

    return get_file_path(path_value)


@dataclass
class Config:
    """
    项目集中配置。

    配置来源：
    1. 系统环境变量；
    2. 项目根目录下的 .env 文件。

    注意：
    API Key 不应出现在 __repr__ 中。
    """

    MODEL_API_KEY: str = field(default_factory=lambda: _get_str("MODEL_API_KEY"))
    MODEL_BASE_URL: str = field(default_factory=lambda: _get_str("MODEL_BASE_URL"))
    MODEL_NAME: str = field(default_factory=lambda: _get_str("MODEL_NAME"))

    LLM_TEMPERATURE: float = field(default_factory=lambda: _get_float("LLM_TEMPERATURE", 0.7))
    LLM_MAX_TOKENS: int = field(default_factory=lambda: _get_int("LLM_MAX_TOKENS", 4096))
    LLM_TIMEOUT: int = field(default_factory=lambda: _get_int("LLM_TIMEOUT", 60))

    WORKFLOW_MAX_RETRIES: int = field(default_factory=lambda: _get_int("WORKFLOW_MAX_RETRIES", 2))
    DB_PATH: str = field(default_factory=lambda: _resolve_project_path(_get_str("DB_PATH", "data/marketing_records.db")))

    LOG_LEVEL: str = field(default_factory=lambda: _get_str("LOG_LEVEL", "INFO"))

    def __post_init__(self) -> None:
        if not self.MODEL_API_KEY:
            print("警告: MODEL_API_KEY 未在 .env 中设置")
        if not self.MODEL_NAME:
            print("警告: MODEL_NAME 未在 .env 中设置")

        if not 0 <= self.LLM_TEMPERATURE <= 2:
            raise ValueError("LLM_TEMPERATURE 必须在 0 到 2 之间。")

        if self.LLM_MAX_TOKENS <= 0:
            raise ValueError("LLM_MAX_TOKENS 必须大于 0。")

        if self.LLM_TIMEOUT <= 0:
            raise ValueError("LLM_TIMEOUT 必须大于 0。")

        if self.WORKFLOW_MAX_RETRIES < 0:
            raise ValueError("WORKFLOW_MAX_RETRIES 不能小于 0。")

    def __repr__(self) -> str:
        return (
            "Config("
            f"MODEL_NAME={self.MODEL_NAME}, "
            f"MODEL_BASE_URL={self.MODEL_BASE_URL}, "
            f"LLM_TEMPERATURE={self.LLM_TEMPERATURE}, "
            f"LLM_MAX_TOKENS={self.LLM_MAX_TOKENS}, "
            f"LLM_TIMEOUT={self.LLM_TIMEOUT}, "
            f"WORKFLOW_MAX_RETRIES={self.WORKFLOW_MAX_RETRIES}, "
            f"DB_PATH={self.DB_PATH}, "
            f"LOG_LEVEL={self.LOG_LEVEL}"
            ")"
        )


if __name__ == "__main__":
    conf = Config()
    print("MODEL_NAME:", conf.MODEL_NAME)
    print("完整配置对象:", conf)
    print("项目 .env 路径:", get_env_path())
