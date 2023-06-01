"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

import klayout.dbcore as kdb
import klayout.lay as lay
from .kcell import (
    KCell,
    Instance,
    Port,
    Ports,
    cell,
    kcl,
    KCLayout,
    default_save,
    LayerEnum,
    show,
    polygon_from_array,
    dpolygon_from_array,
)
from . import cells, placer, routing, utils, port, pdk
from .conf import config
from .pdk import Pdk

__version__ = "0.7.5"

logger = config.logger

__all__ = [
    "KCell",
    "Instance",
    "Port",
    "Ports",
    "cell",
    "kcl",
    "KCLayout",
    "default_save",
    "kdb",
    "lay",
    "port",
    "cells",
    "placer",
    "routing",
    "utils",
    "show",
    "config",
    "LayerEnum",
    "logger",
    "pdk",
    "polygon_from_array",
    "dpolygon_from_array",
]
