"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "0.15.0"

import klayout.db as kdb
import klayout.lay as lay
import klayout.rdb as rdb
from .kcell import (
    Info,
    Instance,
    KCLayout,
    KCell,
    KCellSettings,
    LayerEnum,
    LayerStack,
    Port,
    Ports,
    VKCell,
    VInstance,
    cell,
    dpolygon_from_array,
    kcl,
    polygon_from_array,
    pprint_ports,
    save_layout_options,
    show,
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
    "pprint_ports",
    "rdb",
    "routing",
    "save_layout_options",
    "show",
    "technology",
    "kf_types",
    "utils",
]
