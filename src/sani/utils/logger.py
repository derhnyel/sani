import logging
from sani.core.config import Config
from enum import Enum, unique


@unique
class LogLevels(Enum):
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


_LOGGER = logging.getLogger(__name__)
_LEVEL = eval(f"logging.{Config.log_level.upper()}")
_LOGGER.setLevel(_LEVEL)


def get_logger(format_str: str = None) -> logging.Logger:
    formatter = logging.Formatter(
        f"%(asctime)s::%(levelname)s::{format_str if format_str else str()}::%(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    _LOGGER.addHandler(console_handler)

    return _LOGGER
