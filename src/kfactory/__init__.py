"""KFactory package. Utilities for creating photonic devices.

Uses the klayout package as a backend.

"""
# The import order matters, we need to first import the important stuff.
# isort:skip_file

__version__ = "1.10.0"

import klayout.db as kdb
from klayout import lay
from klayout import rdb

from .conf import config, logger, CheckInstances
from .cross_section import (
    SymmetricalCrossSection,
    CrossSection,
    CrossSectionSpec,
    DCrossSection,
)
from .enclosure import KCellEnclosure, LayerEnclosure
from .grid import flexgrid, flexgrid_dbu, grid, grid_dbu
from .kcell import BaseKCell, DKCell, KCell, ProtoTKCell, VKCell, show
from .pin import Pin, DPin, ProtoPin
from .pins import Pins, DPins
from .ports import Ports, DPorts
from .port import Port, DPort, ProtoPort
from .instance import Instance, DInstance, VInstance
from .instance_group import InstanceGroup, DInstanceGroup, VInstanceGroup
from .instance_ports import InstancePorts, DInstancePorts, VInstancePorts
from .netlist import Netlist
from .schema import Schema, DSchema, get_schema, read_schema
from .instances import Instances, DInstances, VInstances
from .settings import KCellSettings, Info
from .layout import Constants, KCLayout, cell, vcell, kcl, kcls
from .layer import LayerEnum, LayerInfos, LayerStack
from .shapes import VShapes
from .session_cache import save_session, load_session
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
    protocols,
    routing,
    technology,
    utils,
    typings,
    kcell,
    conf,
    layer,
    layout,
    schema,
)
from .routing.generic import ManhattanRoute
from .typings import dbu  # noqa: F401

ManhattanRoute.model_rebuild()


__all__ = [
    "BaseKCell",
    "CheckInstances",
    "Constants",
    "CrossSection",
    "CrossSectionSpec",
    "DCrossSection",
    "DInstance",
    "DInstanceGroup",
    "DInstancePorts",
    "DInstances",
    "DKCell",
    "DPin",
    "DPins",
    "DPort",
    "DPorts",
    "DSchema",
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
    "Netlist",
    "Pin",
    "Pins",
    "Port",
    "Ports",
    "ProtoPin",
    "ProtoPort",
    "ProtoTKCell",
    "Schema",
    "SymmetricalCrossSection",
    "VInstance",
    "VInstanceGroup",
    "VInstancePorts",
    "VInstances",
    "VInstances",
    "VKCell",
    "VShapes",
    "cell",
    "cells",
    "conf",
    "config",
    "dpolygon_from_array",
    "enclosure",
    "factories",
    "flexgrid",
    "flexgrid_dbu",
    "get_schema",
    "grid",
    "grid_dbu",
    "kcell",
    "kcl",
    "kcls",
    "kdb",
    "lay",
    "layer",
    "layout",
    "load_session",
    "logger",
    "packing",
    "placer",
    "polygon_from_array",
    "port",
    "pprint_ports",
    "protocols",
    "rdb",
    "read_schema",
    "routing",
    "save_layout_options",
    "save_session",
    "schema",
    "show",
    "technology",
    "typings",
    "utils",
    "vcell",
]
