"""Kfactory configuration."""

from __future__ import annotations

import os
import re
import sys
import traceback
from itertools import takewhile
from typing import TYPE_CHECKING, ClassVar

import loguru
from loguru import logger as logger
from pydantic import BaseSettings, Field

if TYPE_CHECKING:
    from loguru import Logger


def add_traceback(record: loguru.Record) -> None:
    """Add a traceback to the logger."""
    extra = record["extra"]
    if extra.get("with_traceback", False):
        extra["traceback"] = "\n" + "".join(traceback.format_stack())
    else:
        extra["traceback"] = ""


def tracing_formatter(record: loguru.Record) -> str:
    """Traceback filtering.

    Filter out frames coming from Loguru internals.
    """
    frames = takewhile(
        lambda f: "/loguru/" not in f.filename, traceback.extract_stack()
    )
    stack = " > ".join(f"{f.filename}:{f.name}:{f.lineno}" for f in frames)
    record["extra"]["stack"] = stack

    if record["extra"].get("with_backtrace", False):
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level>"
            " | <cyan>{extra[stack]}</cyan> - <level>{message}</level>\n{exception}"
        )

    else:
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}"
            "</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
            " - <level>{message}</level>\n{exception}"
        )


class LogFilter:
    """Filter certain messages by log level or regex.

    Filtered messages are not evaluated and discarded.
    """

    def __init__(self, level: str, regex: str | None = None) -> None:
        """Create new filter.

        Args:
            level: Minimum log level to print to log. Options:
                ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            regex: Discard messages matching the regex string. Set to `None` to disable.
        """
        self.level = level
        self.regex = regex

    def __call__(self, record: loguru.Record) -> bool:
        """Loguru needs the filter to be callable."""
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


def get_affinity() -> int:
    """Get number of cores/threads available.

    On (most) linux we can get it through the scheduling affinity. Otherwise,
    fall back to the multiprocessing cpu count.
    """
    try:
        threads = len(os.sched_getaffinity(0))
    except AttributeError:
        import multiprocessing

        threads = multiprocessing.cpu_count()
    finally:
        return threads


class Settings(BaseSettings):
    """KFactory settings object."""

    n_threads: int = get_affinity()
    logger: ClassVar[Logger] = logger
    logfilter: LogFilter = filter

    class Config:
        validation = False
        arbitrary_types_allowed = True
        fields = {"logger": {"exclude": True}}


config = Settings()

__all__ = ["config"]
