"""PDK stores layers, enclosures, cell functions ..."""

from __future__ import annotations

from collections.abc import Iterable
from inspect import getmembers, signature
from types import ModuleType

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
                    "LAYER", {}  # type: ignore[arg-type, assignment]
                )
            )
            sparameters_path = sparameters_path or base_pdk.sparameters_path
            interconnect_cml_path = (
                interconnect_cml_path or base_pdk.interconnect_cml_path
            )
            _constants = constants() if constants else base_pdk.constants.copy()
        else:
            name = name
            layer_enclosures = layer_enclosures
            enclosure = enclosure or KCellEnclosure(enclosures=[])
            cell_factories = cell_factories
            layers = layers or kcell_mod.LayerEnum(
                "LAYER", {}  # type: ignore[arg-type, assignment]
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
        """Create a new LAYER enum based on the pdk's kcl."""
        return kcell_mod.LayerEnum(name, layers, kcl=self.kcl)  # type: ignore[arg-type]
