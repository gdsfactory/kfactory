"""Technology settings."""
from __future__ import annotations

import pathlib
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

from pydantic import BaseModel, root_validator

module_path = pathlib.Path(__file__).parent.absolute()
# Layer = Tuple[int, int]
nm = 1e-3


from enum import Enum, IntEnum

from kfactory import KCell, KLib, kdb, library


class LayerEnum(int, Enum):  # IntEnum):

    layer: int
    datatype: int

    def __new__(
        cls: LayerMap, layer: int, datatype, *args, lib: KLib = library, **kwargs
    ) -> LayerMap:
        obj: int = int.__new__(cls, *args, **kwargs)
        obj._value_ = lib.layer(layer, datatype)
        obj.layer = layer
        obj.datatype = datatype
        return obj

    def __getitem__(self, key: int) -> int:
        if key == 0:
            return self.layer
        elif key == 1:
            return self.datatype

        else:
            raise ValueError(
                "LayerMap only has two values accessible like a list, layer == [0] and datatype == [1]"
            )

    def __len__(self) -> int:
        return 2

    def __iter__(self) -> Iterator[int]:
        yield from [self.layer, self.datatype]

    # RX = (2, 0)


# class Layer(kdb.LayerInfo):

#     # ind: int
#     # layer: int
#     # datatype: int
#     # name: int
#     # library: KLib

#     def __init__(
#         self,
#         layer: int,
#         datatype: int,
#         name: Optional[str] = None,
#         library: KLib = library,
#     ) -> None:
#         self.ind = library.layer(layer, datatype)
#         if name is None:
#             kdb.LayerInfo.__init__(self, layer, datatype)
#         else:
#             kdb.LayerInfo.__init__(self, layer, datatype, name)

#     def __iter__(self) -> Iterator[int]:
#         yield from [self.layer, self.datatype]

#     def __len__(self) -> int:
#         return 2

#     def __getitem__(self, key: int) -> int:
#         if key == 0:
#             return self.layer
#         elif key == 1:
#             return self.datatype
#         else:
#             raise ValueError(
#                 "A LayerInfo iterator can only access [0] as the layer and [1] as the datatype"
#             )


# LayerSpec = Union[int, Layer, str, None]


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


