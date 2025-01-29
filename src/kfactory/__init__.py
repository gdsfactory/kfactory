"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""
# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "1.0.3"

import klayout.db as kdb
from klayout import lay
from klayout import rdb


from .conf import config, logger
from .enclosure import KCellEnclosure, LayerEnclosure
from .grid import flexgrid, flexgrid_dbu, grid, grid_dbu
from .kcell import BaseKCell, DKCell, KCell, VKCell, show
from .ports import Ports, DPorts
from .port import Port, DPort
from .instance import Instance, DInstance, VInstance
from .instance_group import InstanceGroup, DInstanceGroup, VInstanceGroup
from .instance_ports import InstancePorts, DInstancePorts, VInstancePorts
from .instances import Instances, DInstances, VInstances
from .settings import KCellSettings, Info
from .layout import KCLayout, cell, vcell, kcl, Constants
from .layer import LayerEnum, LayerInfos, LayerStack
from .shapes import VShapes
from .utilities import (
    dpolygon_from_array,
    polygon_from_array,
    save_layout_options,
    pprint_ports,
)

from . import (
    cells,
    enclosure,
    factories,
    packing,
    placer,
    port,
    routing,
    technology,
    utils,
    typings,
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
    "dpolygon_from_array",
    "enclosure",
    "factories",
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
    "typings",
    "utils",
    "vcell",
]
