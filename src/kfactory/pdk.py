"""PDK stores layers, enclosures, cell functions ..."""

from __future__ import annotations

from collections.abc import Iterable
from inspect import getmembers, signature
from types import ModuleType
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from . import kcell as kcell_mod

# from .technology import LayerStack
from .typings import CellFactory, PathType
from .utils.enclosure import KCellEnclosure, LayerEnclosure


def get_cells(
    modules: Iterable[ModuleType], verbose: bool = False
) -> dict[str, CellFactory]:
    """Returns KCells (KCell functions) from a module or list of modules.

    Args:
        modules: module or iterable of modules.
        verbose: prints in case any errors occur.
    """
    cells = {}
    for module in modules:
        for t in getmembers(module):
            if callable(t[1]) and t[0] != "partial":
                try:
                    r = signature(t[1]).return_annotation
                    if r == kcell_mod.KCell or (
                        isinstance(r, str) and r.endswith("KCell")
                    ):
                        cells[t[0]] = t[1]
                except ValueError:
                    if verbose:
                        print(f"error in {t[0]}")
    return cells


class LayerEnclosureModel(BaseModel):
    """PDK access model for LayerEnclsoures."""

    enclosure_map: dict[str, LayerEnclosure] = Field(default={})

    def __getitem__(self, __key: str) -> LayerEnclosure:
        """Retrieve element by string key."""
        return self.enclosure_map[__key]

    def __getattr__(self, __key: str) -> LayerEnclosure:
        """Retrieve attribute by key."""
        return self.enclosure_map[__key]


class CellModel(BaseModel):
    """PDK access model for KCell."""

    cell_map: dict[str, kcell_mod.KCell] = Field(default={})

    def __getitem__(self, __key: str) -> kcell_mod.KCell:
        """Retrieve element by string key."""
        return self.cell_map[__key]

    def __getattr__(self, __key: str) -> kcell_mod.KCell:
        """Retrieve attribute by key."""
        return self.cell_map[__key]

    class Config:
        """Pydantic Config."""

        arbitrary_types_allowed = True


class CellFactoryModel(BaseModel):
    """PDK access model for KCellFactories."""

    cellfactory_map: dict[str, CellFactory] = Field(default={})

    def __getitem__(self, __key: str) -> CellFactory:
        """Retrieve element by string key."""
        return self.cellfactory_map[__key]

    def __getattr__(self, __key: str) -> CellFactory:
        """Retrieve attribute by key."""
        return self.cellfactory_map[__key]

    class Config:
        """Retrieve element by string key."""

        arbitrary_types_allowed = True


class Constants(BaseSettings):
    """Constant Model class."""

    pass


