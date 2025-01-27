"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""
# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "1.0.1"

import klayout.db as kdb
import klayout.lay as lay
import klayout.rdb as rdb
from aenum import constant  # type: ignore[import-untyped,unused-ignore]


from .conf import config, logger
from .enclosure import KCellEnclosure, LayerEnclosure
from .grid import flexgrid, flexgrid_dbu, grid, grid_dbu
from .kcell import (
    BaseKCell,
    Constants,
    DInstance,
    DInstanceGroup,
    DInstancePorts,
    DInstances,
    DKCell,
    DPort,
    DPorts,
    Info,
    Instance,
    InstanceGroup,
    InstancePorts,
    Instances,
    KCell,
    KCellSettings,
    KCLayout,
    LayerEnum,
    LayerInfos,
    LayerStack,
    Port,
    Ports,
    VInstance,
    VInstanceGroup,
    VInstancePorts,
    VInstances,
    VKCell,
    VShapes,
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
    factories,
    kf_types,
    packing,
    placer,
    port,
    routing,
    technology,
    utils,
)

__all__ = [
    "BaseKCell",
    "Constants",
    "DInstance",
    "DInstanceGroup",
    "DInstancePorts",
    "DInstances",
    "DKCell",
    "DPort",
    "DPorts",
    "Info",
    "Instance",
    "InstanceGroup",
    "InstancePorts",
    "Instances",
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
    "VInstanceGroup",
    "VInstancePorts",
    "VInstances",
    "VInstances",
    "VKCell",
    "VShapes",
    "cell",
    "cells",
    "config",
    "constant",
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
