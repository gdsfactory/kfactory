"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""

# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "1.0.0"

import klayout.db as kdb
import klayout.lay as lay
import klayout.rdb as rdb
from .kcell import (
    BaseKCell,
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
    DPorts,
    cell,
    dcell,
    dpolygon_from_array,
    kcl,
    polygon_from_array,
    pprint_ports,
    save_layout_options,
    show,
    DKCell,
    ProtoPort,
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
    factories,
)
from .conf import config, logger
from .enclosure import LayerEnclosure, KCellEnclosure
from .grid import flexgrid_dbu, flexgrid, grid_dbu, grid

from aenum import constant  # type: ignore[import-untyped,unused-ignore]


__all__ = [
    "BaseKCell",
    "Constants",
    "DKCell",
    "DPorts",
    "Info",
    "ProtoPort",
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
    "dcell",
    "dpolygon_from_array",
    "enclosure",
    "factories",
    "flexgrid",
    "flexgrid_dbu",
    "grid",
    "grid_dbu",
    "kcl",
    "kdb",
    "kf_types",
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
    "utils",
]
