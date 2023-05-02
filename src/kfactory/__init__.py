"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

import klayout.dbcore as kdb
import klayout.lay as lay
from .kcell import (
    Cell,
    Instance,
    Port,
    Ports,
    cell,
    cell,
    klib,
    KLib,
    default_save,
    LayerEnum,
    show,
)
from . import cells, placer, routing, utils, port
from .config import logger


__version__ = "0.6.3"


__all__ = [
    "Cell",
    "Instance",
    "Port",
    "Ports",
    "cell",
    "cell",
    "klib",
    "KLib",
    "default_save",
    "kdb",
    "lay",
    "port",
    "cells",
    "placer",
    "routing",
    "utils",
    "show",
    "klay",
    "logger",
    "LayerEnum",
]
