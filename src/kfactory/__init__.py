"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "0.13.2"

import klayout.db as kdb
import klayout.lay as lay
import klayout.rdb as rdb
from .kcell import (
    KCell,
    Instance,
    Port,
    Ports,
    cell,
    kcl,
    Info,
    KCLayout,
    save_layout_options,
    KCellSettings,
    LayerEnum,
    LayerStack,
    show,
    polygon_from_array,
    dpolygon_from_array,
    VKCell,
    VInstance,
)
from . import cells, enclosure, kf_types, placer, port, routing, technology, utils
from .conf import config
from .enclosure import LayerEnclosure, KCellEnclosure
from .grid import flexgrid_dbu, flexgrid, grid_dbu, grid

from aenum import constant  # type: ignore[import-untyped,unused-ignore]

logger = config.logger

__all__ = [
    "Info",
    "Instance",
    "KCLayout",
    "KCell",
    "KCellEnclosure",
    "KCellSettings",
    "LayerEnclosure",
    "LayerEnum",
    "LayerStack",
    "Port",
    "Ports",
    "VInstance",
    "VKCell",
    "cell",
    "cells",
    "config",
    "constant",
    "default_save",
    "dpolygon_from_array",
    "enclosure",
    "flexgrid",
    "flexgrid_dbu",
    "grid",
    "grid_dbu",
    "kcl",
    "kdb",
    "lay",
    "logger",
    "placer",
    "polygon_from_array",
    "port",
    "rdb",
    "routing",
    "save_layout_options",
    "show",
    "technology",
    "kf_types",
    "utils",
]
