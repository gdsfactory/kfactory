"""Kfactory configuration."""

from __future__ import annotations

import importlib
import os
import re
import sys
import traceback
from enum import Enum, IntEnum
from functools import cached_property
from itertools import takewhile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

import git
import loguru
import rich.console
from dotenv import find_dotenv
from loguru import logger as logger  # noqa: PLC0414
from pydantic import BaseModel, Field, ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from . import kdb, rdb
    from .kcell import AnyKCell
    from .layout import KCLayout

__all__ = ["LogLevel", "config"]


DEFAULT_TRANS: dict[str, str | int | float | dict[str, str | int | float]] = {
    "x": "E",
    "y": "S",
    "x0": "W",
    "y0": "S",
    "margin": {
        "x": 10000,
        "y": 10000,
        "x0": 0,
        "y0": 0,
    },
    "ref": -2,
}
MIN_POINTS_FOR_SIMPLIFY = 3
MIN_POINTS_FOR_CLEAN = 2
MIN_POINTS_FOR_PLACEMENT = 2
MIN_WAYPOINTS_FOR_ROUTING = 2
NUM_PORTS_FOR_ROUTING = 2
MIN_ALL_ANGLE_ROUTES_POINTS = 3
MIN_HEX_THRESHOLD = 6

ANGLE_0 = 0
ANGLE_90 = 1
ANGLE_180 = 2
ANGLE_270 = 3


class PROPID(IntEnum):
    """Mapping for GDS properties."""

    NAME = 0
    """Instance name."""
    PURPOSE = 1
    """Instance purpose (e.g. 'routing')."""


class PORTDIRECTION(IntEnum):
    RIGHT = 0
    TOP = 1
    LEFT = 2
    BOTTOM = 3


@runtime_checkable
class ShowFunction(Protocol):
    def __call__(
        self,
        layout: KCLayout | AnyKCell | Path | str,
        *,
        lyrdb: rdb.ReportDatabase | Path | str | None,
        l2n: kdb.LayoutToNetlist | Path | str | None,
        keep_position: bool,
        save_options: kdb.SaveLayoutOptions,
        use_libraries: bool,
        library_save_options: kdb.SaveLayoutOptions,
    ) -> None: ...


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


class CheckInstances(str, Enum):
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
        return record["level"].no >= levelno and not bool(
            re.search(self.regex, record["message"])
        )


def get_show_function(value: str | ShowFunction) -> ShowFunction:
    if isinstance(value, str):
        mod, f = value.rsplit(".", 1)
        loaded_mod = importlib.import_module(mod)
        return loaded_mod.__getattribute__(f)  # type: ignore[no-any-return]
    return value


def get_affinity() -> int:
    """Get number of cores/threads available.

    On (most) linux we can get it through the scheduling affinity. Otherwise,
    fall back to the multiprocessing cpu count.
    """
    threads = 0
    try:
        return len(os.sched_getaffinity(0))  # type: ignore[attr-defined,unused-ignore]
    except AttributeError:
        import multiprocessing

        threads = multiprocessing.cpu_count()
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
    meta_format: Literal["v3", "v2", "v1"] = "v3"
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
    check_instances: CheckInstances = CheckInstances.RAISE
    max_cellname_length: int = 99
    debug_names: bool = False

    # default write settings
    write_cell_properties: bool = True
    write_context_info: bool = True
    write_file_properties: bool = True

    show_function: ShowFunction | None = None

    @field_validator("show_function", mode="before")
    @classmethod
    def _validate_show_function(
        cls, show: ShowFunction | str | None
    ) -> ShowFunction | None:
        if isinstance(show, str):
            mod, f = show.rsplit(".", 1)
            loaded_mod = importlib.import_module(mod)
            show_ = getattr(loaded_mod, f)
            if not isinstance(show_, ShowFunction):
                raise ValidationError(f"{show=} is not a ShowFunction.")
            show = show_
        return show

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
    def _validate_overwrite_and_cache(cls, v: bool) -> bool:
        if v is True:
            logger.warning(
                "'overwrite_existing' has been set to True. This might cause "
                "unintended behavior when overwriting existing cells and delete any "
                "existing instances of them."
            )
        return v

    @field_validator("cell_layout_cache")
    @classmethod
    def _validate_layout_cache(cls, v: bool) -> bool:
        if v is True:
            logger.debug(
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

    @cached_property
    def project_dir(self) -> Path:
        try:
            repo = git.repo.Repo(".", search_parent_directories=True)
            wtd = repo.working_tree_dir
            root = Path(wtd) if wtd is not None else Path.cwd()
        except git.InvalidGitRepositoryError:
            root = Path.cwd()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def __init__(self, **data: Any) -> None:
        """Set log filter and run pydantic."""
        super().__init__(**data)


config = Settings()
