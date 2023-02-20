from __future__ import annotations

import re
import sys
import traceback
from itertools import takewhile
from typing import Any, Optional

import loguru
from loguru import logger as logger


def add_traceback(record: loguru.Record) -> None:
    extra = record["extra"]
    if extra.get("with_traceback", False):
        extra["traceback"] = "\n" + "".join(traceback.format_stack())
    else:
        extra["traceback"] = ""


def tracing_formatter(record: loguru.Record) -> str:
    # Filter out frames coming from Loguru internals
    frames = takewhile(
        lambda f: "/loguru/" not in f.filename, traceback.extract_stack()
    )
    stack = " > ".join(f"{f.filename}:{f.name}:{f.lineno}" for f in frames)
    record["extra"]["stack"] = stack

    if record["extra"].get("with_backtrace", False):
        return "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[stack]}</cyan> - <level>{message}</level>\n{exception}"
    else:
        return "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n{exception}"


class LogFilter:
    def __init__(self, level: str, regex: Optional[str] = None) -> None:
        self.level = level
        self.regex = regex

    def __call__(self, record: loguru.Record) -> bool:
        levelno = logger.level(self.level).no
        if self.regex is None:
            return record["level"].no >= levelno
        else:
            return record["level"].no >= levelno and not bool(
                re.search(self.regex, record["message"])
            )


filter = LogFilter("DEBUG")
logger.remove()
logger.add(sys.stdout, format=tracing_formatter, filter=filter)
# format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}{extra[traceback]}</level>",

__all__ = ["logger", "filter"]
