"""The import order matters, we need to first import the important stuff

isort:skip_file
"""

import klayout.dbcore as kdb
import klayout.lay as lay
from .kcell import (
    KCell,
    CplxKCell,
    Instance,
    Port,
    DPort,
    ICplxPort,
    DCplxPort,
    Ports,
    autocell,
    cell,
    klib,
    KLib,
    default_save,
    LayerEnum,
    show,
)
from . import pcells, tech, placer, routing, utils, port
from .config import logger


__version__ = "0.4.5"


def __getattr__(name: str) -> "KLib":
    # TODO: Remove with 0.4.5
    if name != "library":
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    logger.opt(ansi=True).bind(with_backtrace=True).warning(
        "<red>DeprecationWarning:</red> library has been renamed to klib since version 0.3.1 and library will be removed with 0.4.5, update your code to use klib instead",
    )
    return klib


__all__ = [
    "KCell",
    "CplxKCell",
    "Instance",
    "Port",
    "DPort",
    "ICplxPort",
    "DCplxPort",
    "Ports",
    "autocell",
    "cell",
    "klib",
    "KLib",
    "default_save",
    "kdb",
    "pcells",
    "placer",
    "routing",
    "utils",
    "show",
    "tech",
    "klay",
    "LayerEnum",
]
