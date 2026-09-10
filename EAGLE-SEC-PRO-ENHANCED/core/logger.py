import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOGGERS: dict[str, logging.Logger] = {}

FMT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str = "eagle_sec") -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            LOG_DIR / "eagle_sec.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(FMT, DATE_FMT))

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(FMT, DATE_FMT))

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    _LOGGERS[name] = logger
    return logger
