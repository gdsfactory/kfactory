"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "0.21.0"

import klayout.db as kdb
import klayout.lay as lay
import klayout.rdb as rdb
from .kcell import (
    Info,
    Instance,
    InstanceGroup,
    KCLayout,
    KCell,
    KCellSettings,
    LayerEnum,
    LayerInfos,
    Constants,
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
from . import (
    cells,
    enclosure,
    kf_types,
    packing,
    placer,
    port,
    routing,
    technology,
    utils,
)
from .conf import config, logger
from .enclosure import LayerEnclosure, KCellEnclosure
from .grid import flexgrid_dbu, flexgrid, grid_dbu, grid
import sys

from aenum import constant  # type: ignore[import-untyped,unused-ignore]


__all__ = [
    "Constants",
    "Info",
    "Instance",
    "InstanceGroup",
    "KCLayout",
    "KCell",
    "KCellEnclosure",
    "KCellSettings",
    "LayerEnclosure",
    "LayerEnum",
    "LayerInfos",
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
    "packing",
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
_vi = sys.version_info
if _vi.major < 3 or _vi.minor < 11:
    logger.error(
        "kfactory will not support python 3.10 in the future anymore. "
        "Please upgrade to python >=3.11",
    )
