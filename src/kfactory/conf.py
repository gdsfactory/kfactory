"""Kfactory configuration."""

from __future__ import annotations

import os
import re
import sys
import traceback
from enum import Enum
from itertools import takewhile
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import loguru
from loguru import logger as logger
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class LogLevel(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFilter(BaseModel):
    """Filter certain messages by log level or regex.

    Filtered messages are not evaluated and discarded.
    """

    level: LogLevel = LogLevel.INFO
    regex: str | None = None

    def __call__(self, record: loguru.Record) -> bool:
        """Loguru needs the filter to be callable."""
        levelno = logger.level(self.level).no
        if self.regex is None:
            return record["level"].no >= levelno
        else:
            return record["level"].no >= levelno and not bool(
                re.search(self.regex, record["message"])
            )


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


class Settings(
    BaseSettings,
):
    """KFactory settings object."""

    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_prefix="kfactory_",
        env_nested_delimiter="_",
    )

    n_threads: int = get_affinity()
    logger: ClassVar[Logger] = logger
    logfilter: LogFilter = Field(default_factory=LogFilter)
    display_type: Literal["widget", "image", "docs"] = "widget"

    def __init__(self, **data: Any):
        """Set log filter and run pydantic."""
        super().__init__(**data)
        self.logger.remove()
        self.logger.add(sys.stdout, format=tracing_formatter, filter=self.logfilter)
        self.logger.debug("LogLevel: {}", self.logfilter.level)


config = Settings()


__all__ = ["config"]
