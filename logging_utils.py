from pathlib import Path
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Union


PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_ROOT = PROJECT_ROOT / "logs"


def _get_env_int(env_key: str, default: int) -> int:
    raw = os.getenv(env_key)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


DEFAULT_LOG_MAX_BYTES = _get_env_int("PROJECT_LOG_MAX_BYTES", 10 * 1024 * 1024)
DEFAULT_LOG_BACKUP_COUNT = _get_env_int("PROJECT_LOG_BACKUP_COUNT", 5)


def get_log_path(relative_log_path: Union[str, Path]) -> Path:
    """Return an absolute log path rooted in the project logs directory."""
    return LOGS_ROOT / Path(relative_log_path)


def configure_project_logger(
    logger_name: str,
    relative_log_path: Union[str, Path],
    level: int = logging.INFO,
    max_bytes: int = DEFAULT_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """Create a project logger that writes both to file and stdout."""
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    log_path = get_log_path(relative_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max(0, max_bytes),
        backupCount=max(0, backup_count),
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger
