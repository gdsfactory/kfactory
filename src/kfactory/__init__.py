"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

try:
    import pya
    kdb = pya
    lay = pya
    rdb = pya
except ImportError:
    import klayout.dbcore as kdb
    import klayout.lay as lay
    import klayout.rdb as rdb
from .kcell import (
    KCell,
    Instance,
    Port,
    Ports,
    cell,
    kcl,
    KCLayout,
    save_layout_options,
    LayerEnum,
    show,
    polygon_from_array,
    dpolygon_from_array,
    VKCell,
    VInstance,
)
from . import cells, placer, routing, port, technology, enclosure, utils
from .conf import config
from .enclosure import LayerEnclosure, KCellEnclosure

from aenum import constant  # type: ignore[import-untyped]

__version__ = "0.10.2"

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
    "rdb",
    "port",
    "cells",
    "placer",
    "routing",
    "utils",
    "show",
    "config",
    "enclosure",
    "LayerEnum",
    "logger",
    "polygon_from_array",
    "dpolygon_from_array",
    "technology",
    "LayerEnclosure",
    "KCellEnclosure",
    "constant",
    "save_layout_options",
    "VKCell",
    "VInstance",
]
