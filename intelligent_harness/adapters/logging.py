"""内部日志适配器：配置 Python 运行日志，不记录业务事件严重级别。"""

import logging
from pathlib import Path

from intelligent_harness.adapters.paths import project_path
from intelligent_harness.adapters.settings import load_harness_settings


def setup_logger(
    name: str = "IntelligentHarness",
    level: str | None = None,
    log_dir: str | Path | None = None,
) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    parsed_level = logging.getLevelName(
        (level or load_harness_settings().python_logging.level).upper()
    )
    if not isinstance(parsed_level, int):
        raise ValueError(f"无效日志级别: {level}")
    logger.setLevel(parsed_level)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setLevel(parsed_level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    )
    logger.addHandler(handler)
    Path(log_dir or project_path("logs")).mkdir(parents=True, exist_ok=True)
    return logger


logger = setup_logger()
