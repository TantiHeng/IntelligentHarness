import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.path_utils import get_env_path


load_dotenv(get_env_path())


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[31;1m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        color = self.COLORS.get(record.levelno, self.RESET)

        try:
            record.levelname = f"{color}{original_levelname}{self.RESET}"
            return super().format(record)
        finally:
            record.levelname = original_levelname


def _parse_log_level(level: Optional[str | int]) -> int:
    if isinstance(level, int):
        return level

    if not level:
        return logging.INFO

    parsed_level = logging.getLevelName(level.upper().strip())

    if isinstance(parsed_level, int):
        return parsed_level

    raise ValueError(f"无效日志级别: {level}")


def setup_logger(
    name: str = "IntelligentMarketingAssistant",
    level: str | int | None = None,
    log_dir: str | os.PathLike | None = None,
    reset_handlers: bool = False,
) -> logging.Logger:
    parsed_level = _parse_log_level(level or os.getenv("LOG_LEVEL", "INFO"))

    logger = logging.getLogger(name)
    logger.setLevel(parsed_level)
    logger.propagate = False

    if reset_handlers:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(parsed_level)
    console_handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(console_handler)

    project_root = Path(__file__).resolve().parent.parent

    if log_dir is None:
        log_dir_path = project_root / "logs"
    else:
        log_dir_path = Path(log_dir)

    log_dir_path.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = log_dir_path / f"run_{run_id}.log"

    file_handler = logging.FileHandler(
        log_file_path,
        encoding="utf-8",
    )

    # 文件日志记录 INFO 及以上，这样每次运行的流程日志都会落盘
    file_handler.setLevel(parsed_level)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    logger.info("日志文件已创建: %s", log_file_path)

    return logger


logger = setup_logger()
