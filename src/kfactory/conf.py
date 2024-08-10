"""Kfactory configuration."""

from __future__ import annotations

import os
import re
import sys
import traceback
from enum import Enum
from itertools import takewhile
from typing import Any, Literal

import loguru
import rich.console
from dotenv import find_dotenv
from loguru import logger as logger
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    """KFactory logger levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CHECK_INSTANCES(str, Enum):
    RAISE = "error"
    FLATTEN = "flatten"
    VINSTANCES = "vinstances"
    IGNORE = "ignore"


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
        threads = len(os.sched_getaffinity(0))  # type: ignore[attr-defined,unused-ignore]
    except AttributeError:
        import multiprocessing

        threads = multiprocessing.cpu_count()
    finally:
        return threads


dotenv_path = find_dotenv(usecwd=True)


class Settings(BaseSettings):
    """KFactory settings object.

    Attrs:
        n_threads: Number of threads to use for tiling processor, defaults
            to all available cores.
        logger: The loguru class to use for logging. Shouldn't be necessary
            to configure by hand.
        logfilter: The filter to use. Can be configured to set log level and filter
            messages by regex.
        display_type: The type of image to show when calling the jupyter display
            function.
        meta_format: Metadata format to use for reading KLayout metadata.
            If set to 'default', metadata will be read as instances such as
            Trans/DCplxTrans. If the metadata is in the old string format
            (there was a bug in how to read metadata in some versions), use
            'string'.
        console: The rich console to use for displaying rich content.
        max_cellname_length: The maximum length of a cell name.
    """

    model_config = SettingsConfigDict(
        arbitrary_types_allowed=True,
        env_prefix="kfactory_",
        env_nested_delimiter="_",
        extra="allow",
        validate_assignment=True,
        env_file=dotenv_path,
    )

    n_threads: int = get_affinity()
    """Number of threads to use for multithreaded operations."""
    logfilter: LogFilter = Field(default_factory=LogFilter)
    """Can configure the logger to ignore certain levels or by regex."""
    display_type: Literal["widget", "image"] = "image"
    """The default behavior for displaying cells in jupyter."""
    meta_format: Literal["v2", "v1"] = "v2"
    """The format of the saving of metadata.

    v1: Transformations and other KLayout objects are stored as a string. In
        case of ports they are converted back to KLayout objects on read.
    v2: All objects can be stored in the nativ KLayout format (klayout>=0.28.13)
    """
    # console for printing
    console: rich.console.Console = Field(default_factory=rich.console.Console)

    # cell decorator settings
    allow_width_mismatch: bool = False
    allow_layer_mismatch: bool = False
    allow_type_mismatch: bool = False
    allow_undefined_layers: bool = False
    cell_layout_cache: bool = False
    cell_overwrite_existing: bool = False
    connect_use_angle: bool = True
    connect_use_mirror: bool = True
    check_instances: CHECK_INSTANCES = CHECK_INSTANCES.RAISE
    max_cellname_length: int = 99
    debug_names: bool = False

    # default write settings
    write_cell_properties: bool = True
    write_context_info: bool = True
    write_file_properties: bool = True

    @field_validator("logfilter")
    @classmethod
    def _validate_logfilter(cls, logfilter: LogFilter) -> LogFilter:
        logger.remove()
        logger.add(
            sys.stdout,
            format=tracing_formatter,
            filter=logfilter,
            enqueue=True,
            backtrace=True,
        )
        logger.debug("LogLevel: {}", logfilter.level)
        logger.patch(add_traceback)

        return logfilter

    @field_validator("cell_overwrite_existing")
    @classmethod
    def _validate_overwrite_and_cache(cls, v: bool, info: ValidationInfo) -> bool:
        if v is True:
            logger.warning(
                "'overwrite_existing' has been set to True. This might cause "
                "unintended behavior when overwriting existing cells and delete any "
                "existing instances of them."
            )
        return v

    @field_validator("cell_layout_cache")
    @classmethod
    def _validate_layout_cache(cls, v: bool, info: ValidationInfo) -> bool:
        if v is True:
            logger.warning(
                "'cell_layout_cache' has been set to True. This might cause when "
                "as any cell names generated automatically are loaded from the layout"
                " instead of created. This could happen e.g. after reading a gds file"
                " into the layout."
            )
        return v

    @field_validator(
        "allow_width_mismatch", "allow_layer_mismatch", "allow_type_mismatch"
    )
    @classmethod
    def _debug_info_on_global_setting(cls, v: Any, info: ValidationInfo) -> Any:
        logger.bind(with_traceback=True).debug(
            "'{}' set globally to '{}'", info.field_name, v
        )
        return v

    def __init__(self, **data: Any):
        """Set log filter and run pydantic."""
        super().__init__(**data)


config = Settings()


__all__ = ["config", "LogLevel"]
