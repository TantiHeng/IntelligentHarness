from pathlib import Path

import pytest

from src.config import Config
from src.path_utils import get_env_path, get_file_path, get_project_root
from src.services.recorder import MarketingRecorder


def test_get_project_root_points_to_project_root():
    project_root = Path(get_project_root())

    assert project_root.name == "IntelligentMarketingAssistant_AutoSend"
    assert (project_root / "src").exists()


def test_get_env_path_points_to_root_env():
    env_path = Path(get_env_path())

    assert env_path.name == ".env"
    assert env_path.parent == Path(get_project_root())


def test_get_file_path_uses_project_root():
    path = Path(get_file_path("data/marketing_records.db"))

    assert path.parent.name == "data"
    assert path.name == "marketing_records.db"
    assert str(path).startswith(str(Path(get_project_root())))


def test_config_reads_environment_variables(monkeypatch, tmp_path):
    db_path = tmp_path / "records.db"

    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_MAX_TOKENS", "1024")
    monkeypatch.setenv("LLM_TIMEOUT", "15")
    monkeypatch.setenv("WORKFLOW_MAX_RETRIES", "3")
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    config = Config()

    assert config.MODEL_API_KEY == "test-key"
    assert config.MODEL_BASE_URL == "https://example.com/v1"
    assert config.MODEL_NAME == "test-model"
    assert config.LLM_TEMPERATURE == 0.2
    assert config.LLM_MAX_TOKENS == 1024
    assert config.LLM_TIMEOUT == 15
    assert config.WORKFLOW_MAX_RETRIES == 3
    assert config.DB_PATH == str(db_path)
    assert config.LOG_LEVEL == "DEBUG"


def test_config_resolves_relative_db_path_to_project_root(monkeypatch):
    monkeypatch.setenv("DB_PATH", "data/test_marketing_records.db")

    config = Config()

    assert config.DB_PATH == get_file_path("data/test_marketing_records.db")


def test_config_rejects_invalid_numeric_values(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT", "invalid")

    with pytest.raises(ValueError, match="LLM_TIMEOUT 必须是整数"):
        Config()


def test_recorder_uses_injected_config_db_path(monkeypatch, tmp_path):
    db_path = tmp_path / "configured_records.db"
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    config = Config(DB_PATH=str(db_path))

    recorder = MarketingRecorder(config=config)

    assert recorder.repo.db_path == db_path
    assert db_path.exists()