class LayerStack(BaseModel):
    """For simulation and 3D rendering.

    Parameters:
        layers: dict of layer_levels.
    """

    layers: Dict[str, LayerLevel]

    def get_layer_to_thickness(self) -> Dict[Tuple[int, int], float]:
        """Returns layer tuple to thickness (um)."""
        return {
            level.layer: level.thickness
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_zmin(self) -> Dict[Tuple[int, int], float]:
        """Returns layer tuple to z min position (um)."""
        return {
            level.layer: level.zmin for level in self.layers.values() if level.thickness
        }

    def get_layer_to_material(self) -> Dict[Tuple[int, int], str]:
        """Returns layer tuple to material name."""
        return {
            level.layer: level.material
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_sidewall_angle(self) -> Dict[Tuple[int, int], str]:
        """Returns layer tuple to material name."""
        return {
            level.layer: level.sidewall_angle
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_info(self) -> Dict[Tuple[int, int], Dict]:
        """Returns layer tuple to info dict."""
        return {level.layer: level.info for level in self.layers.values()}

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return {level_name: dict(level) for level_name, level in self.layers.items()}

    def get_klayout_3d_script(self, klayout28: bool = True) -> str:
        """Prints script for 2.5 view KLayout information.

        You can add this information in your tech.lyt take a look at
        gdsfactory/klayout/tech/tech.lyt
        """
        for level in self.layers.values():
            layer = level.layer
            if layer:
                if klayout28:
                    print(
                        f"z(input({layer[0]}, {layer[1]}), zstart: {level.zmin}, height: {level.zmin+level.thickness}, name: '{level.material} {layer[0]}/{layer[1]}')"
                    )
                else:
                    print(
                        f"{level.layer[0]}/{level.layer[1]}: {level.zmin} {level.zmin+level.thickness}"
                    )


# def get_layer_stack_generic(
#     thickness_wg: float = 220 * nm,
#     thickness_slab_deep_etch: float = 90 * nm,
#     thickness_clad: float = 3.0,
#     thickness_nitride: float = 350 * nm,
#     thickness_ge: float = 500 * nm,
#     gap_silicon_to_nitride: float = 100 * nm,
#     zmin_heater: float = 1.1,
#     zmin_metal1: float = 1.1,
#     thickness_metal1: float = 700 * nm,
#     zmin_metal2: float = 2.3,
#     thickness_metal2: float = 700 * nm,
#     zmin_metal3: float = 3.2,
#     thickness_metal3: float = 2000 * nm,
#     substrate_thickness: float = 10.0,
#     box_thickness: float = 3.0,
#     undercut_thickness: float = 5.0,
# ) -> LayerStack:
#     """Returns generic LayerStack.

#     based on paper https://www.degruyter.com/document/doi/10.1515/nanoph-2013-0034/html

#     Args:
#         thickness_wg: waveguide thickness in um.
#         thickness_slab_deep_etch: for deep etched slab.
#         thickness_clad: cladding thickness in um.
#         thickness_nitride: nitride thickness in um.
#         thickness_ge: germanium thickness.
#         gap_silicon_to_nitride: distance from silicon to nitride in um.
#         zmin_heater: TiN heater.
#         zmin_metal1: metal1.
#         thickness_metal1: metal1 thickness.
#         zmin_metal2: metal2.
#         thickness_metal2: metal2 thickness.
#         zmin_metal3: metal3.
#         thickness_metal3: metal3 thickness.
#         substrate_thickness: substrate thickness in um.
#         box_thickness: bottom oxide thickness in um.
#         undercut_thickness: thickness of the silicon undercut.
#     """
#     return LayerStack(
#         layers=dict(
#             substrate=LayerLevel(
#                 thickness=substrate_thickness,
#                 zmin=-substrate_thickness - box_thickness,
#                 material="si",
#                 info={"mesh_order": 99},
#             ),
#             box=LayerLevel(
#                 thickness=box_thickness,
#                 zmin=-box_thickness,
#                 material="sio2",
#                 info={"mesh_order": 99},
#             ),
#             core=LayerLevel(
#                 layer=LAYER.WG,
#                 thickness=thickness_wg,
#                 zmin=0.0,
#                 material="si",
#                 info={"mesh_order": 1},
#                 sidewall_angle=0,
#             ),
#             clad=LayerLevel(
#                 # layer=LAYER.WGCLAD,
#                 zmin=0.0,
#                 material="sio2",
#                 thickness=thickness_clad,
#                 info={"mesh_order": 10},
#             ),
#             slab150=LayerLevel(
#                 layer=LAYER.SLAB150,
#                 thickness=150e-3,
#                 zmin=0,
#                 material="si",
#                 info={"mesh_order": 3},
#             ),
#             slab90=LayerLevel(
#                 layer=LAYER.SLAB90,
#                 thickness=thickness_slab_deep_etch,
#                 zmin=0.0,
#                 material="si",
#                 info={"mesh_order": 2},
#             ),
#             nitride=LayerLevel(
#                 layer=LAYER.WGN,
#                 thickness=thickness_nitride,
#                 zmin=thickness_wg + gap_silicon_to_nitride,
#                 material="sin",
#                 info={"mesh_order": 2},
#             ),
#             ge=LayerLevel(
#                 layer=LAYER.GE,
#                 thickness=thickness_ge,
#                 zmin=thickness_wg,
#                 material="ge",
#                 info={"mesh_order": 1},
#             ),
#             undercut=LayerLevel(
#                 layer=LAYER.UNDERCUT,
#                 thickness=-undercut_thickness,
#                 zmin=-box_thickness,
#                 material="air",
#                 z_to_bias=[
#                     [0, 0.3, 0.6, 0.8, 0.9, 1],
#                     [-0, -0.5, -1, -1.5, -2, -2.5],
#                 ],
#                 info={"mesh_order": 1},
#             ),
#             via_contact=LayerLevel(
#                 layer=LAYER.VIAC,
#                 thickness=zmin_metal1 - thickness_slab_deep_etch,
#                 zmin=thickness_slab_deep_etch,
#                 material="Aluminum",
#                 info={"mesh_order": 1},
#                 sidewall_angle=-10,
#             ),
#             metal1=LayerLevel(
#                 layer=LAYER.M1,
#                 thickness=thickness_metal1,
#                 zmin=zmin_metal1,
#                 material="Aluminum",
#                 info={"mesh_order": 2},
#             ),
#             heater=LayerLevel(
#                 layer=LAYER.HEATER,
#                 thickness=750e-3,
#                 zmin=zmin_heater,
#                 material="TiN",
#                 info={"mesh_order": 1},
#             ),
#             via1=LayerLevel(
#                 layer=LAYER.VIA1,
#                 thickness=zmin_metal2 - (zmin_metal1 + thickness_metal1),
#                 zmin=zmin_metal1 + thickness_metal1,
#                 material="Aluminum",
#                 info={"mesh_order": 2},
#             ),
#             metal2=LayerLevel(
#                 layer=LAYER.M2,
#                 thickness=thickness_metal2,
#                 zmin=zmin_metal2,
#                 material="Aluminum",
#                 info={"mesh_order": 2},
#             ),
#             via2=LayerLevel(
#                 layer=LAYER.VIA2,
#                 thickness=zmin_metal3 - (zmin_metal2 + thickness_metal2),
#                 zmin=zmin_metal2 + thickness_metal2,
#                 material="Aluminum",
#                 info={"mesh_order": 1},
#             ),
#             metal3=LayerLevel(
#                 layer=LAYER.M3,
#                 thickness=thickness_metal3,
#                 zmin=zmin_metal3,
#                 material="Aluminum",
#                 info={"mesh_order": 2},
#             ),
#         )
#     )


# LAYER_STACK = get_layer_stack_generic()


# class Section(BaseModel):
#     """CrossSection to extrude a path with a waveguide.

#     Parameters:
#         width: of the section (um) or parameterized function from 0 to 1.
#              the width at t==0 is the width at the beginning of the Path.
#              the width at t==1 is the width at the end.
#         offset: center offset (um) or function parameterized function from 0 to 1.
#              the offset at t==0 is the offset at the beginning of the Path.
#              the offset at t==1 is the offset at the end.
#         layer: layer spec.
#         port_names: Optional port names.
#         port_types: optical, electrical, ...
#         name: Optional Section name.
#         hidden: hide layer.
#     .. code::
#           0   offset
#           |<-------------->|
#           |              _____
#           |             |     |
#           |             |layer|
#           |             |_____|
#           |              <---->
#                          width
#     """

#     width: Union[float, Callable]
#     offset: Union[float, Callable] = 0
#     layer: Union[LayerSpec, Tuple[LayerSpec, LayerSpec]]
#     port_names: Tuple[Optional[str], Optional[str]] = (None, None)
#     port_types: Tuple[str, str] = ("optical", "optical")
#     name: Optional[str] = None
#     hidden: bool = False

#     class Config:
#         """pydantic basemodel config."""

#         extra = "forbid"


# MaterialSpec = Union[str, float, complex, Tuple[float, float]]


# class SimulationSettingsLumericalFdtd(BaseModel):
#     """Lumerical FDTD simulation_settings.

#     Parameters:
#         background_material: for the background.
#         port_margin: on both sides of the port width (um).
#         port_height: port height (um).
#         port_extension: port extension (um).
#         mesh_accuracy: 2 (1: coarse, 2: fine, 3: superfine).
#         zmargin: for the FDTD region (um).
#         ymargin: for the FDTD region (um).
#         xmargin: for the FDTD region (um).
#         wavelength_start: 1.2 (um).
#         wavelength_stop: 1.6 (um).
#         wavelength_points: 500.
#         simulation_time: (s) related to max path length
#             3e8/2.4*10e-12*1e6 = 1.25mm.
#         simulation_temperature: in kelvin (default = 300).
#         frequency_dependent_profile: compute mode profiles for each wavelength.
#         field_profile_samples: number of wavelengths to compute field profile.
#     """

#     background_material: str = "sio2"
#     port_margin: float = 1.5
#     port_extension: float = 5.0
#     mesh_accuracy: int = 2
#     zmargin: float = 1.0
#     ymargin: float = 3.0
#     xmargin: float = 3.0
#     wavelength_start: float = 1.2
#     wavelength_stop: float = 1.6
#     wavelength_points: int = 500
#     simulation_time: float = 10e-12
#     simulation_temperature: float = 300
#     frequency_dependent_profile: bool = True
#     field_profile_samples: int = 15
#     distance_source_to_monitors: float = 0.2
#     material_name_to_lumerical: Dict[str, MaterialSpec] = {
#         "si": "Si (Silicon) - Palik",
#         "sio2": "SiO2 (Glass) - Palik",
#         "sin": "Si3N4 (Silicon Nitride) - Phillip",
#     }

#     class Config:
#         """pydantic basemodel config."""

#         arbitrary_types_allowed = True


# SIMULATION_SETTINGS_LUMERICAL_FDTD = SimulationSettingsLumericalFdtd()


def assert_callable(function):
    if not callable(function):
        raise ValueError(
            f"Error: function = {function} with type {type(function)} is not callable"
        )


if __name__ == "__main__":
    # import gdsfactory as gf
    # from gdsfactory.serialization import clean_value_json

    # d = clean_value_json(SIMULATION_SETTINGS_LUMERICAL_FDTD)

    # def mmi1x2_longer(length_mmi: float = 25.0, **kwargs):
    #     return gf.components.mmi1x2(length_mmi=length_mmi, **kwargs)

    # def mzi_longer(**kwargs):
    #     return gf.components.mzi(splitter=mmi1x2_longer, **kwargs)

    # ls = LAYER_STACK
    # ls.get_klayout_3d_script()
    # print(ls.get_layer_to_material())
    # print(ls.get_layer_to_thickness())

    # s = Section(width=1, layer=(1, 0))
    # print(s)
    print(
        LAYER.WG,
        int(LAYER.WG),
        LAYER.WG.name,
        LAYER.WG[0],
        LAYER.WG[1],
        list(LAYER.WG),
        KCell().shapes(LAYER.WG),
    )
