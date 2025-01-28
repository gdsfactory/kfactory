"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""
# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "1.0.2"

import klayout.db as kdb
import klayout.lay as lay
import klayout.rdb as rdb


from kfactory.config import config, logger
from kfactory.enclosure import KCellEnclosure, LayerEnclosure
from kfactory.grid import flexgrid, flexgrid_dbu, grid, grid_dbu
from kfactory.kcell import BaseKCell, DKCell, KCell, VKCell, show
from kfactory.ports import Ports, DPorts, pprint_ports
from kfactory.port import Port, DPort
from kfactory.instance import Instance, DInstance, VInstance
from kfactory.instance_group import InstanceGroup, DInstanceGroup, VInstanceGroup
from kfactory.instance_ports import InstancePorts, DInstancePorts, VInstancePorts
from kfactory.instances import Instances, DInstances, VInstances
from kfactory.settings import KCellSettings, Info
from kfactory.layout import KCLayout, cell, vcell, kcl, Constants
from kfactory.layer import LayerEnum, LayerInfos, LayerStack
from kfactory.shapes import VShapes
from kfactory.utilities import (
    dpolygon_from_array,
    polygon_from_array,
    save_layout_options,
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
    "vcell",
]