class Pdk(BaseModel):
    """Store layers, enclosures, cell functions, simulation_settings ...

    only one Pdk can be active at a given time.

    Attributes:
        name: PDK name.
        enclosures: dict of enclosures factories.
        cells: dict of str mapping to KCells.
        cell_factories: dict of str mapping to cell factories.
        base_pdk: a pdk to copy from and extend.
        default_decorator: decorate all cells, if not otherwise defined on the cell.
        layers: maps name to gdslayer/datatype.
            Must be of type LayerEnum.
        layer_stack: maps name to layer numbers, thickness, zmin, sidewall_angle.
            if can also contain material properties
            (refractive index, nonlinear coefficient, sheet resistance ...).
        sparameters_path: to store Sparameters simulations.
        interconnect_cml_path: path to interconnect CML (optional).
        grid_size: in um. Defaults to 1nm.
        constants: dict of constants for the PDK.

    """

    name: str | None = None
    kcl: kcell_mod.KCLayout = kcell_mod.kcl
    layer_enclosures: LayerEnclosureModel
    enclosure: KCellEnclosure

    cell_factories: CellFactoryModel
    cells: CellModel
    layers: type[kcell_mod.LayerEnum]
    sparameters_path: PathType | None
    interconnect_cml_path: PathType | None
    layer_stack: LayerStack | None
    constants: Constants = Field(default_factory=Constants)

    class Config:
        """Configuration."""

        arbitrary_types_allowed = True
        extra = "allow"

    def __init__(
        self,
        name: str | None = None,
        kcl: kcell_mod.KCLayout = kcell_mod.kcl,
        layer_enclosures: dict[str, LayerEnclosure]
        | LayerEnclosureModel = LayerEnclosureModel(),
        enclosure: KCellEnclosure | None = None,
        cell_factories: dict[str, CellFactory] | CellFactoryModel = CellFactoryModel(),
        cells: dict[str, kcell_mod.KCell] | CellModel = CellModel(),
        layers: type[kcell_mod.LayerEnum] | None = None,
        layer_stack: LayerStack | None = None,
        sparameters_path: PathType | None = None,
        interconnect_cml_path: PathType | None = None,
        constants: type[Constants] | None = None,
        base_pdk: Pdk | None = None,
    ) -> None:
        """Create a new pdk. Can be based on an old PDK.

        Args:
            name: Name of the PDK.
            kcl: The layout object the pdk should use.
            layer_enclosures: Additional KCellEnclosures that should be available
                except the KCellEnclosure
            enclosure: The standard KCellEnclosure of the PDK.
            cell_factories: Functions for creating pcells from the PDK.
            cells: Fixed cells of the PDK.
            layers: A LayerEnum describing the layerstack of the PDK
            sparameters_path: Path to the sparameters config file.
            interconnect_cml_path: Path to the interconnect file.
            constants: A model containing all the constants related to the PDK.
            base_pdk: an optional basis of the PDK.
        """
        if isinstance(layer_enclosures, dict):
            layer_enclosures = LayerEnclosureModel(enclosure_map=layer_enclosures)
        if isinstance(cell_factories, dict):
            cell_factories = CellFactoryModel(cellfactory_map=cell_factories)
        if isinstance(cells, dict):
            cells = CellModel(cell_map=cells)

        if base_pdk:
            name = name or base_pdk.name
            lm = base_pdk.layer_enclosures.enclosure_map.copy()
            lm.update(layer_enclosures.enclosure_map)
            layer_enclosures = LayerEnclosureModel(enclosure_map=lm)
            enclosure = enclosure or base_pdk.enclosure or KCellEnclosure(enclosures=[])
            cfm = base_pdk.cell_factories.cellfactory_map.copy()
            cfm.update(cell_factories)
            cell_factories = CellFactoryModel(cellfactory_map=cfm)
            cm = base_pdk.cells.cell_map.copy()
            cm.update(cells.cell_map)
            cells = CellModel(cell_map=cm)
            layers = (
                layers
                or base_pdk.layers
                or kcell_mod.LayerEnum(
                    "kcell_mod.LayerEnum", {}  # type: ignore[arg-type, assignment]
                )
            )
            sparameters_path = sparameters_path or base_pdk.sparameters_path
            interconnect_cml_path = (
                interconnect_cml_path or base_pdk.interconnect_cml_path
            )
            layer_stack_ = base_pdk.layer_stack.layers
            layer_stack.layers.update(layer_stack_)
            _constants = constants() if constants else base_pdk.constants.copy()
        else:
            name = name
            layer_enclosures = layer_enclosures
            enclosure = enclosure or KCellEnclosure(enclosures=[])
            cell_factories = cell_factories
            layers = layers or kcell_mod.LayerEnum(
                "kcell_mod.LayerEnum", {}  # type: ignore[arg-type, assignment]
            )
            sparameters_path = sparameters_path
            interconnect_cml_path = interconnect_cml_path
            _constants = constants() if constants else Constants()

        super().__init__(
            name=name,
            kcl=kcl,
            layer_enclosures=layer_enclosures,
            enclosure=enclosure,
            cell_factories=cell_factories,
            cells=cells,
            layers=layers,
            layer_stack=layer_stack,
            sparameters_path=sparameters_path,
            interconnect_cml_path=interconnect_cml_path,
            constants=_constants,
        )

    def kcell(
        self, name: str | None = None, ports: kcell_mod.Ports | None = None
    ) -> kcell_mod.KCell:
        """Create a new cell based ont he pdk's layout object."""
        return kcell_mod.KCell(name=name, kcl=self.kcl, ports=ports)

    def layer_enum(
        self, name: str, layers: dict[str, tuple[int, int]]
    ) -> kcell_mod.LayerEnum:
        """Create a new kcell_mod.LayerEnum enum based on the pdk's kcl."""
        return kcell_mod.LayerEnum(name, layers, kcl=self.kcl)  # type: ignore[arg-type]


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

    layer: Union[Tuple[int, int], kcell_mod.LayerEnum]
    thickness: float
    thickness_tolerance: float | None = None
    zmin: float
    material: str | None = None
    sidewall_angle: float = 0
    z_to_bias: Optional[Tuple[float, ...]] = None
    info: kcell_mod.Info = {}


