"""Technology settings."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple

from pydantic import BaseModel

from .kcell import KCell, KLib, LayerEnum, klib

# from kfactory import KCell, KLib, library


class LAYER(LayerEnum):
    #     """Generic layermap based on book.

    #     Lukas Chrostowski, Michael Hochberg, "Silicon Photonics Design",
    #     Cambridge University Press 2015, page 353
    #     You will need to create a new LayerMap with your specific foundry layers.
    #     """

    #     @root_validator(pre=True)
    #     def check_layer(cls, values):
    #         for key, value in values.items():
    #             if key != "Config":
    #                 assert isinstance(value.layer, int)
    #                 assert isinstance(value.datatype, int)
    #                 assert isinstance(value.ind, int)

    WG = (1, 0)
    WGCLAD = (111, 0)
    SLAB150 = (2, 0)
    SLAB90 = (3, 0)
    DEEPTRENCH = (4, 0)
    GE = (5, 0)
    UNDERCUT = (6, 0)
    WGN = (34, 0)
    WGN_CLAD = (36, 0)

    N = (20, 0)
    NP = (22, 0)
    NPP = (24, 0)
    P = (21, 0)
    PP = (23, 0)
    PPP = (25, 0)
    GEN = (26, 0)
    GEP = (27, 0)

    HEATER = (47, 0)
    M1 = (41, 0)
    M2 = (45, 0)
    M3 = (49, 0)
    VIAC = (40, 0)
    VIA1 = (44, 0)
    VIA2 = (43, 0)
    PADOPEN = (46, 0)

    DICING = (100, 0)
    NO_TILE_SI = (71, 0)
    PADDING = (67, 0)
    DEVREC = (68, 0)
    FLOORPLAN = (64, 0)
    TEXT = (66, 0)
    PORT = (1, 10)
    PORTE = (1, 11)
    PORTH = (70, 0)
    SHOW_PORTS = (1, 12)
    LABEL = (201, 0)
    LABEL_SETTINGS = (202, 0)
    TE = (203, 0)
    TM = (204, 0)
    DRC_MARKER = (205, 0)
    LABEL_INSTANCE = (206, 0)
    ERROR_MARKER = (207, 0)
    ERROR_PATH = (208, 0)

    SOURCE = (110, 0)
    MONITOR = (101, 0)


#     class Config:
#         """pydantic config."""

#         frozen = True
#         extra = "forbid"


# LAYER = LayerMap()
PORT_MARKER_LAYER_TO_TYPE = {
    LAYER.PORT: "optical",
    LAYER.PORTE: "dc",
    LAYER.TE: "vertical_te",
    LAYER.TM: "vertical_tm",
}

PORT_LAYER_TO_TYPE = {
    LAYER.WG: "optical",
    LAYER.WGN: "optical",
    LAYER.SLAB150: "optical",
    LAYER.M1: "dc",
    LAYER.M2: "dc",
    LAYER.M3: "dc",
    LAYER.TE: "vertical_te",
    LAYER.TM: "vertical_tm",
}

PORT_TYPE_TO_MARKER_LAYER = {v: k for k, v in PORT_MARKER_LAYER_TO_TYPE.items()}


class LayerLevel(BaseModel):
    """Level for 3D LayerStack.

    Parameters:
        layer: (GDSII Layer number, GDSII datatype).
        thickness: layer thickness in um.
        thickness_tolerance: layer thickness tolerance in um.
        zmin: height position where material starts in um.
        material: material name.
        sidewall_angle: in degrees with respect to normal.
        z_to_bias: parametrizes shrinking/expansion of the design GDS layer
            when extruding from zmin (0) to zmin + thickness (1).
            Defaults no buffering [[0, 1], [0, 0]].
        info: simulation_info and other types of metadata.
            mesh_order: lower mesh order (1) will have priority over higher
                mesh order (2) in the regions where materials overlap.
            refractive_index: refractive_index
                can be int, complex or function that depends on wavelength (um).
            type: grow, etch, implant, or background.
            mode: octagon, taper, round.
                https://gdsfactory.github.io/klayout_pyxs/DocGrow.html
            into: etch into another layer.
                https://gdsfactory.github.io/klayout_pyxs/DocGrow.html
            doping_concentration: for implants.
            resistivity: for metals.
            bias: in um for the etch.
    """

    layer: Optional[Tuple[int, int]]
    thickness: float
    thickness_tolerance: Optional[float] = None
    zmin: float
    material: Optional[str] = None
    sidewall_angle: float = 0
    z_to_bias: Optional[Tuple[List[float], List[float]]] = None
    info: Dict[str, Any] = {}