class LayerStack(BaseModel):
    """For simulation and 3D rendering.

    Parameters:
        layers: dict of layer_levels.
    """

    layers: Dict[str, LayerLevel] = Field(default_factory=dict)

    def __init__(self, **data: Any):
        """Add LayerLevels automatically for subclassed LayerStacks."""
        super().__init__(**data)

        for field in self.model_dump():
            val = getattr(self, field)
            if isinstance(val, LayerLevel):
                self.layers[field] = val
                if isinstance(val.layer, kcell_mod.LayerEnum):
                    self.layers[field].layer = (val.layer[0], val.layer[1])

    def get_layer_to_thickness(self) -> Dict[Tuple[int, int] | kcell_mod.LayerEnum, float]:
        """Returns layer tuple to thickness (um)."""
        return {
            level.layer: level.thickness
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_zmin(self) -> Dict[Tuple[int, int] | kcell_mod.LayerEnum, float]:
        """Returns layer tuple to z min position (um)."""
        return {
            level.layer: level.zmin for level in self.layers.values() if level.thickness
        }

    def get_layer_to_material(self) -> Dict[Tuple[int, int] | kcell_mod.LayerEnum, str]:
        """Returns layer tuple to material name."""
        return {
            level.layer: level.material
            for level in self.layers.values()
            if level.thickness and level.material
        }

    def get_layer_to_sidewall_angle(self) -> Dict[Tuple[int, int] | kcell_mod.LayerEnum, float]:
        """Returns layer tuple to material name."""
        return {
            level.layer: level.sidewall_angle
            for level in self.layers.values()
            if level.thickness
        }

    def get_layer_to_info(self) -> Dict[Tuple[int, int] | kcell_mod.LayerEnum, kcell_mod.Info]:
        """Returns layer tuple to info dict."""
        return {level.layer: level.info for level in self.layers.values()}

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return {level_name: dict(level) for level_name, level in self.layers.items()}

    def __getitem__(self, key: str) -> LayerLevel:
        """Access layer stack elements."""
        if key not in self.layers:
            layers = list(self.layers.keys())
            raise ValueError(f"{key!r} not in {layers}")

        return self.layers[key]


# def get_layer_stack(
nm = kcell_mod.kcl.dbu
thickness_wg = 220 * nm
thickness_slab_deep_etch = 90 * nm
thickness_clad = 3.0
thickness_nitride = 350 * nm
thickness_ge = 500 * nm
gap_silicon_to_nitride = 100 * nm
zmin_heater = 1.1
zmin_metal1 = 1.1
thickness_metal1 = 700 * nm
zmin_metal2 = 2.3
thickness_metal2 = 700 * nm
zmin_metal3 = 3.2
thickness_metal3 = 2000 * nm
substrate_thickness = 10.0
box_thickness = 3.0
undercut_thickness = 5.0
# )
# -> LayerStack:
#     """Returns generic LayerStack.

#     based on paper https://www.degruyter.com/document/doi/10.1515/nanoph-2013-0034/html

#     Args:
#         thickness_wg: straight thickness in um.
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


class LAYER_CLASS(kcell_mod.LayerEnum):
    WAFER = (99999, 0)

    WG = (1, 0)
    WGCLAD = (111, 0)
    SLAB150 = (2, 0)
    SHALLOW_ETCH = (2, 6)
    SLAB90 = (3, 0)
    DEEP_ETCH = (3, 6)
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
    MTOP = (49, 0)
    VIAC = (40, 0)
    VIA1 = (44, 0)
    VIA2 = (43, 0)
    PADOPEN = (46, 0)


class GenericLayerStack(LayerStack):
    substrate: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.WAFER,
        thickness=substrate_thickness,
        zmin=-substrate_thickness - box_thickness,
        material="si",
        info={"mesh_order": 99},
    )
    box: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.WAFER,
        thickness=box_thickness,
        zmin=-box_thickness,
        material="sio2",
        info={"mesh_order": 99},
    )
    core: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.WG,
        thickness=thickness_wg,
        zmin=0.0,
        material="si",
        info={"mesh_order": 1},
        sidewall_angle=10,
        # width_to_z=0.5,
    )
    clad: LayerLevel = LayerLevel(
        # layer=LAYER_CLASS.WGCLAD,
        layer=LAYER_CLASS.WAFER,
        zmin=0.0,
        material="sio2",
        thickness=thickness_clad,
        info={"mesh_order": 10},
    )
    slab150: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.SLAB150,
        thickness=150e-3,
        zmin=0,
        material="si",
        info={"mesh_order": 3},
    )
    slab90: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.SLAB90,
        thickness=thickness_slab_deep_etch,
        zmin=0.0,
        material="si",
        info={"mesh_order": 2},
    )
    nitride: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.WGN,
        thickness=thickness_nitride,
        zmin=thickness_wg + gap_silicon_to_nitride,
        material="sin",
        info={"mesh_order": 2},
    )
    ge: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.GE,
        thickness=thickness_ge,
        zmin=thickness_wg,
        material="ge",
        info={"mesh_order": 1},
    )
    undercut: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.UNDERCUT,
        thickness=-undercut_thickness,
        zmin=-box_thickness,
        material="air",
        # z_to_bias=tuple(
        #     list([0, 0.3, 0.6, 0.8, 0.9, 1]),
        #     list([-0, -0.5, -1, -1.5, -2, -2.5]),
        # ),
        info={"mesh_order": 1},
    )
    via_contact: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.VIAC,
        thickness=zmin_metal1 - thickness_slab_deep_etch,
        zmin=thickness_slab_deep_etch,
        material="Aluminum",
        info={"mesh_order": 1},
        sidewall_angle=-10,
    )
    metal1: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.M1,
        thickness=thickness_metal1,
        zmin=zmin_metal1,
        material="Aluminum",
        info={"mesh_order": 2},
    )
    heater: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.HEATER,
        thickness=750e-3,
        zmin=zmin_heater,
        material="TiN",
        info={"mesh_order": 1},
    )
    via1: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.VIA1,
        thickness=zmin_metal2 - (zmin_metal1 + thickness_metal1),
        zmin=zmin_metal1 + thickness_metal1,
        material="Aluminum",
        info={"mesh_order": 2},
    )
    metal2: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.M2,
        thickness=thickness_metal2,
        zmin=zmin_metal2,
        material="Aluminum",
        info={"mesh_order": 2},
    )
    via2: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.VIA2,
        thickness=zmin_metal3 - (zmin_metal2 + thickness_metal2),
        zmin=zmin_metal2 + thickness_metal2,
        material="Aluminum",
        info={"mesh_order": 1},
    )
    metal3: LayerLevel = LayerLevel(
        layer=LAYER_CLASS.M3,
        thickness=thickness_metal3,
        zmin=zmin_metal3,
        material="Aluminum",
        info={"mesh_order": 2},
    )


LAYER_STACK = GenericLayerStack()
